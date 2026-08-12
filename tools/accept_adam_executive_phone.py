#!/usr/bin/env python3
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import adam_exec_compat as compat


def main() -> int:
    cwd = str(ROOT)
    plan = compat.compatible_local_exec_plan([], "hello", cwd, 45)
    ok = plan.get("kind") == "say" and bool(str(plan.get("say") or "").strip()) and not str(plan.get("payload") or "").strip()
    receipt = {
        "schema": "adam-executive-phone-acceptance-v2",
        "ok": ok,
        "input": "hello",
        "expectedKind": "say",
        "plan": plan,
        "localExecutive": compat.adam.PHONE_LLM_URL,
        "model": compat.adam.PHONE_LLM_MODEL,
        "cwd": cwd,
    }
    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
