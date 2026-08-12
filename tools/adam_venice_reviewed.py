#!/usr/bin/env python3
"""Codex-shaped Adam worker with canonical Venice completion review and daemon persistence.

Bare Adam executes tools until a terminal action is proposed. Stopping is then
governed by the repository's canonical tools/venice_review.py protocol. The
phone-local model is only the inference transport for that protocol when Adam is
running on Termux; the review schema/laws/parser remain canonical.
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


def git_evidence(workspace: Path) -> dict:
    evidence: dict[str, object] = {"workspace": str(workspace), "isGitRepo": False, "codeChanged": False}
    try:
        root_p = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=workspace, text=True, capture_output=True, timeout=10)
        if root_p.returncode != 0:
            evidence["gitError"] = worker.clipped(root_p.stderr or root_p.stdout, 2000)
            return evidence
        root = Path(root_p.stdout.strip())
        evidence["isGitRepo"] = True
        evidence["gitRoot"] = str(root)
        base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, timeout=10)
        evidence["baseCommit"] = base.stdout.strip() if base.returncode == 0 else "UNKNOWN"
        status = subprocess.run(["git", "status", "--short"], cwd=root, text=True, capture_output=True, timeout=10)
        unstaged = subprocess.run(["git", "diff", "--no-ext-diff"], cwd=root, text=True, capture_output=True, timeout=20)
        staged = subprocess.run(["git", "diff", "--cached", "--no-ext-diff"], cwd=root, text=True, capture_output=True, timeout=20)
        check = subprocess.run(["git", "diff", "--check", "HEAD"], cwd=root, text=True, capture_output=True, timeout=20)
        status_text = status.stdout
        combined = (unstaged.stdout or "") + ("\n--- STAGED ---\n" + staged.stdout if staged.stdout else "")
        changed_paths = []
        untracked_sections = []
        for line in status_text.splitlines():
            path_text = line[3:].strip() if len(line) > 3 else ""
            if " -> " in path_text:
                path_text = path_text.split(" -> ", 1)[1]
            if not path_text:
                continue
            changed_paths.append(path_text)
            if line.startswith("??"):
                p = root / path_text
                if p.is_file() and p.stat().st_size <= 120000:
                    try:
                        untracked_sections.append(f"\n--- UNTRACKED {path_text} ---\n" + p.read_text(encoding="utf-8", errors="replace"))
                    except Exception:
                        pass
        combined += "".join(untracked_sections)
        evidence["status"] = worker.clipped(status_text, 6000)
        evidence["diff"] = worker.clipped(combined, 28000)
        evidence["diffFullSha256"] = hashlib.sha256(combined.encode()).hexdigest()
        evidence["diffTruncated"] = len(combined) > 28000
        evidence["diffCheckRc"] = check.returncode
        evidence["diffCheck"] = worker.clipped((check.stdout or "") + (check.stderr or ""), 4000)
        evidence["changedPaths"] = changed_paths
        code_ext = (".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".java", ".kt", ".kts", ".sh", ".ps1", ".json", ".yaml", ".yml", ".toml", ".gradle", ".xml")
        evidence["codeChanged"] = any(p.lower().endswith(code_ext) or p.startswith(".continue/") for p in changed_paths)
    except Exception as exc:
        evidence["gitError"] = str(exc)
    return evidence


def canonical_venice_review(task: str, workspace: Path, proposal: dict, jars: str, recent_messages: list[dict], attempts: int = 4) -> dict:
    ev = git_evidence(workspace)
    code_changed = bool(ev.get("codeChanged"))
    checks = [{"name": "git_diff_check", "ok": ev.get("diffCheckRc") in (0, None), "detail": ev.get("diffCheck", "")}]
    if not ev.get("isGitRepo"):
        checks.append({"name": "repository_identity", "ok": True, "detail": "non-repository task; code review not applicable"})
    acceptance = json.dumps({
        "commission": task,
        "proposedTerminalAction": proposal,
        "recentWorkerEvidence": recent_messages[-12:],
        "knownEvidenceGaps": ["working-tree review; deployed/runtime state requires separate fresh evidence"] if code_changed else [],
    }, ensure_ascii=False, indent=2)
    diff = str(ev.get("diff") or "(no repository diff; review conversational/non-code stop proposal)")
    base = str(ev.get("baseCommit") or "NON_GIT")
    head = "WORKTREE:" + str(ev.get("diffFullSha256") or hashlib.sha256(diff.encode()).hexdigest())[:16]
    prompt = canonical_venice.review_prompt(
        diff,
        acceptance,
        checks,
        bool(ev.get("diffTruncated")),
        jars,
        base,
        head,
        str(ev.get("diffFullSha256") or hashlib.sha256(diff.encode()).hexdigest()),
    )
    if code_changed:
        prompt += "\n\nPRIORITY OVERRIDE: repository code/config changed. Perform code review first and name the most important correctness/regression issue before any style observation."
    messages = [{"role": "system", "content": "You are Venice executing the canonical repository code-review/stop protocol. Return exactly the required VERDICT/DIRECTIVE/JAR/FINDING/NOTE text format."}, {"role": "user", "content": prompt}]
    for _ in range(max(1, attempts)):
        raw = worker.call_model(messages, timeout=120)
        verdict, directive, findings, jar_applied = canonical_venice.parse_review(raw)
        valid = not any(f in findings for f in ("reviewer_output_missing_strict_verdict", "reviewer_output_missing_strict_directive", "inconsistent_pass_directive", "fail_cannot_allow_stop"))
        if valid:
            stop = verdict == "PASS" and directive == "STOP_ALLOWED" and all(bool(c.get("ok")) for c in checks)
            return {"schema": "venice-code-review-v2-phone", "verdict": verdict, "directive": directive, "stopPermissionGranted": stop, "continuationRequired": directive == "CONTINUE_REQUIRED", "haltRequired": directive == "HALT_REQUIRED", "externalReviewGateSatisfied": stop, "judgmentJarApplied": jar_applied, "findings": findings, "reviewText": raw, "codeReviewFirst": code_changed, "freshEvidence": ev}
        messages.append({"role": "assistant", "content": raw})
        messages.append({"role": "user", "content": "Malformed canonical review. Return exactly VERDICT, DIRECTIVE, at least one JAR, optional FINDING, and NOTE. Fail closed rather than improvising."})
    return {"schema": "venice-code-review-v2-phone", "verdict": "FAIL", "directive": "HALT_REQUIRED", "stopPermissionGranted": False, "continuationRequired": False, "haltRequired": True, "externalReviewGateSatisfied": False, "judgmentJarApplied": ["unknowns remain unknown"], "findings": ["canonical_venice_review_unavailable_after_recovery"], "reviewText": "", "codeReviewFirst": code_changed, "freshEvidence": ev}


def checkpoint(task: str, workspace: Path, step: int, messages: list[dict]) -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"schema": "adam-daemon-checkpoint-v1", "task": task, "workspace": str(workspace), "step": step, "updatedAtEpoch": int(time.time()), "gitEvidence": git_evidence(workspace), "recentMessages": messages[-8:]}
    path = STATE_DIR / "current.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def run_task(task: str, workspace: Path, max_steps: int | None = None) -> int:
    jars = worker.active_jars()
    if "Venice Completion and Code Review Gate" not in jars:
        raise RuntimeError("Venice completion-review Jar is not loaded; stopping is disabled")
    if "Daemon Persistence and Connector Backoff" not in jars:
        raise RuntimeError("daemon/backoff Jar is not loaded; worker persistence contract unavailable")
    interval = max(8, int(max_steps or CHECKPOINT_STEPS))
    original_call = worker.call_model
    worker.call_model = lambda messages, timeout=120: resilient_call_model(original_call, messages, timeout)
    try:
        messages = [{"role": "system", "content": worker.SYSTEM + "\n\nACTIVE JUDGEMENT JARS (binding):\n" + jars}, {"role": "user", "content": f"TASK FROM DREW:\n{task}\n\nINITIAL OBSERVATION:\n{worker.initial_observation(workspace)}"}]
        format_failures = 0
        step = 0
        while True:
            step += 1
            raw = worker.call_model(messages)
            action = worker.parse_action(raw)
            if action is None:
                format_failures += 1
                messages.append({"role": "assistant", "content": raw})
                messages.append({"role": "user", "content": "FORMAT_ERROR: Output was not one valid JSON object. Do not talk. Emit exactly one allowed tool JSON object."})
                if format_failures % 4 == 0:
                    path = checkpoint(task, workspace, step, messages)
                    messages.append({"role": "user", "content": f"DAEMON_CHECKPOINT: format recovery continues; state persisted at {path}. Slow down and emit one valid typed action."})
                    time.sleep(1)
                continue
            format_failures = 0
            messages.append({"role": "assistant", "content": json.dumps(action, ensure_ascii=False)})
            tool = str(action.get("tool") or "").strip()
            if tool in {"finish", "respond"}:
                review = canonical_venice_review(task, workspace, action, jars, messages)
                if not review.get("stopPermissionGranted"):
                    if review.get("continuationRequired"):
                        observation = {"ok": False, "reviewGate": "venice", "directive": "CONTINUE_REQUIRED", "findings": review.get("findings"), "reviewText": review.get("reviewText"), "message": "Canonical Venice denied stopping. Continue the same commissioned slice and return for review."}
                        messages.append({"role": "user", "content": "TOOL OBSERVATION:\n" + json.dumps(observation, ensure_ascii=False)})
                        continue
                    path = checkpoint(task, workspace, step, messages)
                    print(f"Adam [halted]: canonical Venice review returned HALT_REQUIRED. Mission checkpoint preserved at {path}. Findings: {review.get('findings')}")
                    return 2
                terminal, result = worker.execute_tool(workspace, action)
                if not terminal:
                    messages.append({"role": "user", "content": "TOOL OBSERVATION:\n" + json.dumps(result, ensure_ascii=False)})
                    continue
                if result.get("terminal") == "finish":
                    text = str(result.get("text") or "").strip()
                    print(f"Adam [{result.get('status','partial')}]: {text}\nVenice review: STOP_ALLOWED. externalReviewGateSatisfied=true.")
                    status = result.get("status", "partial")
                    return 0 if status == "done" else 2 if status == "blocked" else 1
                print(str(result.get("text") or "").strip())
                return 0
            terminal, observation = worker.execute_tool(workspace, action)
            if terminal:
                messages.append({"role": "user", "content": "TOOL OBSERVATION:\n" + json.dumps({"ok": False, "error": "unexpected unreviewed terminal tool blocked"}, ensure_ascii=False)})
                continue
            messages.append({"role": "user", "content": "TOOL OBSERVATION:\n" + json.dumps(observation, ensure_ascii=False)})
            if step % interval == 0:
                path = checkpoint(task, workspace, step, messages)
                messages.append({"role": "user", "content": f"DAEMON_CHECKPOINT: mission remains active after {step} actions. State persisted at {path}. Elapsed time/action count is not permission to stop. Continue deliberately."})
                time.sleep(1)
    finally:
        worker.call_model = original_call


def run_interactive(cwd: str | None = None) -> int:
    workspace = Path(cwd or Path.cwd()).expanduser().resolve()
    if not workspace.is_dir():
        workspace = ROOT
    print("Adam worker online. Codex loop. Jar-governed. Daemon persistent. Canonical Venice reviews every stop.")
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
            print(worker.help_text() + "\nEvery terminal response passes tools/venice_review.py protocol. Long work checkpoints and continues; transient model failures back off.")
            continue
        if stripped == ":status":
            try:
                jars = worker.active_jars(); venice = "Venice Completion and Code Review Gate" in jars; daemon = "Daemon Persistence and Connector Backoff" in jars; error = ""
            except Exception as exc:
                venice = daemon = False; error = str(exc)
            print(json.dumps({"schema":"adam-venice-reviewed-status-v4","workspace":str(workspace),"model":worker.PHONE_LLM_MODEL,"jarGate":venice and daemon,"veniceProtocol":"tools/venice_review.py","veniceStopReview":venice,"daemonPersistence":daemon,"checkpointSteps":CHECKPOINT_STEPS,"checkpoint":str(STATE_DIR / 'current.json'),"backoffSeconds":list(BACKOFF_SECONDS),"error":error}, indent=2))
            continue
        if stripped == ":cwd" or stripped.startswith(":cwd "):
            raw = stripped[len(":cwd"):].strip(); target = (workspace / raw).resolve() if raw and not Path(raw).expanduser().is_absolute() else Path(raw or workspace).expanduser().resolve()
            if target.is_dir(): workspace = target; print(f"Adam: workspace {workspace}")
            else: print(f"Adam: not a directory: {target}")
            continue
        try:
            run_task(text, workspace)
        except Exception as exc:
            path = checkpoint(text, workspace, -1, [{"role":"system","content":"runtime exception"},{"role":"user","content":str(exc)}])
            print(f"Adam [blocked-current-process]: runtime failed after daemon recovery attempts; mission checkpoint preserved at {path}: {exc}")


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args:
        return run_task(" ".join(args), Path.cwd().resolve())
    return run_interactive()


if __name__ == "__main__":
    raise SystemExit(main())
