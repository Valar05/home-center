#!/usr/bin/env python3
"""Venice-reviewed, daemon-persistent wrapper for the Codex-shaped Adam phone worker.

Terminal `finish`/`respond` actions are intercepted and reviewed by a separate
Venice pass using active Judgement Jars. Transient model failures back off.
The action budget is a durable checkpoint interval, never permission to quit.
"""
from __future__ import annotations

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

CHECKPOINT_STEPS = int(os.environ.get("HC_ADAM_CHECKPOINT_STEPS", "48"))
BACKOFF_SECONDS = (1, 2, 4, 8, 15, 30)
STATE_DIR = Path(os.path.expanduser(os.environ.get("HC_STATE_DIR", "~/.local/state/home-center"))) / "adam-daemon"

VENICE_SYSTEM = r'''You are Venice acting as an independent completion reviewer for Drew.
You are not Adam and you do not protect Adam's feelings. Apply the supplied active Judgement Jars.
Your job is to decide whether the worker may stop and whether the work is actually good.

When repository code/config changed, CODE REVIEW IS FIRST PRIORITY. Inspect the supplied status/diff before personality, prose, or praise. Check mission fidelity, regression risk, correctness, validation evidence, runtime truth, durability/recovery, simplicity, and only then maintainability/quality.

For non-code work, apply the same evidence-first standard without inventing a code requirement.

Return exactly one JSON object and nothing else:
{"verdict":"approve|continue","quality":"good|mixed|poor","code_review_first":true|false,"critique":"specific evidence-grounded review","next":"empty when approved; concrete next action when continuing"}

Approve only when the current bounded slice is genuinely allowed to stop. If work is incomplete, weakly verified, self-congratulatory, or source-only while claiming runtime success, return continue. Drew remains final acceptance authority.
'''


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
        root = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=workspace, text=True, capture_output=True, timeout=10)
        if root.returncode != 0:
            evidence["gitError"] = worker.clipped(root.stderr or root.stdout, 2000)
            return evidence
        evidence["isGitRepo"] = True
        evidence["gitRoot"] = root.stdout.strip()
        status = subprocess.run(["git", "status", "--short"], cwd=workspace, text=True, capture_output=True, timeout=10)
        diff = subprocess.run(["git", "diff", "--no-ext-diff"], cwd=workspace, text=True, capture_output=True, timeout=20)
        staged = subprocess.run(["git", "diff", "--cached", "--no-ext-diff"], cwd=workspace, text=True, capture_output=True, timeout=20)
        check = subprocess.run(["git", "diff", "--check"], cwd=workspace, text=True, capture_output=True, timeout=20)
        status_text = status.stdout
        combined_diff = (diff.stdout or "") + ("\n--- STAGED ---\n" + staged.stdout if staged.stdout else "")
        evidence["status"] = worker.clipped(status_text, 6000)
        evidence["diff"] = worker.clipped(combined_diff, 18000)
        evidence["diffCheckRc"] = check.returncode
        evidence["diffCheck"] = worker.clipped((check.stdout or "") + (check.stderr or ""), 4000)
        code_ext = (".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".java", ".kt", ".kts", ".sh", ".ps1", ".json", ".yaml", ".yml", ".toml", ".gradle", ".xml")
        changed_paths = []
        for line in status_text.splitlines():
            path = line[3:].strip() if len(line) > 3 else ""
            if " -> " in path:
                path = path.split(" -> ", 1)[1]
            if path:
                changed_paths.append(path)
        evidence["changedPaths"] = changed_paths
        evidence["codeChanged"] = any(p.lower().endswith(code_ext) or p.startswith(".continue/") for p in changed_paths)
    except Exception as exc:
        evidence["gitError"] = str(exc)
    return evidence


def parse_review(raw: str) -> dict | None:
    obj = worker.parse_action(raw)
    if not isinstance(obj, dict):
        return None
    verdict = str(obj.get("verdict") or "").strip().lower()
    quality = str(obj.get("quality") or "").strip().lower()
    if verdict not in {"approve", "continue"} or quality not in {"good", "mixed", "poor"}:
        return None
    obj["verdict"] = verdict
    obj["quality"] = quality
    obj["code_review_first"] = bool(obj.get("code_review_first"))
    obj["critique"] = str(obj.get("critique") or "").strip()
    obj["next"] = str(obj.get("next") or "").strip()
    return obj


def venice_review(task: str, workspace: Path, proposal: dict, jars: str, attempts: int = 4) -> dict:
    evidence = git_evidence(workspace)
    messages = [
        {"role": "system", "content": VENICE_SYSTEM + "\n\nACTIVE JUDGEMENT JARS (binding):\n" + jars},
        {"role": "user", "content": "REVIEW THIS WORKER STOP PROPOSAL:\n" + json.dumps({"taskFromDrew": task, "proposedTerminalAction": proposal, "freshEvidence": evidence}, ensure_ascii=False)},
    ]
    for _ in range(max(1, attempts)):
        raw = worker.call_model(messages, timeout=120)
        review = parse_review(raw)
        if review is not None:
            if evidence.get("codeChanged") and not review.get("code_review_first"):
                messages.append({"role": "assistant", "content": raw})
                messages.append({"role": "user", "content": "REVIEW_FORMAT_ERROR: code/config changed, so code_review_first must be true. Re-review the actual diff first and return the required JSON."})
                continue
            review["freshEvidence"] = evidence
            return review
        messages.append({"role": "assistant", "content": raw})
        messages.append({"role": "user", "content": "REVIEW_FORMAT_ERROR: Return exactly the Venice review JSON object. No prose outside JSON."})
    return {"verdict": "continue", "quality": "poor", "code_review_first": bool(evidence.get("codeChanged")), "critique": "Venice review protocol did not return a valid governed verdict; stopping is denied.", "next": "Recover the Venice review path and retry completion review.", "freshEvidence": evidence}


def checkpoint(task: str, workspace: Path, step: int, messages: list[dict]) -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "adam-daemon-checkpoint-v1",
        "task": task,
        "workspace": str(workspace),
        "step": step,
        "updatedAtEpoch": int(time.time()),
        "gitEvidence": git_evidence(workspace),
        "recentMessages": messages[-8:],
    }
    path = STATE_DIR / "current.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def run_task(task: str, workspace: Path, max_steps: int | None = None) -> int:
    """Run until a Venice-approved terminal action. max_steps is a checkpoint interval compatibility alias."""
    jars = worker.active_jars()
    if "Venice Completion and Code Review Gate" not in jars:
        raise RuntimeError("Venice completion-review Jar is not loaded; stopping is disabled")
    if "Daemon Persistence and Connector Backoff" not in jars:
        raise RuntimeError("daemon/backoff Jar is not loaded; worker persistence contract unavailable")
    interval = max(8, int(max_steps or CHECKPOINT_STEPS))
    original_call = worker.call_model
    worker.call_model = lambda messages, timeout=120: resilient_call_model(original_call, messages, timeout)
    try:
        messages = [
            {"role": "system", "content": worker.SYSTEM + "\n\nACTIVE JUDGEMENT JARS (binding):\n" + jars},
            {"role": "user", "content": f"TASK FROM DREW:\n{task}\n\nINITIAL OBSERVATION:\n{worker.initial_observation(workspace)}"},
        ]
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
                review = venice_review(task, workspace, action, jars)
                if review.get("verdict") != "approve":
                    observation = {"ok": False, "reviewGate": "venice", "verdict": "continue", "quality": review.get("quality"), "codeReviewFirst": review.get("code_review_first"), "critique": review.get("critique"), "next": review.get("next"), "message": "Venice denied stopping. Continue the worker loop and address this review."}
                    messages.append({"role": "user", "content": "TOOL OBSERVATION:\n" + json.dumps(observation, ensure_ascii=False)})
                    continue
                terminal, result = worker.execute_tool(workspace, action)
                if not terminal:
                    messages.append({"role": "user", "content": "TOOL OBSERVATION:\n" + json.dumps(result, ensure_ascii=False)})
                    continue
                if result.get("terminal") == "finish":
                    text = str(result.get("text") or "").strip()
                    print(f"Adam [{result.get('status','partial')}]: {text}\nVenice review: approved ({review.get('quality')}). {review.get('critique')}")
                    status = result.get("status", "partial")
                    return 0 if status == "done" else 2 if status == "blocked" else 1
                print(str(result.get("text") or "").strip())
                return 0
            terminal, observation = worker.execute_tool(workspace, action)
            if terminal:
                # Defensive invariant: only finish/respond are terminal tools.
                messages.append({"role": "user", "content": "TOOL OBSERVATION:\n" + json.dumps({"ok": False, "error": "unexpected unreviewed terminal tool blocked"}, ensure_ascii=False)})
                continue
            messages.append({"role": "user", "content": "TOOL OBSERVATION:\n" + json.dumps(observation, ensure_ascii=False)})
            if step % interval == 0:
                path = checkpoint(task, workspace, step, messages)
                messages.append({"role": "user", "content": f"DAEMON_CHECKPOINT: mission remains active after {step} actions. State persisted at {path}. Do not treat elapsed time or action count as permission to stop; continue deliberately."})
                time.sleep(1)
    finally:
        worker.call_model = original_call


def run_interactive(cwd: str | None = None) -> int:
    workspace = Path(cwd or Path.cwd()).expanduser().resolve()
    if not workspace.is_dir():
        workspace = ROOT
    print("Adam worker online. Codex loop. Jar-governed. Daemon persistent. Venice reviews every stop.")
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
            print(worker.help_text() + "\nEvery terminal response is independently reviewed by Venice. Long work checkpoints and continues; transient model failures back off.")
            continue
        if stripped == ":status":
            try:
                jars = worker.active_jars()
                venice = "Venice Completion and Code Review Gate" in jars
                daemon = "Daemon Persistence and Connector Backoff" in jars
                error = ""
            except Exception as exc:
                venice = daemon = False
                error = str(exc)
            print(json.dumps({"schema":"adam-venice-reviewed-status-v3","workspace":str(workspace),"model":worker.PHONE_LLM_MODEL,"jarGate":venice and daemon,"veniceStopReview":venice,"daemonPersistence":daemon,"checkpointSteps":CHECKPOINT_STEPS,"checkpoint":str(STATE_DIR / 'current.json'),"backoffSeconds":list(BACKOFF_SECONDS),"error":error}, indent=2))
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
            path = checkpoint(text, workspace, -1, [{"role":"system","content":"runtime exception"},{"role":"user","content":str(exc)}])
            print(f"Adam [blocked-current-process]: runtime failed after daemon recovery attempts; mission checkpoint preserved at {path}: {exc}")


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args:
        return run_task(" ".join(args), Path.cwd().resolve())
    return run_interactive()


if __name__ == "__main__":
    raise SystemExit(main())
