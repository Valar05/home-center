#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEST_FILES = (
    "test_chekhov_kinesis_engine.py",
    "test_chekhov_kinesis_runtime_contract.py",
)


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load test module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    failures: list[tuple[str, str, str]] = []
    count = 0

    for filename in TEST_FILES:
        path = ROOT / filename
        module = load_module(path)
        for name in sorted(vars(module)):
            fn = getattr(module, name)
            if not name.startswith("test_") or not callable(fn):
                continue
            count += 1
            try:
                fn()
            except Exception:
                failures.append((filename, name, traceback.format_exc()))
                print(f"FAIL {filename}::{name}")
            else:
                print(f"PASS {filename}::{name}")

    if failures:
        print()
        for filename, name, trace in failures:
            print(f"--- {filename}::{name} ---")
            print(trace.rstrip())
        print(f"FAIL {len(failures)}/{count} Chekhov kinesis contracts")
        return 1

    print(f"PASS {count} Chekhov kinesis contracts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
