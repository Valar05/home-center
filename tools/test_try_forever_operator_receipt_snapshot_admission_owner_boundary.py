#!/usr/bin/env python3
"""RED / UNEXECUTED owner boundary for bounded exact-container snapshot admission.

This fixture must remain RED until the existing snapshot-custody organ consumes the supporting
admission policy. It proves source ownership only; it is never TESTED/runtime/deployment evidence.
"""

import ast
from pathlib import Path


OWNER = Path(__file__).with_name("try_forever_operator_receipt_snapshot_custody.py")
POLICY_MODULE = "try_forever_operator_receipt_snapshot_admission_policy"


def direct_calls(function: ast.FunctionDef) -> list[tuple[int, ast.Call]]:
    calls: list[tuple[int, ast.Call]] = []

    def visit(node: ast.AST) -> None:
        if node is not function and isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)
        ):
            return
        if isinstance(node, ast.Call):
            calls.append((getattr(node, "lineno", -1), node))
        for child in ast.iter_child_nodes(node):
            visit(child)

    for statement in function.body:
        visit(statement)
    return calls


def call_name(call: ast.Call) -> str | None:
    return call.func.id if isinstance(call.func, ast.Name) else None


def has_call(function: ast.FunctionDef, name: str, argument: str) -> bool:
    for _line, call in direct_calls(function):
        if call_name(call) != name:
            continue
        if call.args and isinstance(call.args[0], ast.Name) and call.args[0].id == argument:
            return True
    return False


def main() -> int:
    source = OWNER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = False
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == POLICY_MODULE:
            names = {alias.name for alias in node.names}
            imported = {"admit_diagnostic_context", "is_exact_json_object"} <= names
    assert imported, "snapshot owner does not import exact-container/diagnostic admission policy"

    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    recursive = functions["_snapshot_json_value"]
    root = functions["snapshot_json_mapping"]

    assert has_call(recursive, "is_exact_json_object", "value"), (
        "nested snapshot object admission still accepts arbitrary Mapping callbacks"
    )
    assert has_call(root, "is_exact_json_object", "value"), (
        "root snapshot object admission still accepts arbitrary Mapping callbacks"
    )

    calls = direct_calls(root)
    diagnostic_admission_lines = [
        line
        for line, call in calls
        if call_name(call) == "admit_diagnostic_context"
        and call.args
        and isinstance(call.args[0], ast.Name)
        and call.args[0].id == "field"
    ]
    diagnostic_projection_lines = [
        line
        for line, call in calls
        if call_name(call) == "_diagnostic_root"
        and call.args
        and isinstance(call.args[0], ast.Name)
        and call.args[0].id in {"field", "diagnostic_context"}
    ]
    assert diagnostic_admission_lines, "root diagnostic context lacks pre-projection admission"
    assert diagnostic_projection_lines, "snapshot owner lost its bounded diagnostic projection"
    assert min(diagnostic_admission_lines) < min(diagnostic_projection_lines), (
        "diagnostic context must be admitted before JSON escaping/projection work"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
