#!/usr/bin/env python3
"""Receipt-governed Judgment Jar context for the phone worker."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def active_jars(limit: int = 18000) -> str:
    command = [
        sys.executable,
        str(ROOT / "tools" / "judgment_jars.py"),
        "--root",
        str(ROOT),
        "--offline",
        "prompt",
        "--all",
    ]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=45)
    if result.returncode != 0:
        raise RuntimeError(
            "receipt-governed Judgment Jar loading failed: "
            + (result.stderr.strip() or result.stdout.strip() or f"rc={result.returncode}")
        )
    text = result.stdout
    if not text.strip():
        raise RuntimeError("receipt-governed Judgment Jar loading returned no context")
    if len(text) <= limit:
        return text
    half = max(1, limit // 2)
    return text[:half] + "\n...[Judgment Jar context clipped after receipts]...\n" + text[-half:]
