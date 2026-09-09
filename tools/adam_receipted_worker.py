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
from judgment_jar_runtime import active_jars as runtime_active_jars
from judgment_jar_task_router import task_source_packet


_task_context: str | None = None


def active_jars(limit: int | None = None) -> str:
    """Compatibility hook used by the existing execution worker.

    When execution is inside a task, the current utterance is carried into the
    runtime so task-mentioned Jars are resolved before any model response.
    """
    return runtime_active_jars(_task_context, limit)


# Ground planning too.  This is read-only: the planner receives the exact current
# canonical native source when the task names a Jar, or planning fails closed.
_original_planning_system = worker.planning_system


def planning_system(task: str, workspace: Path) -> str:
    base = _original_planning_system(task, workspace)
    extra = task_source_packet(task, root=ROOT)
    if extra.strip():
        base += "\n\nTASK-RESOLVED CANONICAL JUDGMENT JAR SOURCE (binding):\n" + extra
    return base


worker.planning_system = planning_system


# The underlying execution loop predates task-aware Jar loading and calls
# active_jars() with no arguments.  Carry its task through this compatibility
# context instead of forking or replacing the execution engine.
_original_execution_run_task = worker.execution.run_task


def execution_run_task(task: str, *args, **kwargs):
    global _task_context
    prior = _task_context
    _task_context = task
    try:
        return _original_execution_run_task(task, *args, **kwargs)
    finally:
        _task_context = prior


worker.execution.run_task = execution_run_task
core.active_jars = active_jars
worker.core.active_jars = active_jars
worker.execution.worker.active_jars = active_jars


def main(argv: list[str] | None = None) -> int:
    return worker.main(sys.argv[1:] if argv is None else argv)


if __name__ == "__main__":
    raise SystemExit(main())
