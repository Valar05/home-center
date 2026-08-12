#!/usr/bin/env python3
"""Adam: conversational deterministic executive for Home Center.

The Android overlay keeps the explicit one-shot modes terminal/chat/continue/vlad.
Bare ``adam`` opens the conversational executive. Natural-language turns are
planned by the local phone model into one typed action, then the deterministic
runtime validates and executes that action. Explicit colon commands bypass
interpretation completely.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = os.environ.get("HC_ADAM_MODEL", "qwen2.5-coder:1.5b")
DEFAULT_OLLAMA = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
PHONE_LLM_URL = os.environ.get("HC_PHONE_LLM_URL", "http://127.0.0.1:8790/v1/chat/completions")
PHONE_LLM_MODEL = os.environ.get("HC_PHONE_LLM_MODEL", "local-phone")
MAX_RECEIPT_TEXT = int(os.environ.get("HC_ADAM_RECEIPT_TEXT", "1400"))
MAX_MODEL_TEXT = int(os.environ.get("HC_ADAM_MODEL_TEXT", "2600"))
ONE_SHOT_MODES = ("terminal", "chat", "continue", "vlad")
EXEC_KINDS = ("say", "terminal", "continue", "phone", "vlad")
DANGEROUS_SHELL = re.compile(
    r"(^|[;&|]\s*)(sudo|su\b|rm\s+-rf\b|mkfs\b|dd\s+if=|pm\s+uninstall\b|reboot\b|shutdown\b|poweroff\b)",
    re.I,
)


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
        "You are Adam, Drew's terse local Home Center companion. Converse naturally. Do not claim actions were executed unless evidence is supplied. This explicit chat mode never executes tools.",
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


def run_phone(text: str, timeout: int):
    helper = ROOT / "tools" / "android_phone_local_executive.py"
    if not helper.exists():
        return receipt("phone", False, error="phone_executive_missing")
    p = subprocess.run(
        [sys.executable, str(helper), text],
        cwd=str(ROOT / "tools"),
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    return receipt(
        "phone",
        p.returncode == 0,
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


EXEC_SYSTEM = """You are Adam, Drew's local conversational executive on his Android phone.
You are both a chatbot and an executor. Return exactly one JSON object and nothing else.
Schema: {"kind":"say|terminal|continue|phone|vlad","say":"brief conversational text","payload":"action payload"}
Rules:
- Use kind=say for greetings, conversation, explanations, questions, or when no action is needed.
- Use kind=terminal only for a bounded, ordinary, non-destructive shell command that directly fulfills the user's request in the current workspace. Prefer inspection/status/build/test commands. Never use sudo, su, rm -rf, mkfs, dd, uninstall, reboot, shutdown, permission escalation, credential access, messaging, purchases, or account/security changes.
- Use kind=continue for coding/editing/refactoring work that belongs in the repository rather than inventing a shell patch yourself.
- Use kind=phone for Android UI/device intents such as go home, open an app, back, recents, or other Phone Hands work.
- Use kind=vlad only when the user explicitly asks for Vlad or an independent second opinion.
- payload is the exact shell command, Continue prompt, phone intent, or Vlad question. For say, payload must be empty.
- say should sound like Adam speaking to Drew. Never claim success before the runtime result exists.
- Preserve conversational context from prior turns.
"""


def extract_local_message(body: dict) -> str:
    try:
        msg = body["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("local executive returned no assistant message") from exc
    for key in ("content", "reasoning_content"):
        value = msg.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise RuntimeError("local executive returned an empty assistant message")


def local_exec_plan(history: list[dict], text: str, cwd: str, timeout: int) -> dict:
    messages = [{"role": "system", "content": EXEC_SYSTEM}]
    messages.extend(history[-12:])
    messages.append({"role": "user", "content": f"Current workspace: {cwd}\nUser: {text}"})
    payload = json.dumps({
        "model": PHONE_LLM_MODEL,
        "messages": messages,
        "temperature": 0,
        "max_tokens": 260,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")
    req = urllib.request.Request(PHONE_LLM_URL, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise RuntimeError(f"local executive unavailable: {exc}") from exc
    raw = extract_local_message(body)
    try:
        plan = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.S)
        if not match:
            raise RuntimeError("local executive did not return JSON")
        plan = json.loads(match.group(0))
    if not isinstance(plan, dict):
        raise RuntimeError("local executive plan was not an object")
    kind = str(plan.get("kind") or "").strip().lower()
    say = str(plan.get("say") or "").strip()
    action = str(plan.get("payload") or "").strip()
    if kind not in EXEC_KINDS:
        raise RuntimeError(f"local executive selected invalid kind: {kind!r}")
    if kind == "say":
        action = ""
    elif not action:
        raise RuntimeError(f"local executive selected {kind} without payload")
    if kind == "terminal" and DANGEROUS_SHELL.search(action):
        raise RuntimeError("local executive proposed a blocked high-risk shell command")
    return {"kind": kind, "say": say, "payload": action}


def executive_help() -> str:
    return (
        "Adam executive commands:\n"
        "  :sh COMMAND        execute exact shell command\n"
        "  :continue PROMPT   send exact prompt to Continue\n"
        "  :phone INTENT      send exact intent to Phone Hands local executive\n"
        "  :vlad QUESTION     ask Vlad exactly\n"
        "  :chat TEXT         explicit chat-only turn\n"
        "  :cwd PATH          change workspace\n"
        "  :status            show workspace and local executive endpoint\n"
        "  :help              show this help\n"
        "  :quit / :exit      leave Adam\n"
        "Anything else is a conversational Adam turn. Adam may choose one bounded typed action."
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


def print_action_result(kind: str, before: str, captured: str = "") -> None:
    if before:
        print(before)
    if captured:
        print(captured)


def execute_plan(plan: dict, cwd: str, timeout: int) -> int:
    kind = plan["kind"]
    say = plan.get("say", "")
    payload = plan.get("payload", "")
    if kind == "say":
        print(say or "Okay.")
        return 0
    if say:
        print(say)
    if kind == "terminal":
        return run_terminal(payload, cwd, timeout)
    if kind == "continue":
        return run_continue(payload, cwd, timeout)
    if kind == "phone":
        return run_phone(payload, timeout)
    return run_vlad(payload, timeout)


def explicit_command(text: str, cwd: str, timeout: int):
    stripped = text.strip()
    mapping = ((":sh", "terminal"), (":continue", "continue"), (":vlad", "vlad"), (":chat", "chat"))
    for prefix, mode in mapping:
        if stripped == prefix or stripped.startswith(prefix + " "):
            payload = text[len(prefix):].strip()
            return True, run_mode(mode, payload, cwd, timeout)
    if stripped == ":phone" or stripped.startswith(":phone "):
        return True, run_phone(text[len(":phone"):].strip(), timeout)
    return False, 0


def run_shell(cwd: str, timeout: int):
    current_cwd = str(Path(cwd).expanduser().resolve())
    if not Path(current_cwd).is_dir():
        return receipt("shell", False, error="invalid_cwd", cwd=current_cwd)
    if not sys.stdin.isatty():
        return receipt(
            "shell",
            False,
            error="interactive_tty_required",
            detail="Use a one-shot mode for piped input: adam terminal|chat|continue|vlad TEXT",
        )

    history: list[dict] = []
    print("Adam online. Chat naturally; :help for exact controls.")
    while True:
        try:
            text = input(f"adam {current_cwd}$ ")
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
            print(executive_help())
            continue
        if stripped == ":status":
            print(json.dumps({"schema": "adam-executive-status-v1", "cwd": current_cwd, "localExecutive": PHONE_LLM_URL, "model": PHONE_LLM_MODEL}, sort_keys=True))
            continue
        if stripped == ":cwd" or stripped.startswith(":cwd "):
            try:
                current_cwd = resolve_cwd(text[len(":cwd"):], current_cwd)
            except ValueError as exc:
                print(f"Adam: {exc}")
                continue
            print(f"Adam: workspace {current_cwd}")
            continue
        handled, _ = explicit_command(text, current_cwd, timeout)
        if handled:
            continue
        if stripped.startswith(":"):
            print(f"Adam: unknown command {stripped.split()[0]}; use :help")
            continue
        try:
            plan = local_exec_plan(history, text, current_cwd, timeout)
        except Exception as exc:
            print(f"Adam: local executive unavailable: {tail(str(exc), 500)}")
            continue
        history.append({"role": "user", "content": text})
        history.append({"role": "assistant", "content": json.dumps(plan, ensure_ascii=False)})
        execute_plan(plan, current_cwd, timeout)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="adam", description="Home Center conversational deterministic executive")
    parser.add_argument("mode", nargs="?", choices=ONE_SHOT_MODES + ("shell",), default="shell")
    parser.add_argument("text", nargs="?", default="")
    parser.add_argument("--cwd", default=str(ROOT))
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args(argv)
    if args.mode == "shell":
        if args.text.strip():
            return receipt("shell", False, error="shell_does_not_accept_text", detail="Enter requests at the interactive prompt.")
        return run_shell(args.cwd, args.timeout)
    text = args.text if args.text else sys.stdin.read()
    return run_mode(args.mode, text, args.cwd, args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
