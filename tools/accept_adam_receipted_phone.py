#!/usr/bin/env python3
from __future__ import annotations

import adam_codex_phone as core
import adam_planned_venice as planned
from judgment_jar_runtime import active_jars

core.active_jars = active_jars
planned.core.active_jars = active_jars
planned.execution.worker.active_jars = active_jars

import accept_adam_executive_phone as acceptance


if __name__ == "__main__":
    raise SystemExit(acceptance.main())
