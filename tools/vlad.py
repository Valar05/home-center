#!/usr/bin/env python3
"""Vlad command surface.

`vlad jar ...` and `vlad jars ...` route to the canonical two-authority
Judgment Jar registry. Other text preserves Vlad's existing bounded critical
review lane through Adam.
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
import judgment_jars  # noqa: E402


def jar_args(args: list[str]) -> list[str]:
    if not args:
        return ["status"]
    command = args[0].lower()
    rest = args[1:]
    aliases = {
        "ls": "list",
        "show": "get",
        "use": "receipt",
        "flush": "flush-receipts",
    }
    return [aliases.get(command, command), *rest]


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        return judgment_jars.main(["status"])
    if args[0].lower() in {"jar", "jars"}:
        return judgment_jars.main(jar_args(args[1:]))
    cwd = os.environ.get("HC_REPO_ROOT") or str(Path.cwd().resolve())
    return adam.run_mode("vlad", " ".join(args), cwd, 300)


if __name__ == "__main__":
    raise SystemExit(main())
