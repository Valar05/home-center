#!/usr/bin/env python3
"""Installed Adam worker with receipt-governed Judgment Jar loading."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

import adam_codex_phone as core
import adam_planned_venice as worker
from judgment_jar_runtime import active_jars

core.active_jars = active_jars
worker.core.active_jars = active_jars
worker.execution.worker.active_jars = active_jars


def main(argv: list[str] | None = None) -> int:
    return worker.main(sys.argv[1:] if argv is None else argv)


if __name__ == "__main__":
    raise SystemExit(main())
