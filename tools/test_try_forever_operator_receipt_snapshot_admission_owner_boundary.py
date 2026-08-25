#!/usr/bin/env python3
"""RED / UNEXECUTED owner boundary for bounded exact-container snapshot admission.

This fixture must remain RED until the existing snapshot-custody organ *uses* the supporting
admission policy as a control-flow gate. Marker-shaped calls are insufficient: a no-op policy call
followed by legacy ``Mapping`` traversal must stay RED. This proves source ownership only; it is never
TESTED/runtime/deployment evidence.
"""

import ast
from pathlib import Path


OWNER = Path(__file__).with_name("try_forever_operator_receipt_snapshot_custody.py")
POLICY_MODULE = "try_forever_operator_receipt_snapshot_admission_policy"


def direct_nodes(function: ast.FunctionDef):
    """Yield nodes owned by this direct function body, excluding nested functions/lambdas."""

    def visit(node: ast.AST):
        if node is not function and isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)
        ):
            return
        yield node
        for child in ast.iter_child_nodes(node):
            yield from visit(child)

    for statement in function.body:
        yield from visit(statement)


def call_name(call: ast.Call) -> str | None:
    return call.func.id if isinstance(call.func, ast.Name) else None


def call_uses_name(call: ast.Call, function_name: str, argument_name: str) -> bool:
    return (
        call_name(call) == function_name
        and bool(call.args)
        and isinstance(call.args[0], ast.Name)
        and call.args[0].id == argument_name
    )


def test_contains_call(test: ast.AST, function_name: str, argument_name: str) -> bool:
    return any(
        isinstance(node, ast.Call)
        and call_uses_name(node, function_name, argument_name)
        for node in ast.walk(test)
    )


def branch_contains(function: ast.FunctionDef, *, predicate, consequence) -> bool:
    for node in direct_nodes(function):
        if not isinstance(node, ast.If) or not predicate(node.test):
            continue
        if any(consequence(child) for statement in node.body for child in ast.walk(statement)):
            return True
    return False


def has_legacy_mapping_gate(function: ast.FunctionDef) -> bool:
    for node in direct_nodes(function):
        if not isinstance(node, ast.Call) or call_name(node) != "isinstance":
            continue
        if len(node.args) < 2:
            continue
        first, second = node.args[0], node.args[1]
        if (
            isinstance(first, ast.Name)
            and first.id == "value"
            and isinstance(second, ast.Name)
            and second.id == "Mapping"
        ):
            return True
    return False


def diagnostic_admission_binding(function: ast.FunctionDef) -> tuple[str, int] | None:
    for node in direct_nodes(function):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        if not isinstance(node.targets[0], ast.Name) or not isinstance(node.value, ast.Call):
            continue
        if call_uses_name(node.value, "admit_diagnostic_context", "field"):
            return node.targets[0].id, node.lineno
    return None


def diagnostic_projection_line(function: ast.FunctionDef, admitted_name: str) -> int | None:
    for node in direct_nodes(function):
        if not isinstance(node, ast.Call) or call_name(node) != "_diagnostic_root":
            continue
        if (
            node.args
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id == admitted_name
        ):
            return node.lineno
    return None


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

    # Nested object admission must own a real return-producing branch, not a marker-shaped call.
    assert branch_contains(
        recursive,
        predicate=lambda test: test_contains_call(test, "is_exact_json_object", "value"),
        consequence=lambda node: isinstance(node, ast.Return),
    ), "nested snapshot admission policy is not a return-producing control-flow gate"

    # Root admission must own a fail-closed branch. A no-op policy call does not count.
    assert branch_contains(
        root,
        predicate=lambda test: test_contains_call(test, "is_exact_json_object", "value"),
        consequence=lambda node: isinstance(node, ast.Raise),
    ), "root snapshot admission policy is not a fail-closed control-flow gate"

    assert not has_legacy_mapping_gate(recursive), (
        "nested snapshot path still retains legacy isinstance(value, Mapping) authority"
    )
    assert not has_legacy_mapping_gate(root), (
        "root snapshot path still retains legacy isinstance(value, Mapping) authority"
    )

    # Diagnostic admission must produce the exact value later handed to the JSON-escaping projector.
    # A no-op call followed by _diagnostic_root(field) must remain RED.
    binding = diagnostic_admission_binding(root)
    assert binding is not None, "root diagnostic context lacks bound pre-projection admission"
    admitted_name, admitted_line = binding
    projection_line = diagnostic_projection_line(root, admitted_name)
    assert projection_line is not None, (
        "bounded diagnostic projector does not consume the admitted diagnostic context"
    )
    assert admitted_line < projection_line, (
        "diagnostic context must be admitted before JSON escaping/projection work"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
