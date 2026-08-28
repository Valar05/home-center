#!/usr/bin/env python3
"""SOURCE-ONLY convergence fixture for canonical v10 → exact-observation semantic producer composition.

The existing canonical custody owner must observe each artifact once, then delegate patch/delta
semantics to the already-owned pure ``parse_owner_surgery_observation`` producer. The fixture also
rejects split semantic parsing inside either canonical inspection function. Presence of this file is
not regression execution or TESTED evidence.
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

        segment = ast.get_source_segment(source, function)
        assert segment is not None
        assert segment.index("_observe_bounded_utf8") < segment.index(
            "parse_owner_surgery_observation"
        )
        assert "admit_patch_metadata(" not in segment
        assert "admit_default_owner_from_patch(" not in segment
        assert "json.loads(" not in segment
        assert "semantic.artifact_sha256" in segment
        assert "semantic.artifact_byte_count" in segment
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
