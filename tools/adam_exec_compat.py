#!/usr/bin/env python3
"""Compatibility entrypoint for Adam's tiny local phone model.

Structured model output may select a bounded action. Unstructured output is
conversation only and can never authorize execution.
"""
from __future__ import annotations
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import adam


def compatible_local_exec_plan(history: list[dict], text: str, cwd: str, timeout: int) -> dict:
    messages = [{"role": "system", "content": adam.EXEC_SYSTEM}]
    messages.extend(history[-12:])
    messages.append({"role": "user", "content": f"Current workspace: {cwd}\nUser: {text}"})
    payload = json.dumps({
        "model": adam.PHONE_LLM_MODEL,
        "messages": messages,
        "temperature": 0,
        "max_tokens": 260,
    }).encode("utf-8")
    req = urllib.request.Request(adam.PHONE_LLM_URL, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise RuntimeError(f"local executive unavailable: {exc}") from exc

    raw = adam.extract_local_message(body).strip()
    plan = None
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            plan = parsed
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.S)
        if match:
            try:
                parsed = json.loads(match.group(0))
                if isinstance(parsed, dict):
                    plan = parsed
            except json.JSONDecodeError:
                pass

    # Critical safety boundary: prose is allowed to talk, never to execute.
    if plan is None:
        return {"kind": "say", "say": raw or "I'm here.", "payload": "", "structure": "prose-fallback"}

    kind = str(plan.get("kind") or "").strip().lower()
    say = str(plan.get("say") or "").strip()
    action = str(plan.get("payload") or "").strip()
    if kind not in adam.EXEC_KINDS:
        return {"kind": "say", "say": raw or "I'm here.", "payload": "", "structure": "invalid-structure-fallback"}
    if kind == "say":
        action = ""
    elif not action:
        return {"kind": "say", "say": say or raw or "I need a clearer action.", "payload": "", "structure": "missing-payload-fallback"}
    if kind == "terminal" and adam.DANGEROUS_SHELL.search(action):
        return {"kind": "say", "say": "I won't execute that as an inferred shell action. Use :sh explicitly if you intend an exact command.", "payload": "", "structure": "blocked-action"}
    return {"kind": kind, "say": say, "payload": action, "structure": "typed"}


def main(argv=None) -> int:
    adam.local_exec_plan = compatible_local_exec_plan
    return adam.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
