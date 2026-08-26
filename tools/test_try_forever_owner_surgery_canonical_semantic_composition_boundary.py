#!/usr/bin/env python3
"""RED SOURCE-ONLY boundary for canonical v10 → exact-observation semantic producer composition.

This fixture is intentionally expected to remain RED until the existing canonical custody owner is
mutated in place. It forbids sidecar authority: both canonical patch and delta inspection functions
must call the already-owned pure ``parse_owner_surgery_observation`` producer after their bounded
artifact observation. Presence of this file is not regression execution or TESTED evidence.
"""

import ast
from pathlib import Path


OWNER = Path(__file__).with_name("try_forever_owner_surgery_custody_probe.py")


def _called_names(function: ast.FunctionDef) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(function):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            names.add(node.func.id)
    return names


def main() -> int:
    source = OWNER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    for function_name in ("inspect_patch", "inspect_delta"):
        function = functions[function_name]
        calls = _called_names(function)
        assert "_observe_bounded_utf8" in calls
        assert "parse_owner_surgery_observation" in calls
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
