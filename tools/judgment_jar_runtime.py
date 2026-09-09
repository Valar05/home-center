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
from judgment_jar_task_router import task_source_packet


def active_jars(task: str | int | None = None, limit: int | None = None) -> str:
    """Return the bounded default packet plus any freshly resolved task Jar sources.

    Before task-aware routing this function accepted one positional integer limit.
    Preserve that call shape so the repair does not break existing carriers.
    """
    if isinstance(task, int) and not isinstance(task, bool) and limit is None:
        limit, task = task, None
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

    if task and str(task).strip():
        try:
            extra = task_source_packet(str(task), root=ROOT, config_path=CONFIG_PATH)
        except Exception as exc:
            # Jar routing must fail closed before the model sees an ungrounded task.
            message = str(exc)
            if "JAR_UNRESOLVED" in message:
                raise RuntimeError(message) from exc
            raise RuntimeError(f"JAR_UNRESOLVED: task-level canonical Jar routing failed: {exc}") from exc
        if extra.strip():
            text = text.rstrip() + "\n\n" + extra

    if len(text) > bounded_limit:
        raise RuntimeError(
            "receipt-governed Judgment Jar packet exceeds the configured phone bound "
            f"({len(text)} > {bounded_limit} characters); narrow the selected Jars instead of clipping receipted context"
        )
    return text
