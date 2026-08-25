#!/usr/bin/env python3
"""RED source boundary for final-v4 operator receipt surrogate-safe digest ownership.

SOURCE ONLY. This fixture has not executed in an authorized lane.

The existing final receipt owner must compose the existing canonical-result fingerprint organ inside
``_operator_receipt_sha256``. Merely importing the helper elsewhere, mentioning it in a comment, or
calling it from a nested function does not establish owner wiring.
"""

import ast
from pathlib import Path


OWNER = Path("tools/try_forever_owner_surgery_descriptor_shadow_operator_receipt.py")
SHARED_MODULE = "try_forever_canonical_result_fingerprint"
SHARED_CALL = "canonical_result_sha256"


def direct_calls(function: ast.FunctionDef) -> set[str]:
    calls: set[str] = set()

    class Visitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            if node is function:
                self.generic_visit(node)

        def visit_Lambda(self, node):
            return

        def visit_Call(self, node):
            target = node.func
            if isinstance(target, ast.Name):
                calls.add(target.id)
            elif isinstance(target, ast.Attribute):
                calls.add(target.attr)
            self.generic_visit(node)

    Visitor().visit(function)
    return calls


def main() -> int:
    source = OWNER.read_text(encoding="utf-8")
    tree = ast.parse(source)

    imported = False
    owner_function = None
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == SHARED_MODULE:
            imported = any(alias.name == SHARED_CALL for alias in node.names)
        if isinstance(node, ast.FunctionDef) and node.name == "_operator_receipt_sha256":
            owner_function = node

    assert imported, "final receipt owner must import the existing surrogate-safe fingerprint organ"
    assert owner_function is not None, "final receipt digest owner function is missing"

    calls = direct_calls(owner_function)
    assert SHARED_CALL in calls, (
        "final receipt digest owner must directly consume canonical_result_sha256; "
        "helper presence elsewhere is not owner wiring"
    )
    assert "_deterministic_json_sha256" not in calls, (
        "final receipt digest owner must not retain the ordinary UTF-8-only digest path"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
