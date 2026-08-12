#!/usr/bin/env python3
"""Codex-shaped Adam phone worker with canonical Venice completion review.

This is the only conversational/executive entrypoint shipped as bare `adam`.
The tiny local model proposes one typed action at a time. Deterministic code
executes tools, loads Codex-local steering documents, checkpoints long work,
backs off transient failures, and refuses to stop until canonical Venice review
allows it. Every Venice ruling is persisted as evidence.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import adam_codex_phone as worker
import venice_review as canonical_venice

CHECKPOINT_STEPS = int(os.environ.get("HC_ADAM_CHECKPOINT_STEPS", "48"))
BACKOFF_SECONDS = (1, 2, 4, 8, 15, 30)
STATE_DIR = Path(os.path.expanduser(os.environ.get("HC_STATE_DIR", "~/.local/state/home-center"))) / "adam-daemon"
CODEX_DOC_NAMES = ("AGENTS.md", "MEMORIES.md", "SKILLS.md")
CODEX_DOC_LIMIT = int(os.environ.get("HC_ADAM_CODEX_DOC_LIMIT", "24000"))


def resilient_call_model(original, messages: list[dict], timeout: int = 120) -> str:
    last = None
    for attempt, delay in enumerate((0, *BACKOFF_SECONDS)):
        if delay:
            time.sleep(delay + random.uniform(0, min(1.0, delay * 0.2)))
        try:
            return original(messages, timeout=timeout)
        except Exception as exc:
            last = exc
            if attempt >= len(BACKOFF_SECONDS):
                break
    raise RuntimeError(f"phone model unavailable after daemon backoff burst: {last}") from last


def repo_root(workspace: Path) -> Path | None:
    try:
        p = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=workspace, text=True, capture_output=True, timeout=10)
        if p.returncode == 0 and p.stdout.strip():
            return Path(p.stdout.strip()).resolve()
    except Exception:
        pass
    return None


def codex_local_documents(workspace: Path) -> tuple[str, list[str]]:
    """Load actual project-local Codex steering files, root first then deeper."""
    root = repo_root(workspace) or ROOT
    dirs: list[Path] = []
    try:
        rel = workspace.resolve().relative_to(root.resolve())
        current = root.resolve()
        dirs.append(current)
        for part in rel.parts:
            current = current / part
            dirs.append(current)
    except Exception:
        dirs = [ROOT.resolve()]
        if workspace.resolve() != ROOT.resolve():
            dirs.append(workspace.resolve())

    seen: set[Path] = set()
    sections: list[str] = []
    loaded: list[str] = []
    remaining = CODEX_DOC_LIMIT
    for directory in dirs:
        for name in CODEX_DOC_NAMES:
            path = (directory / name).resolve()
            if path in seen or not path.is_file():
                continue
            seen.add(path)
            raw = path.read_text(encoding="utf-8", errors="replace")
            label = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
            header = f"\n--- CODEX LOCAL {label} ---\n"
            allowance = max(0, remaining - len(header))
            if allowance <= 0:
                break
            body = raw[:allowance]
            sections.append(header + body)
            loaded.append(label)
            remaining -= len(header) + len(body)
        if remaining <= 0:
            break
    if not loaded:
        raise RuntimeError("Codex local steering documents missing; refusing generic-agent fallback")
    return "".join(sections), loaded


def git_evidence(workspace: Path, base_commit: str | None = None) -> dict:
    evidence: dict[str, object] = {"workspace": str(workspace), "isGitRepo": False, "codeChanged": False}
    root = repo_root(workspace)
    if root is None:
        return evidence
    try:
        evidence["isGitRepo"] = True
        evidence["gitRoot"] = str(root)
        hp = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, timeout=10)
        current_head = hp.stdout.strip() if hp.returncode == 0 else "UNKNOWN"
        task_base = base_commit or current_head
        if task_base not in {"", "UNKNOWN"}:
            vp = subprocess.run(["git", "rev-parse", f"{task_base}^{{commit}}"], cwd=root, text=True, capture_output=True, timeout=10)
            if vp.returncode != 0:
                task_base = current_head
        evidence["baseCommit"] = task_base
        evidence["headCommit"] = current_head

        status = subprocess.run(["git", "status", "--short"], cwd=root, text=True, capture_output=True, timeout=10)
        status_text = status.stdout
        sections: list[str] = []
        changed_paths: list[str] = []
        if task_base != "UNKNOWN" and current_head != "UNKNOWN":
            committed = subprocess.run(["git", "diff", "--no-ext-diff", f"{task_base}..{current_head}"], cwd=root, text=True, capture_output=True, timeout=30)
            names = subprocess.run(["git", "diff", "--name-only", f"{task_base}..{current_head}"], cwd=root, text=True, capture_output=True, timeout=20)
            if committed.stdout:
                sections.append("--- COMMITTED SINCE TASK START ---\n" + committed.stdout)
            if names.returncode == 0:
                changed_paths.extend(x.strip() for x in names.stdout.splitlines() if x.strip())
        staged = subprocess.run(["git", "diff", "--cached", "--no-ext-diff"], cwd=root, text=True, capture_output=True, timeout=20)
        unstaged = subprocess.run(["git", "diff", "--no-ext-diff"], cwd=root, text=True, capture_output=True, timeout=20)
        if staged.stdout:
            sections.append("--- STAGED WORKTREE ---\n" + staged.stdout)
        if unstaged.stdout:
            sections.append("--- UNSTAGED WORKTREE ---\n" + unstaged.stdout)
        for line in status_text.splitlines():
            path_text = line[3:].strip() if len(line) > 3 else ""
            if " -> " in path_text:
                path_text = path_text.split(" -> ", 1)[1]
            if not path_text:
                continue
            if path_text not in changed_paths:
                changed_paths.append(path_text)
            if line.startswith("??"):
                p = root / path_text
                if p.is_file() and p.stat().st_size <= 120000:
                    try:
                        sections.append(f"--- UNTRACKED {path_text} ---\n" + p.read_text(encoding="utf-8", errors="replace"))
                    except Exception:
                        pass
        combined = "\n\n".join(sections)
        check_args = ["git", "diff", "--check"] + ([task_base] if task_base != "UNKNOWN" else [])
        check = subprocess.run(check_args, cwd=root, text=True, capture_output=True, timeout=30)
        evidence.update({
            "status": worker.clipped(status_text, 6000),
            "diff": worker.clipped(combined, 28000),
            "diffFullSha256": hashlib.sha256(combined.encode()).hexdigest(),
            "diffTruncated": len(combined) > 28000,
            "diffCheckRc": check.returncode,
            "diffCheck": worker.clipped((check.stdout or "") + (check.stderr or ""), 4000),
            "changedPaths": changed_paths,
        })
        code_ext = (".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".java", ".kt", ".kts", ".sh", ".ps1", ".json", ".yaml", ".yml", ".toml", ".gradle", ".xml")
        evidence["codeChanged"] = any(p.lower().endswith(code_ext) or p.startswith(".continue/") for p in changed_paths)
    except Exception as exc:
        evidence["gitError"] = str(exc)
    return evidence


def persist_venice_review(task: str, proposal: dict, review: dict) -> Path:
    """Append durable proof that Venice was actually consulted before stopping."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    ev = review.get("freshEvidence") or {}
    compact = {
        "schema": "adam-venice-stop-review-v1",
        "createdAtEpoch": int(time.time()),
        "taskSha256": hashlib.sha256(task.encode("utf-8")).hexdigest(),
        "task": task[:4000],
        "proposal": proposal,
        "verdict": review.get("verdict"),
        "directive": review.get("directive"),
        "stopPermissionGranted": review.get("stopPermissionGranted") is True,
        "externalReviewGateSatisfied": review.get("externalReviewGateSatisfied") is True,
        "codeReviewFirst": review.get("codeReviewFirst") is True,
        "judgmentJarApplied": review.get("judgmentJarApplied") or [],
        "findings": review.get("findings") or [],
        "reviewText": str(review.get("reviewText") or "")[:8000],
        "baseCommit": ev.get("baseCommit"),
        "headCommit": ev.get("headCommit"),
        "diffFullSha256": ev.get("diffFullSha256"),
    }
    history = STATE_DIR / "venice-reviews.jsonl"
    with history.open("a", encoding="utf-8") as f:
        f.write(json.dumps(compact, ensure_ascii=False, sort_keys=True) + "\n")
    last = STATE_DIR / "venice-review-last.json"
    tmp = last.with_suffix(".tmp")
    tmp.write_text(json.dumps(compact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(last)
    return last


def parse_canonical_review_compat(raw: str):
    verdict, directive, findings, jars = canonical_venice.parse_review(raw)
    malformed = {"reviewer_output_missing_strict_verdict", "reviewer_output_missing_strict_directive", "inconsistent_pass_directive", "fail_cannot_allow_stop"}
    if not any(f in malformed for f in findings):
        return verdict, directive, findings, jars, raw
    obj = worker.parse_action(raw)
    if not isinstance(obj, dict):
        return verdict, directive, findings, jars, raw
    v = str(obj.get("verdict") or "").upper()
    d = str(obj.get("directive") or "").upper()
    if v not in {"PASS", "FAIL"} or d not in canonical_venice.DIRECTIVES:
        return verdict, directive, findings, jars, raw
    jar_value = obj.get("jar") or obj.get("judgmentJar") or obj.get("criterion") or "observable evidence"
    finding = obj.get("finding") or ""
    note = obj.get("note") or obj.get("critique") or ""
    normalized = f"VERDICT: {v}\nDIRECTIVE: {d}\nJAR: {jar_value}\n"
    if finding:
        normalized += f"FINDING: {finding}\n"
    normalized += f"NOTE: {note}"
    verdict, directive, findings, jars = canonical_venice.parse_review(normalized)
    return verdict, directive, findings, jars, normalized


def canonical_venice_review(task: str, workspace: Path, proposal: dict, jars: str, recent_messages: list[dict], task_base_commit: str | None, attempts: int = 4) -> dict:
    ev = git_evidence(workspace, task_base_commit)
    code_changed = bool(ev.get("codeChanged"))
    checks = [{"name": "git_diff_check", "ok": ev.get("diffCheckRc") in (0, None), "detail": ev.get("diffCheck", "")}]
    if not ev.get("isGitRepo"):
        checks.append({"name": "repository_identity", "ok": True, "detail": "non-repository task"})
    acceptance = json.dumps({
        "commission": task,
        "proposedTerminalAction": proposal,
        "recentWorkerEvidence": recent_messages[-12:],
        "knownEvidenceGaps": ["deployment/runtime claims require fresh surface evidence"] if code_changed else [],
    }, ensure_ascii=False, indent=2)
    diff = str(ev.get("diff") or "(no repository delta; conversational/non-code stop proposal)")
    base = str(ev.get("baseCommit") or "NON_GIT")
    head_commit = str(ev.get("headCommit") or "NON_GIT")
    full_hash = str(ev.get("diffFullSha256") or hashlib.sha256(diff.encode()).hexdigest())
    head = head_commit if not ev.get("status") else f"{head_commit}+WORKTREE:{full_hash[:16]}"
    prompt = canonical_venice.review_prompt(diff, acceptance, checks, bool(ev.get("diffTruncated")), jars, base, head, full_hash)
    if code_changed:
        prompt += "\n\nPRIORITY OVERRIDE: code/config changed. Review correctness/regression first. Do not permit stopping merely because tests are green."
    messages = [
        {"role": "system", "content": "You are Venice executing the canonical repository Judgment-Jar stop protocol. Return VERDICT/DIRECTIVE/JAR/FINDING/NOTE only."},
        {"role": "user", "content": prompt},
    ]
    result = None
    for _ in range(max(1, attempts)):
        raw = worker.call_model(messages, timeout=120)
        verdict, directive, findings, applied, normalized = parse_canonical_review_compat(raw)
        malformed = {"reviewer_output_missing_strict_verdict", "reviewer_output_missing_strict_directive", "inconsistent_pass_directive", "fail_cannot_allow_stop"}
        if not any(f in malformed for f in findings):
            stop = verdict == "PASS" and directive == "STOP_ALLOWED" and all(bool(c.get("ok")) for c in checks)
            result = {
                "schema": "venice-code-review-v2-phone",
                "verdict": verdict,
                "directive": directive,
                "stopPermissionGranted": stop,
                "continuationRequired": directive == "CONTINUE_REQUIRED",
                "haltRequired": directive == "HALT_REQUIRED",
                "externalReviewGateSatisfied": stop,
                "judgmentJarApplied": applied,
                "findings": findings,
                "reviewText": normalized,
                "codeReviewFirst": code_changed,
                "freshEvidence": ev,
            }
            break
        messages.append({"role": "assistant", "content": raw})
        messages.append({"role": "user", "content": "Malformed Venice review. Return only the canonical review fields; fail closed."})
    if result is None:
        result = {
            "schema": "venice-code-review-v2-phone",
            "verdict": "FAIL",
            "directive": "HALT_REQUIRED",
            "stopPermissionGranted": False,
            "continuationRequired": False,
            "haltRequired": True,
            "externalReviewGateSatisfied": False,
            "judgmentJarApplied": ["unknowns remain unknown"],
            "findings": ["canonical_venice_review_unavailable_after_recovery"],
            "reviewText": "",
            "codeReviewFirst": code_changed,
            "freshEvidence": ev,
        }
    result["receipt"] = str(persist_venice_review(task, proposal, result))
    return result


def checkpoint(task: str, workspace: Path, step: int, messages: list[dict], task_base_commit: str | None) -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    _, loaded = codex_local_documents(workspace)
    payload = {
        "schema": "adam-daemon-checkpoint-v3",
        "task": task,
        "workspace": str(workspace),
        "taskBaseCommit": task_base_commit,
        "step": step,
        "updatedAtEpoch": int(time.time()),
        "codexLocalDocuments": loaded,
        "gitEvidence": git_evidence(workspace, task_base_commit),
        "recentMessages": messages[-8:],
    }
    path = STATE_DIR / "current.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def run_task(task: str, workspace: Path, max_steps: int | None = None, stop_after_steps: int | None = None) -> int:
    """Run indefinitely in production; stop_after_steps exists only for bounded tests."""
    jars = worker.active_jars()
    if "Venice Completion and Code Review Gate" not in jars:
        raise RuntimeError("Venice completion-review Jar missing; stopping disabled")
    if "Daemon Persistence and Connector Backoff" not in jars:
        raise RuntimeError("daemon/backoff Jar missing; worker persistence unavailable")
    codex_docs, codex_loaded = codex_local_documents(workspace)
    interval = max(8, int(max_steps or CHECKPOINT_STEPS))
    initial_ev = git_evidence(workspace)
    task_base_commit = str(initial_ev.get("headCommit") or "") if initial_ev.get("isGitRepo") else None
    original_call = worker.call_model
    worker.call_model = lambda messages, timeout=120: resilient_call_model(original_call, messages, timeout)
    try:
        messages = [
            {"role": "system", "content": worker.SYSTEM + "\n\nACTIVE JUDGEMENT JARS (binding):\n" + jars + "\n\nCODEX LOCAL STEERING DOCUMENTS (binding):\n" + codex_docs},
            {"role": "user", "content": f"TASK FROM DREW:\n{task}\n\nTASK_BASE_COMMIT: {task_base_commit or 'NON_GIT'}\nCODEX_DOCS_LOADED: {json.dumps(codex_loaded)}\n\nINITIAL OBSERVATION:\n{worker.initial_observation(workspace)}"},
        ]
        format_failures = 0
        step = 0
        while True:
            step += 1
            if stop_after_steps is not None and step > stop_after_steps:
                path = checkpoint(task, workspace, step, messages, task_base_commit)
                print(f"Adam [acceptance-boundary]: bounded test harness stopped after {stop_after_steps} actions; production mission remains checkpointed at {path}.")
                return 3
            raw = worker.call_model(messages)
            action = worker.parse_action(raw)
            if action is None:
                format_failures += 1
                if format_failures >= 2 and raw.strip():
                    candidate = {"tool": "respond", "text": raw.strip()}
                    review = canonical_venice_review(task, workspace, candidate, jars, messages, task_base_commit)
                    if review.get("stopPermissionGranted"):
                        print(raw.strip())
                        return 0
                    if review.get("continuationRequired"):
                        messages.append({"role": "assistant", "content": raw})
                        messages.append({"role": "user", "content": "VENICE REVIEW: stopping denied. " + json.dumps({"findings": review.get("findings"), "reviewText": review.get("reviewText"), "receipt": review.get("receipt")}, ensure_ascii=False) + "\nEmit one valid typed action. Prose can talk only after Venice approval and can never execute."})
                        format_failures = 0
                        continue
                    path = checkpoint(task, workspace, step, messages, task_base_commit)
                    print(f"Adam [halted]: Venice review path could not authorize prose fallback; checkpoint={path}; receipt={review.get('receipt')}; findings={review.get('findings')}")
                    return 2
                messages.append({"role": "assistant", "content": raw})
                messages.append({"role": "user", "content": "FORMAT_ERROR: emit exactly one allowed tool JSON object."})
                if format_failures % 4 == 0:
                    path = checkpoint(task, workspace, step, messages, task_base_commit)
                    messages.append({"role": "user", "content": f"DAEMON_CHECKPOINT: state persisted at {path}. Slow down; continue the same mission."})
                    time.sleep(1)
                continue
            format_failures = 0
            messages.append({"role": "assistant", "content": json.dumps(action, ensure_ascii=False)})
            tool = str(action.get("tool") or "").strip()
            if tool in {"finish", "respond"}:
                review = canonical_venice_review(task, workspace, action, jars, messages, task_base_commit)
                if not review.get("stopPermissionGranted"):
                    if review.get("continuationRequired"):
                        messages.append({"role": "user", "content": "TOOL OBSERVATION:\n" + json.dumps({
                            "ok": False,
                            "reviewGate": "venice",
                            "directive": "CONTINUE_REQUIRED",
                            "findings": review.get("findings"),
                            "reviewText": review.get("reviewText"),
                            "receipt": review.get("receipt"),
                            "message": "Venice denied stopping. Repair the same slice and return for review.",
                        }, ensure_ascii=False)})
                        continue
                    path = checkpoint(task, workspace, step, messages, task_base_commit)
                    print(f"Adam [halted]: Venice returned HALT_REQUIRED; checkpoint={path}; receipt={review.get('receipt')}; findings={review.get('findings')}")
                    return 2
                terminal, result = worker.execute_tool(workspace, action)
                if result.get("terminal") == "finish":
                    status = result.get("status", "partial")
                    print(f"Adam [{status}]: {str(result.get('text') or '').strip()}\nVenice review: STOP_ALLOWED. externalReviewGateSatisfied=true. receipt={review.get('receipt')}")
                    return 0 if status == "done" else 2 if status == "blocked" else 1
                print(str(result.get("text") or "").strip())
                return 0
            terminal, observation = worker.execute_tool(workspace, action)
            if terminal:
                messages.append({"role": "user", "content": "TOOL OBSERVATION: unexpected unreviewed terminal action was blocked."})
                continue
            messages.append({"role": "user", "content": "TOOL OBSERVATION:\n" + json.dumps(observation, ensure_ascii=False)})
            if step % interval == 0:
                path = checkpoint(task, workspace, step, messages, task_base_commit)
                messages.append({"role": "user", "content": f"DAEMON_CHECKPOINT: mission remains active after {step} actions; state={path}. Time/action count is not permission to stop."})
                time.sleep(1)
    finally:
        worker.call_model = original_call


def run_interactive(cwd: str | None = None) -> int:
    workspace = Path(cwd or Path.cwd()).expanduser().resolve()
    if not workspace.is_dir():
        workspace = ROOT
    print("Adam worker online. Codex-local docs loaded per task. Jar-governed. Daemon persistent. Venice reviews every stop with receipts.")
    while True:
        try:
            text = input(f"adam {workspace}$ ")
        except EOFError:
            print()
            return 0
        except KeyboardInterrupt:
            print("\n^C")
            continue
        stripped = text.strip()
        if not stripped:
            continue
        if stripped in {":exit", ":quit"}:
            return 0
        if stripped == ":help":
            print(worker.help_text() + "\nCodex local steering loads AGENTS/MEMORIES/SKILLS. Every terminal response requires canonical Venice review and a durable receipt.")
            continue
        if stripped == ":status":
            try:
                jars = worker.active_jars()
                _, loaded = codex_local_documents(workspace)
                venice = "Venice Completion and Code Review Gate" in jars
                daemon = "Daemon Persistence and Connector Backoff" in jars
                error = ""
            except Exception as exc:
                loaded = []
                venice = daemon = False
                error = str(exc)
            print(json.dumps({
                "schema": "adam-venice-reviewed-status-v8",
                "workspace": str(workspace),
                "model": worker.PHONE_LLM_MODEL,
                "codexLocalDocuments": loaded,
                "jarGate": venice and daemon,
                "veniceProtocol": "tools/venice_review.py",
                "veniceStopReview": venice,
                "veniceLastReceipt": str(STATE_DIR / "venice-review-last.json"),
                "veniceHistory": str(STATE_DIR / "venice-reviews.jsonl"),
                "daemonPersistence": daemon,
                "checkpointSteps": CHECKPOINT_STEPS,
                "checkpoint": str(STATE_DIR / "current.json"),
                "backoffSeconds": list(BACKOFF_SECONDS),
                "error": error,
            }, indent=2))
            continue
        if stripped == ":cwd" or stripped.startswith(":cwd "):
            raw = stripped[len(":cwd"):].strip()
            target = (workspace / raw).resolve() if raw and not Path(raw).expanduser().is_absolute() else Path(raw or workspace).expanduser().resolve()
            if target.is_dir():
                workspace = target
                print(f"Adam: workspace {workspace}")
            else:
                print(f"Adam: not a directory: {target}")
            continue
        try:
            run_task(text, workspace)
        except Exception as exc:
            ev = git_evidence(workspace)
            base = str(ev.get("headCommit") or "") if ev.get("isGitRepo") else None
            path = checkpoint(text, workspace, -1, [{"role": "system", "content": "runtime exception"}, {"role": "user", "content": str(exc)}], base)
            print(f"Adam [blocked-current-process]: mission preserved at {path}: {exc}")


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args:
        return run_task(" ".join(args), Path.cwd().resolve())
    return run_interactive()


if __name__ == "__main__":
    raise SystemExit(main())
