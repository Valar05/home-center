#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv):
    if not argv or argv[0] in {"-h", "--help", "help"}:
        print("Usage: venice review [review options]\n\nCommands:\n  review   Independent minimal-compute code review gate")
        return 0
    command, *rest = argv
    if command == "review":
        return subprocess.call([sys.executable, str(ROOT / "tools" / "venice_review.py"), *rest], cwd=os.getcwd())
    print(f"venice: unknown command: {command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
