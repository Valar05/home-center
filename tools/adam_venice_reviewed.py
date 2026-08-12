#!/usr/bin/env python3
"""Venice-reviewed wrapper around the Codex-shaped Adam phone worker.

This module makes completion review a runtime invariant rather than a prompt
suggestion. Any terminal `finish` or `respond` proposed by Adam is intercepted,
reviewed by a separate Venice pass using the active Judgement Jars, and denied
unless Venice explicitly approves stopping.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import adam_codex_phone as worker

VENICE_SYSTEM = r'''You are Venice acting as an independent completion reviewer for Drew.
You are not Adam and you do not protect Adam's feelings. Apply the supplied active Judgement Jars.
Your job is to decide whether the worker may stop and whether the work is actually good.

When repository code/config changed, CODE REVIEW IS FIRST PRIORITY. Inspect the supplied status/diff before personality, prose, or praise. Check mission fidelity, regression risk, correctness, validation evidence, runtime truth, durability/recovery, simplicity, and only then maintainability/quality.

For non-code work, apply the same evidence-first standard without inventing a code requirement.

Return exactly one JSON object and nothing else:
{"verdict":"approve|continue","quality":"good|mixed|poor","code_review_first":true|false,"critique":"specific evidence-grounded review","next":"empty when approved; concrete next action when continuing"}

Approve only when the current bounded slice is genuinely allowed to stop. If work is incomplete, weakly verified, self-congratulatory, or source-only while claiming runtime success, return continue. Drew remains final acceptance authority.
'''


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


def venice_review(task: str, workspace: Path, proposal: dict, jars: str, attempts: int = 3) -> dict:
    evidence = git_evidence(workspace)
    messages = [
        {"role": "system", "content": VENICE_SYSTEM + "\n\nACTIVE JUDGEMENT JARS (binding):\n" + jars},
        {
            "role": "user",
            "content": "REVIEW THIS WORKER STOP PROPOSAL:\n" + json.dumps({
                "taskFromDrew": task,
                "proposedTerminalAction": proposal,
                "freshEvidence": evidence,
            }, ensure_ascii=False),
        },
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
    return {
        "verdict": "continue",
        "quality": "poor",
        "code_review_first": bool(evidence.get("codeChanged")),
        "critique": "Venice review protocol failed to return a valid governed verdict; stopping is denied.",
        "next": "Recover the Venice review path and retry completion review.",
        "freshEvidence": evidence,
    }


def run_task(task: str, workspace: Path, max_steps: int = worker.MAX_STEPS) -> int:
    jars = worker.active_jars()
    original_execute = worker.execute_tool

    def reviewed_execute(ws: Path, action: dict):
        tool = str(action.get("tool") or "").strip()
        if tool not in {"finish", "respond"}:
            return original_execute(ws, action)
        review = venice_review(task, ws, action, jars)
        if review.get("verdict") != "approve":
            return False, {
                "ok": False,
                "reviewGate": "venice",
                "verdict": "continue",
                "quality": review.get("quality"),
                "codeReviewFirst": review.get("code_review_first"),
                "critique": review.get("critique"),
                "next": review.get("next"),
                "message": "Venice denied stopping. Continue the worker loop and address this review.",
            }
        terminal, result = original_execute(ws, action)
        result = dict(result)
        result["veniceReview"] = {
            "verdict": "approve",
            "quality": review.get("quality"),
            "codeReviewFirst": review.get("code_review_first"),
            "critique": review.get("critique"),
        }
        # Keep the user-visible finish concise but prove the gate happened.
        if result.get("terminal") == "finish":
            text = result.get("text", "")
            result["text"] = f"{text}\nVenice review: approved ({review.get('quality')}). {review.get('critique')}".strip()
        return terminal, result

    worker.execute_tool = reviewed_execute
    try:
        return worker.run_task(task, workspace, max_steps=max_steps)
    finally:
        worker.execute_tool = original_execute


def run_interactive(cwd: str | None = None) -> int:
    workspace = Path(cwd or Path.cwd()).expanduser().resolve()
    if not workspace.is_dir():
        workspace = ROOT
    print("Adam worker online. Codex loop. Jar-governed. Venice reviews every stop.")
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
            print(worker.help_text() + "\nEvery terminal response is independently reviewed by Venice before Adam may stop.")
            continue
        if stripped == ":status":
            try:
                jars = worker.active_jars()
                gate = "Venice Completion and Code Review Gate" in jars
                error = ""
            except Exception as exc:
                gate = False
                error = str(exc)
            print(json.dumps({"schema":"adam-venice-reviewed-status-v1","workspace":str(workspace),"model":worker.PHONE_LLM_MODEL,"jarGate":gate,"veniceStopReview":gate,"error":error}, indent=2))
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
            print(f"Adam [blocked]: worker runtime failure: {exc}")


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args:
        return run_task(" ".join(args), Path.cwd().resolve())
    return run_interactive()


if __name__ == "__main__":
    raise SystemExit(main())
