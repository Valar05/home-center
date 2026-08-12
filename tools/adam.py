#!/usr/bin/env python3
"""Adam: explicit, no-agent console router for Home Center.

One-shot modes are user-selected and remain the transport contract used by the
Android operator overlay. The interactive ``shell`` mode is only a thin prompt
around those same explicit lanes; it does not infer, delegate, or auto-route.
Bare ``adam`` opens that deterministic shell. Every executed request still
prints one bounded JSON receipt.
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
MAX_RECEIPT_TEXT = int(os.environ.get("HC_ADAM_RECEIPT_TEXT", "1400"))
MAX_MODEL_TEXT = int(os.environ.get("HC_ADAM_MODEL_TEXT", "2600"))
ONE_SHOT_MODES = ("terminal", "chat", "continue", "vlad")
SHELL_COMMANDS = (":mode", ":cwd", ":status", ":help", ":quit", ":exit")


def tail(value: str, limit: int = MAX_RECEIPT_TEXT) -> str:
    text = str(value or "")
    return text if len(text) <= limit else text[-limit:]


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
        command=tail(text, 600),
        cwd=str(Path(cwd).resolve()),
        rc=p.returncode,
        stdout=tail(p.stdout),
        stderr=tail(p.stderr),
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
            detail=tail(str(exc)),
            model=DEFAULT_MODEL,
            ollama=DEFAULT_OLLAMA,
            cloudFallback=False,
        )
    answer = tail(str(body.get("response") or "").strip(), MAX_MODEL_TEXT)
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
        stdout=tail(p.stdout),
        stderr=tail(p.stderr),
        cloudFallback=False,
    )


def run_mode(mode: str, text: str, cwd: str, timeout: int):
    if mode not in ONE_SHOT_MODES:
        return receipt(mode, False, error="unsupported_mode")
    if not text.strip():
        return receipt(mode, False, error="empty_request")
    if mode == "terminal":
        return run_terminal(text, cwd, timeout)
    if mode == "chat":
        return run_chat(text, timeout)
    if mode == "continue":
        return run_continue(text, cwd, timeout)
    return run_vlad(text, timeout)


def shell_help() -> str:
    return (
        "Adam shell commands:\n"
        "  :mode terminal|chat|continue|vlad  select the explicit lane\n"
        "  :cwd PATH                          change working directory\n"
        "  :status                            show current lane and cwd\n"
        "  :help                              show this help\n"
        "  :quit / :exit                      leave the shell\n"
        "Any other line is sent unchanged to the selected lane. No auto-routing."
    )


def resolve_cwd(value: str, current: str) -> str:
    raw = value.strip()
    if not raw:
        return current
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = Path(current) / path
    path = path.resolve()
    if not path.is_dir():
        raise ValueError(f"not a directory: {path}")
    return str(path)


def run_shell(initial_lane: str, cwd: str, timeout: int):
    lane = initial_lane
    current_cwd = str(Path(cwd).expanduser().resolve())
    if lane not in ONE_SHOT_MODES:
        return receipt("shell", False, error="invalid_initial_lane", lane=lane)
    if not Path(current_cwd).is_dir():
        return receipt("shell", False, error="invalid_cwd", cwd=current_cwd)
    if not sys.stdin.isatty():
        return receipt(
            "shell",
            False,
            error="interactive_tty_required",
            detail="Use a one-shot mode for piped input: adam terminal|chat|continue|vlad TEXT",
        )

    print("Adam deterministic shell. :help for commands. No auto-routing.")
    while True:
        try:
            text = input(f"adam[{lane}] {current_cwd}$ ")
        except EOFError:
            print()
            return 0
        except KeyboardInterrupt:
            print("\n^C")
            continue
        stripped = text.strip()
        if not stripped:
            continue
        if stripped in (":quit", ":exit"):
            return 0
        if stripped == ":help":
            print(shell_help())
            continue
        if stripped == ":status":
            print(json.dumps({"schema": "adam-shell-status-v1", "lane": lane, "cwd": current_cwd}, sort_keys=True))
            continue
        if stripped.startswith(":mode"):
            parts = stripped.split()
            if len(parts) != 2 or parts[1] not in ONE_SHOT_MODES:
                print(f"usage: :mode {'|'.join(ONE_SHOT_MODES)}")
                continue
            lane = parts[1]
            print(json.dumps({"schema": "adam-shell-mode-v1", "lane": lane}, sort_keys=True))
            continue
        if stripped.startswith(":cwd"):
            raw = text[len(":cwd"):]
            try:
                current_cwd = resolve_cwd(raw, current_cwd)
            except ValueError as exc:
                print(json.dumps({"schema": "adam-shell-cwd-v1", "ok": False, "error": str(exc)}, sort_keys=True))
                continue
            print(json.dumps({"schema": "adam-shell-cwd-v1", "ok": True, "cwd": current_cwd}, sort_keys=True))
            continue
        if stripped.startswith(":"):
            print(f"unknown shell command: {stripped.split()[0]}; use :help")
            continue
        run_mode(lane, text, current_cwd, timeout)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="adam", description="Explicit no-agent Home Center console")
    parser.add_argument("mode", nargs="?", choices=ONE_SHOT_MODES + ("shell",), default="shell")
    parser.add_argument("text", nargs="?", default="")
    parser.add_argument("--cwd", default=str(ROOT))
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--lane", choices=ONE_SHOT_MODES, default="terminal", help="initial lane for shell mode")
    args = parser.parse_args(argv)
    if args.mode == "shell":
        if args.text.strip():
            return receipt("shell", False, error="shell_does_not_accept_text", detail="Enter requests at the interactive prompt.")
        return run_shell(args.lane, args.cwd, args.timeout)
    text = args.text if args.text else sys.stdin.read()
    return run_mode(args.mode, text, args.cwd, args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
