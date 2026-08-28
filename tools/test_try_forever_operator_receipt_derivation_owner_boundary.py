#!/usr/bin/env python3
"""Source boundary for existing-owner receipt derivation and field-set custody.

SOURCE ONLY. Current expected source state: projection derivation SOURCE_WIRED; exact final field-set
owner wiring SOURCE_WIRED; regression execution unobserved.
"""

import ast
from pathlib import Path


OWNER = Path(__file__).with_name(
    "try_forever_owner_surgery_descriptor_shadow_operator_receipt.py"
)
EXPECTED_HELPER = "verify_operator_receipt_derivation_against_raw_evidence"
EXPECTED_POLICY_CALL = "require_operator_receipt_projection_derivation"
EXPECTED_FIELDSET_KEYWORD = "allowed_extra_fields"
EXPECTED_FIELD_FAMILIES = (
    "OPERATOR_OWNED_RECEIPT_FIELDS",
    "FINAL_DENIED_CAPABILITY_FIELDS",
)


def direct_calls(function: ast.FunctionDef) -> list[ast.Call]:
    """Collect calls owned by this function while ignoring nested function bodies."""

    calls: list[ast.Call] = []

    class DirectVisitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            if node is function:
                for statement in node.body:
                    self.visit(statement)

        def visit_AsyncFunctionDef(self, node):
            if node is function:
                for statement in node.body:
                    self.visit(statement)

        def visit_Call(self, node):
            calls.append(node)
            self.generic_visit(node)

    DirectVisitor().visit(function)
    return calls


def call_name(call: ast.Call) -> str | None:
    target = call.func
    if isinstance(target, ast.Name):
        return target.id
    if isinstance(target, ast.Attribute):
        return target.attr
    return None


def exact_allowed_field_families(call: ast.Call) -> tuple[str, ...] | None:
    """Return the exact starred field-family names supplied to allowed_extra_fields."""

    keyword = next(
        (item for item in call.keywords if item.arg == EXPECTED_FIELDSET_KEYWORD),
        None,
    )
    if keyword is None or not isinstance(keyword.value, ast.Tuple):
        return None

    names: list[str] = []
    for element in keyword.value.elts:
        if not isinstance(element, ast.Starred) or not isinstance(element.value, ast.Name):
            return None
        names.append(element.value.id)
    return tuple(names)


def main() -> int:
    tree = ast.parse(OWNER.read_text(encoding="utf-8"), filename=str(OWNER))
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    helper = functions.get(EXPECTED_HELPER)
    assert isinstance(helper, ast.FunctionDef), (
        "existing final receipt owner must retain the derivation-custody reverification helper"
    )
    policy_calls = [
        call for call in direct_calls(helper) if call_name(call) == EXPECTED_POLICY_CALL
    ]
    assert len(policy_calls) == 1, (
        "derivation helper must consume the supporting projection-derivation policy exactly once"
    )
    assert exact_allowed_field_families(policy_calls[0]) == EXPECTED_FIELD_FAMILIES, (
        "final v4 owner must close the exact receipt field namespace with the actual operator-owned "
        "+ final denied-capability field families; a keyword-shaped empty/wrong allowlist is partial unsafe"
    )

    build = functions.get("build_descriptor_shadow_operator_receipt")
    assert isinstance(build, ast.FunctionDef)
    assert any(call_name(call) == EXPECTED_HELPER for call in direct_calls(build)), (
        "normal build path must retain direct derivation custody before returning the final receipt"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
