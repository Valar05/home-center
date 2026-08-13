#!/usr/bin/env python3
"""Read-only Vlad text-message MVP through the same Home Center gate as Adam."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))
import adam  # noqa: E402

def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    cwd = os.environ.get("HC_REPO_ROOT") or str(Path.cwd().resolve())
    return adam.run_text(" ".join(args) if args else "recent 10", cwd, 60)

if __name__ == "__main__":
    raise SystemExit(main())
