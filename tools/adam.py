#!/usr/bin/env python3
"""Adam: explicit, no-agent console router for Home Center.

Modes are user-selected. Nothing loops, delegates, or chooses another lane on its own.
Every invocation prints one JSON receipt and exits.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = os.environ.get("HC_ADAM_MODEL", "qwen2.5-coder:1.5b")
DEFAULT_OLLAMA = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")


def receipt(mode: str, ok: bool, **data):
    value = {"schema": "adam-console-v1", "mode": mode, "ok": bool(ok), **data}
    print(json.dumps(value, ensure_ascii=False, sort_keys=True))
    return 0 if ok else 1


def run_terminal(text: str, cwd: str, timeout: int):
    p = subprocess.run(
        ["bash", "-lc", text],
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    return receipt(
        "terminal",
        p.returncode == 0,
        command=text,
        cwd=str(Path(cwd).resolve()),
        rc=p.returncode,
        stdout=p.stdout[-8000:],
        stderr=p.stderr[-8000:],
    )


def ollama_generate(mode: str, text: str, system: str, timeout: int):
    payload = json.dumps({
        "model": DEFAULT_MODEL,
        "stream": False,
        "system": system,
        "prompt": text,
        "options": {"temperature": 0, "num_predict": 600},
    }).encode("utf-8")
    request = urllib.request.Request(
        DEFAULT_OLLAMA + "/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return receipt(
            mode,
            False,
            error="local_model_unavailable",
            detail=str(exc),
            model=DEFAULT_MODEL,
            ollama=DEFAULT_OLLAMA,
            cloudFallback=False,
        )
    answer = str(body.get("response") or "").strip()
    return receipt(
        mode,
        bool(answer),
        response=answer,
        model=DEFAULT_MODEL,
        ollama=DEFAULT_OLLAMA,
        cloudFallback=False,
    )


def run_chat(text: str, timeout: int):
    return ollama_generate(
        "chat",
        text,
        "You are Adam, Drew's terse local Home Center console companion. Answer the explicit prompt only. Do not invent actions, claim execution, delegate, or choose tools. If an action should be executed, say exactly what command or explicit mode would do it.",
        timeout,
    )


def run_vlad(text: str, timeout: int):
    return ollama_generate(
        "vlad",
        text,
        "You are Vlad, an independent bounded consultant to Adam. Analyze only the supplied question. Be terse. Challenge bad assumptions. Never execute, delegate, or claim evidence you were not given. Return advice to Adam, not commands already performed.",
        timeout,
    )


def continue_command(prompt: str):
    explicit = os.environ.get("HC_ADAM_CONTINUE_CMD", "").strip()
    if explicit:
        return ["bash", "-lc", explicit], prompt, "configured"

    launcher = ROOT / "tools" / "cn-offline.ps1"
    pwsh = shutil.which("pwsh") or shutil.which("powershell")
    if pwsh and launcher.exists():
        return [pwsh, "-NoProfile", "-File", str(launcher), "-Prompt", prompt], None, "repo-offline-continue"
    return None, None, "unavailable"


def run_continue(text: str, cwd: str, timeout: int):
    command, stdin_text, adapter = continue_command(text)
    if command is None:
        return receipt(
            "continue",
            False,
            error="continue_adapter_unavailable_on_this_node",
            detail="Set HC_ADAM_CONTINUE_CMD to the deterministic Continue consumer for this node, or run Adam where tools/cn-offline.ps1 and PowerShell are available.",
            cloudFallback=False,
        )
    p = subprocess.run(
        command,
        cwd=cwd,
        input=stdin_text,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    return receipt(
        "continue",
        p.returncode == 0,
        adapter=adapter,
        rc=p.returncode,
        stdout=p.stdout[-12000:],
        stderr=p.stderr[-12000:],
        cloudFallback=False,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(prog="adam", description="Explicit no-agent Home Center console")
    parser.add_argument("mode", choices=("terminal", "chat", "continue", "vlad"))
    parser.add_argument("text", nargs="?", default="")
    parser.add_argument("--cwd", default=str(ROOT))
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args(argv)
    text = args.text if args.text else sys.stdin.read()
    if not text.strip():
        return receipt(args.mode, False, error="empty_request")
    if args.mode == "terminal":
        return run_terminal(text, args.cwd, args.timeout)
    if args.mode == "chat":
        return run_chat(text, args.timeout)
    if args.mode == "continue":
        return run_continue(text, args.cwd, args.timeout)
    return run_vlad(text, args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
