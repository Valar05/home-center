#!/usr/bin/env python3
"""RED source boundary for existing-owner receipt derivation custody.

SOURCE ONLY. Current expected state: RED / owner integration not yet implemented.
"""

import ast
from pathlib import Path


OWNER = Path(__file__).with_name(
    "try_forever_owner_surgery_descriptor_shadow_operator_receipt.py"
)
EXPECTED_HELPER = "verify_operator_receipt_derivation_against_raw_evidence"
EXPECTED_POLICY_CALL = "require_operator_receipt_projection_derivation"


def direct_call_names(function: ast.FunctionDef) -> set[str]:
    """Collect calls owned by this function while ignoring nested function bodies."""

    names: set[str] = set()

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
            target = node.func
            if isinstance(target, ast.Name):
                names.add(target.id)
            elif isinstance(target, ast.Attribute):
                names.add(target.attr)
            self.generic_visit(node)

    DirectVisitor().visit(function)
    return names


def main() -> int:
    tree = ast.parse(OWNER.read_text(encoding="utf-8"), filename=str(OWNER))
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    helper = functions.get(EXPECTED_HELPER)
    assert isinstance(helper, ast.FunctionDef), (
        "RED: existing final receipt owner still lacks the derivation-custody reverification helper"
    )
    assert EXPECTED_POLICY_CALL in direct_call_names(helper), (
        "RED: derivation helper must consume the supporting projection-derivation policy directly"
    )

    build = functions.get("build_descriptor_shadow_operator_receipt")
    assert isinstance(build, ast.FunctionDef)
    assert EXPECTED_HELPER in direct_call_names(build), (
        "RED: normal build path must run derivation custody directly before returning the final receipt"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
