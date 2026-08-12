#!/usr/bin/env python3
"""Internal deterministic primitives for the phone-local Adam worker.

This module is deliberately NOT an agent entrypoint. `adam_venice_reviewed.py`
owns the Codex loop, daemon persistence, local steering, and Venice stop gate.
This file only provides bounded tools, model transport, parsing, and shared law.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHONE_LLM_URL = os.environ.get("HC_PHONE_LLM_URL", "http://127.0.0.1:8790/v1/chat/completions")
PHONE_LLM_MODEL = os.environ.get("HC_PHONE_LLM_MODEL", "local-phone")
MAX_OUTPUT = int(os.environ.get("HC_ADAM_TOOL_OUTPUT", "12000"))
MAX_FILE_WRITE = int(os.environ.get("HC_ADAM_MAX_WRITE", str(256 * 1024)))

DANGEROUS = re.compile(
    r"(^|[;&|]\s*)(sudo\b|su\b|rm\s+-rf\b|mkfs\b|dd\s+if=|reboot\b|shutdown\b|poweroff\b|"
    r"pm\s+uninstall\b|settings\s+put\s+secure\b|chmod\s+777\b)",
    re.I,
)
# Model-inferred shell is deliberately inspection/validation oriented. Mutating
# repository/filesystem operations must use the typed write tool or an explicit
# operator-selected terminal lane; this prevents a tiny model from smuggling a
# mutation through shell syntax.
MUTATING_SHELL = re.compile(
    r"(?:^|[;&|]\s*)(?:"
    r"rm\b|mv\b|cp\b|install\b|truncate\b|touch\b|mkdir\b|rmdir\b|"
    r"sed\s+-[^\n]*i\b|perl\s+-[^\n]*i\b|tee\b|"
    r"git\s+(?:add|commit|reset|clean|checkout|restore|switch|merge|rebase|cherry-pick|revert|tag|push|pull)\b|"
    r"npm\s+(?:install|uninstall|update)\b|pnpm\s+(?:add|remove|install|update)\b|yarn\s+(?:add|remove|install|upgrade)\b|"
    r"pip(?:3)?\s+install\b|pkg\s+(?:install|uninstall|upgrade)\b|apt(?:-get)?\s+(?:install|remove|upgrade)\b"
    r")|(?:^|[^<])>>?|\b(?:echo|printf)\b[^\n]*>\s*[^&]",
    re.I,
)

SYSTEM = r'''You are Adam, Drew's local phone worker. Work like Codex, not like a generic chatbot.

CORE LOOP
1. Inspect real workspace state.
2. Choose ONE typed tool action.
3. Read its observation.
4. Continue until the requested outcome is actually verified.
5. Propose a terminal response only when evidence supports it; Venice owns stop permission.

AUTHORITY
- Repository/runtime evidence outranks confidence.
- Preserve Drew's commissioned outcome, owner, tool/lane, exclusions, evidence standard, and delivery surface.
- Do not silently substitute architecture or workflow.
- Prefer small coherent edits and project-native validation.
- Never claim deployment/device/runtime success without fresh evidence for that exact claim.
- You are running on Drew's Android phone in Termux.

OUTPUT CONTRACT
Return EXACTLY one JSON object and nothing else. No markdown fences.
Allowed objects:
{"tool":"read_file","path":"relative/path","start":1,"lines":220}
{"tool":"list_dir","path":"relative/path"}
{"tool":"search_files","query":"literal or regex","path":"relative/path"}
{"tool":"run_command","command":"inspection/build/test command","timeout":120}
{"tool":"write_file","path":"relative/path","content":"complete UTF-8 content"}
{"tool":"phone_intent","intent":"bounded Android UI/device intent"}
{"tool":"respond","text":"governed conversational response candidate"}
{"tool":"finish","status":"done|blocked|partial","text":"evidence-grounded result candidate"}

RULES
- One tool action per turn.
- Use read/list/search before editing unfamiliar code.
- run_command is for inspection, builds, tests, and validation; it cannot directly mutate files/repository state.
- Use write_file for model-authored file changes. Exact operator-requested raw shell belongs to the explicit terminal lane.
- write_file may only write inside the current workspace.
- phone_intent delegates to the existing phone body helper.
- respond/finish are proposals only; the reviewed launcher sends them through Venice before they can terminate.
- Never emit generic customer-service filler.
- Do not emit plain prose outside JSON.
- If blocked, inspect alternate authorized existing routes before proposing blocked.
'''


def clipped(value: str, limit: int = MAX_OUTPUT) -> str:
    value = str(value or "")
    if len(value) <= limit:
        return value
    return value[: limit // 2] + "\n...[clipped]...\n" + value[-limit // 2 :]


def active_jars() -> str:
    rule_dir = ROOT / ".continue" / "rules"
    if not rule_dir.is_dir():
        raise RuntimeError(f"Judgement Jar directory missing: {rule_dir}")
    docs: list[str] = []
    for path in sorted(rule_dir.glob("*judgement-jar*.md")):
        docs.append(f"\n--- {path.relative_to(ROOT)} ---\n{path.read_text(encoding='utf-8', errors='replace')}")
    personality = rule_dir / "60-adam-personality-gate.md"
    if personality.exists() and all("60-adam-personality-gate.md" not in d for d in docs):
        docs.append(f"\n--- {personality.relative_to(ROOT)} ---\n{personality.read_text(encoding='utf-8', errors='replace')}")
    if not docs:
        raise RuntimeError("No active Judgement Jars found")
    return clipped("".join(docs), 18000)


def workspace_path(workspace: Path, raw: str) -> Path:
    raw = str(raw or ".").strip()
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = workspace / candidate
    candidate = candidate.resolve()
    try:
        candidate.relative_to(workspace)
    except ValueError as exc:
        raise RuntimeError(f"path escapes workspace: {candidate}") from exc
    return candidate


def read_file(workspace: Path, obj: dict) -> dict:
    path = workspace_path(workspace, obj.get("path", ""))
    if not path.is_file():
        return {"ok": False, "error": f"not a file: {path}"}
    start = max(1, int(obj.get("start", 1)))
    count = min(1000, max(1, int(obj.get("lines", 220))))
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    chunk = lines[start - 1 : start - 1 + count]
    rendered = "\n".join(f"{i}: {line}" for i, line in enumerate(chunk, start=start))
    return {"ok": True, "path": str(path.relative_to(workspace)), "start": start, "returned": len(chunk), "totalLines": len(lines), "content": clipped(rendered)}


def list_dir(workspace: Path, obj: dict) -> dict:
    path = workspace_path(workspace, obj.get("path", "."))
    if not path.is_dir():
        return {"ok": False, "error": f"not a directory: {path}"}
    items = []
    for p in sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))[:300]:
        items.append({"name": p.name, "type": "dir" if p.is_dir() else "file", "size": None if p.is_dir() else p.stat().st_size})
    return {"ok": True, "path": str(path.relative_to(workspace)) if path != workspace else ".", "items": items}


def search_files(workspace: Path, obj: dict) -> dict:
    base = workspace_path(workspace, obj.get("path", "."))
    query = str(obj.get("query") or "")
    if not query:
        return {"ok": False, "error": "empty search query"}
    try:
        rx = re.compile(query, re.I)
    except re.error:
        rx = re.compile(re.escape(query), re.I)
    hits = []
    skip = {".git", "node_modules", ".gradle", "build", "dist", ".venv", "venv"}
    roots = [base] if base.is_file() else base.rglob("*")
    for p in roots:
        if len(hits) >= 120:
            break
        if not p.is_file() or any(part in skip for part in p.parts):
            continue
        try:
            if p.stat().st_size > 2_000_000:
                continue
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for idx, line in enumerate(text.splitlines(), 1):
            if rx.search(line):
                hits.append({"path": str(p.relative_to(workspace)), "line": idx, "text": line[:600]})
                if len(hits) >= 120:
                    break
    return {"ok": True, "query": query, "hits": hits, "truncated": len(hits) >= 120}


def run_command(workspace: Path, obj: dict) -> dict:
    command = str(obj.get("command") or "").strip()
    if not command:
        return {"ok": False, "error": "empty command"}
    if DANGEROUS.search(command):
        return {"ok": False, "error": "blocked destructive/privileged command", "command": command}
    if MUTATING_SHELL.search(command):
        return {"ok": False, "error": "model-generated shell is inspection/validation-only; use write_file or the explicit terminal lane for intentional mutation", "command": command}
    timeout = min(900, max(1, int(obj.get("timeout", 120))))
    try:
        p = subprocess.run(["bash", "-lc", command], cwd=workspace, text=True, capture_output=True, timeout=timeout)
        return {"ok": p.returncode == 0, "command": command, "rc": p.returncode, "stdout": clipped(p.stdout), "stderr": clipped(p.stderr)}
    except subprocess.TimeoutExpired as exc:
        return {"ok": False, "error": "timeout", "command": command, "stdout": clipped(exc.stdout or ""), "stderr": clipped(exc.stderr or "")}


def write_file(workspace: Path, obj: dict) -> dict:
    path = workspace_path(workspace, obj.get("path", ""))
    content = obj.get("content")
    if not isinstance(content, str):
        return {"ok": False, "error": "content must be a string"}
    size = len(content.encode("utf-8"))
    if size > MAX_FILE_WRITE:
        return {"ok": False, "error": f"write exceeds {MAX_FILE_WRITE} bytes"}
    path.parent.mkdir(parents=True, exist_ok=True)
    existed = path.exists()
    before = path.read_text(encoding="utf-8", errors="replace") if existed and path.is_file() and path.stat().st_size <= MAX_FILE_WRITE else None
    path.write_text(content, encoding="utf-8")
    return {"ok": True, "path": str(path.relative_to(workspace)), "bytes": size, "created": not existed, "changed": before != content}


def phone_intent(workspace: Path, obj: dict) -> dict:
    intent = str(obj.get("intent") or "").strip()
    if not intent:
        return {"ok": False, "error": "empty phone intent"}
    helper = ROOT / "tools" / "android_phone_local_executive.py"
    if not helper.is_file():
        return {"ok": False, "error": f"phone helper missing: {helper}"}
    try:
        p = subprocess.run([sys.executable, str(helper), intent], cwd=ROOT / "tools", text=True, capture_output=True, timeout=120)
        return {"ok": p.returncode == 0, "intent": intent, "rc": p.returncode, "stdout": clipped(p.stdout), "stderr": clipped(p.stderr)}
    except subprocess.TimeoutExpired as exc:
        return {"ok": False, "error": "phone intent timeout", "stdout": clipped(exc.stdout or ""), "stderr": clipped(exc.stderr or "")}


def initial_observation(workspace: Path) -> str:
    data = {"cwd": str(workspace), "repoRoot": str(ROOT)}
    try:
        p = subprocess.run(["git", "status", "-sb"], cwd=workspace, text=True, capture_output=True, timeout=10)
        data["gitStatus"] = clipped(p.stdout + p.stderr, 4000)
    except Exception as exc:
        data["gitStatus"] = f"unavailable: {exc}"
    return json.dumps(data, ensure_ascii=False)


def call_model(messages: list[dict], timeout: int = 120) -> str:
    payload = json.dumps({"model": PHONE_LLM_MODEL, "messages": messages, "temperature": 0, "max_tokens": 700}).encode("utf-8")
    req = urllib.request.Request(PHONE_LLM_URL, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise RuntimeError(f"phone model unavailable: {exc}") from exc
    try:
        msg = body["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("phone model returned no assistant message") from exc
    for key in ("content", "reasoning_content"):
        value = msg.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise RuntimeError("phone model returned empty assistant output")


def parse_action(raw: str) -> dict | None:
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        for i, ch in enumerate(raw):
            if ch != "{":
                continue
            try:
                value, _ = decoder.raw_decode(raw[i:])
                if isinstance(value, dict):
                    return value
            except json.JSONDecodeError:
                continue
    return None


def execute_tool(workspace: Path, action: dict) -> tuple[bool, dict]:
    tool = str(action.get("tool") or "").strip()
    if tool == "read_file": return False, read_file(workspace, action)
    if tool == "list_dir": return False, list_dir(workspace, action)
    if tool == "search_files": return False, search_files(workspace, action)
    if tool == "run_command": return False, run_command(workspace, action)
    if tool == "write_file": return False, write_file(workspace, action)
    if tool == "phone_intent": return False, phone_intent(workspace, action)
    if tool == "respond":
        return True, {"terminal": "respond", "text": str(action.get("text") or "").strip()}
    if tool == "finish":
        status = str(action.get("status") or "partial").strip().lower()
        if status not in {"done", "blocked", "partial"}: status = "partial"
        return True, {"terminal": "finish", "status": status, "text": str(action.get("text") or "").strip()}
    return False, {"ok": False, "error": f"unknown tool: {tool!r}"}


def help_text() -> str:
    return """Adam phone worker

Type a natural-language task. The reviewed launcher loads Codex local steering,
executes bounded tools, checkpoints long work, and requires Venice permission to stop.
Special commands: :cwd PATH, :status, :help, :exit.
"""


if __name__ == "__main__":
    print("adam_codex_phone.py is an internal core; use bare `adam` / adam_venice_reviewed.py", file=sys.stderr)
    raise SystemExit(2)
