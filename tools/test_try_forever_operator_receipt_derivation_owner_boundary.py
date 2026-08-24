#!/usr/bin/env python3
"""Source boundary for existing-owner receipt derivation and field-set custody.

SOURCE ONLY. Current expected state: derivation SOURCE_WIRED; exact final field-set owner wiring RED;
regression execution unobserved.
"""

import ast
from pathlib import Path


OWNER = Path(__file__).with_name(
    "try_forever_owner_surgery_descriptor_shadow_operator_receipt.py"
)
EXPECTED_HELPER = "verify_operator_receipt_derivation_against_raw_evidence"
EXPECTED_POLICY_CALL = "require_operator_receipt_projection_derivation"
EXPECTED_FIELDSET_KEYWORD = "allowed_extra_fields"


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
    assert any(
        keyword.arg == EXPECTED_FIELDSET_KEYWORD for keyword in policy_calls[0].keywords
    ), (
        "RED: final v4 owner must close the exact receipt field namespace by supplying "
        "allowed_extra_fields to derivation custody"
    )

    build = functions.get("build_descriptor_shadow_operator_receipt")
    assert isinstance(build, ast.FunctionDef)
    assert any(call_name(call) == EXPECTED_HELPER for call in direct_calls(build)), (
        "normal build path must retain direct derivation custody before returning the final receipt"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
