#!/usr/bin/env python3
"""Receipt-governed Judgment Jar context for the phone worker."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

from judgment_jar_common import CONFIG_PATH, read_config


def active_jars(limit: int | None = None) -> str:
    config = read_config(CONFIG_PATH)
    runtime = dict(config.get("runtime") or {})
    selected = [str(value) for value in runtime.get("defaultPhoneJarIds") or [] if str(value).strip()]
    if not selected:
        raise RuntimeError("Judgment Jar runtime has no configured defaultPhoneJarIds")
    bounded_limit = int(limit or runtime.get("maxPhonePromptCharacters") or 18000)
    command = [
        sys.executable,
        str(ROOT / "tools" / "judgment_jars.py"),
        "--root",
        str(ROOT),
        "--offline",
        "prompt",
        *selected,
    ]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=45)
    if result.returncode != 0:
        raise RuntimeError(
            "receipt-governed Judgment Jar loading failed: "
            + (result.stderr.strip() or result.stdout.strip() or f"rc={result.returncode})")
        )
    text = result.stdout
    if not text.strip():
        raise RuntimeError("receipt-governed Judgment Jar loading returned no context")
    if len(text) > bounded_limit:
        raise RuntimeError(
            "receipt-governed default Judgment Jar packet exceeds the configured phone bound "
            f"({len(text)} > {bounded_limit} characters); narrow defaultPhoneJarIds instead of clipping receipted context"
        )
    return text
