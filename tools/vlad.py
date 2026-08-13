#!/usr/bin/env python3
"""Human-facing Vlad command surface.

`vlad jar ...` and `vlad jars ...` route to the canonical two-authority
Judgment Jar registry and receipt tools. Other text preserves Vlad's existing
bounded critical-review lane through Adam.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import adam  # noqa: E402
import jar_receipt  # noqa: E402
import judgment_jars  # noqa: E402

JAR_COMMANDS = {
    "sync", "status", "list", "get", "source", "search", "prompt",
    "registry", "receipt-status", "flush-receipts",
}


def route_jar(args: list[str]) -> int:
    if not args:
        return judgment_jars.main(["list"])
    command = args[0].lower()
    rest = args[1:]
    if command in {"receipt", "use"}:
        return jar_receipt.main(["record", *rest])
    aliases = {"ls": "list", "show": "get", "flush": "flush-receipts"}
    command = aliases.get(command, command)
    if command in JAR_COMMANDS:
        return judgment_jars.main([command, *rest])
    return judgment_jars.main(["get", *args])


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        return judgment_jars.main(["status"])
    if args[0].lower() in {"jar", "jars"}:
        return route_jar(args[1:])
    cwd = os.environ.get("HC_REPO_ROOT") or str(Path.cwd().resolve())
    return adam.run_mode("vlad", " ".join(args), cwd, 300)


if __name__ == "__main__":
    raise SystemExit(main())
