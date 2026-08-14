#!/data/data/com.termux/files/usr/bin/python
"""Dungeon-confined adapter for the existing phone-local Adam/Venice worker.

The ordinary local worker can request inspection shell and phone intents. Fortress
campaign fallback deliberately removes both powers. Local inference may read,
list, search, and write inside the isolated worktree; only the deterministic
coordinator may run trusted verification argv.
"""
from __future__ import annotations

import sys
from pathlib import Path

import adam_codex_phone as worker
import adam_venice_reviewed as reviewed

ALLOWED_TOOLS = frozenset({"read_file", "list_dir", "search_files", "write_file", "respond", "finish"})
_ORIGINAL_EXECUTE_TOOL = worker.execute_tool


def disabled_run_command(_workspace: Path, obj: dict) -> dict:
    return {
        "ok": False,
        "error": "Dungeon local inference cannot choose shell commands; the coordinator owns trusted verification argv.",
        "command": str(obj.get("command") or "")[:500],
    }


def disabled_phone_intent(_workspace: Path, obj: dict) -> dict:
    return {
        "ok": False,
        "error": "Dungeon local inference has no Phone Hands, UI, overlay, Shizuku, or device-intent authority.",
        "intent": str(obj.get("intent") or "")[:500],
    }


def confined_execute_tool(workspace: Path, action: dict) -> tuple[bool, dict]:
    tool = str(action.get("tool") or "").strip()
    if tool == "run_command":
        return False, disabled_run_command(workspace, action)
    if tool == "phone_intent":
        return False, disabled_phone_intent(workspace, action)
    if tool not in ALLOWED_TOOLS:
        return False, {"ok": False, "error": f"Dungeon local inference rejects unapproved tool: {tool!r}"}
    return _ORIGINAL_EXECUTE_TOOL(workspace, action)


def install_confinement() -> None:
    worker.run_command = disabled_run_command
    worker.phone_intent = disabled_phone_intent
    worker.execute_tool = confined_execute_tool


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("dungeon_local_adam requires one bounded campaign prompt", file=sys.stderr)
        return 2
    install_confinement()
    return reviewed.run_task(" ".join(args), Path.cwd().resolve())


if __name__ == "__main__":
    raise SystemExit(main())
