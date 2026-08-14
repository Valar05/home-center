#!/usr/bin/env python3
"""Prompt-first phone entrypoint for Home Center/Adam.

Usage:
  adam-do "recover the old AI mentorship skill from Codex's drive and repair sync"
  printf '%s\n' "do the thing" | adam-do
  adam-do --chat "explain current state"
  adam-do --vlad "antagonize this plan"

The wrapper deliberately does not invent a new execution stack. It delegates to
Home Center's existing tools/adam.py router so prompts inherit the same Codex,
Venice, Judgment Jar, receipts, and deterministic phone orchestration contract.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def find_repo() -> Path:
    candidates = []
    if os.environ.get("HOME_CENTER_ROOT"):
        candidates.append(Path(os.environ["HOME_CENTER_ROOT"]).expanduser())
    wrapper_root = os.environ.get("ADAM_DO_REPO")
    if wrapper_root:
        candidates.append(Path(wrapper_root).expanduser())
    candidates.extend([
        Path.home() / "home-center",
        Path.home() / "src" / "home-center",
        Path.home() / "repos" / "home-center",
    ])
    # Permit installation from an arbitrary checkout by storing the absolute repo
    # path in the generated launcher environment.
    for root in candidates:
        if (root / "tools" / "adam.py").is_file():
            return root.resolve()
    raise SystemExit(
        "BLOCKED: Home Center checkout not found. Set HOME_CENTER_ROOT to the checkout containing tools/adam.py"
    )


def read_prompt(values: list[str]) -> str:
    text = " ".join(values).strip()
    if not text and not sys.stdin.isatty():
        text = sys.stdin.read().strip()
    if not text:
        raise SystemExit('usage: adam-do "what you want done"')
    return text


def append_receipt(payload: dict) -> None:
    state = Path(os.environ.get("HC_STATE_DIR", "~/.local/state/home-center")).expanduser() / "adam-do"
    state.mkdir(parents=True, exist_ok=True)
    path = state / "receipts.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    tmp = state / "last.json.tmp"
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(state / "last.json")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="adam-do", description="One-prompt Home Center command surface")
    group = p.add_mutually_exclusive_group()
    group.add_argument("--chat", action="store_true", help="conversation/research only unless prompt explicitly requests action")
    group.add_argument("--vlad", action="store_true", help="independent critical second opinion")
    group.add_argument("--terminal", action="store_true", help="explicit shell command through Adam terminal mode")
    p.add_argument("--timeout", type=int, default=1800)
    p.add_argument("prompt", nargs="*")
    args = p.parse_args(argv)

    text = read_prompt(args.prompt)
    mode = "chat" if args.chat else "vlad" if args.vlad else "terminal" if args.terminal else "continue"
    root = find_repo()
    command = [sys.executable, str(root / "tools" / "adam.py"), mode, text, "--cwd", str(root), "--timeout", str(args.timeout)]
    started = int(time.time())
    proc = subprocess.run(command, cwd=root, text=True)
    append_receipt({
        "schema": "adam-do-receipt-v1",
        "startedAtEpoch": started,
        "finishedAtEpoch": int(time.time()),
        "mode": mode,
        "prompt": text[:12000],
        "repo": str(root),
        "rc": proc.returncode,
        "ok": proc.returncode == 0,
        "delegatedTo": "tools/adam.py",
    })
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
