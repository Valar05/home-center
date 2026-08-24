#!/usr/bin/env python3
"""SOURCE / UNEXECUTED owner boundary for final-v4 identity field-set custody.

The existing final receipt owner is now source-wired to consume the supporting fieldset gate inside
its ordinary final-receipt contract, before digest trust. This fixture proves that source shape only;
it is not runtime or TESTED evidence.
"""

import ast
from pathlib import Path


OWNER = Path(__file__).with_name(
    "try_forever_owner_surgery_descriptor_shadow_operator_receipt.py"
)


def direct_function(tree: ast.Module, name: str) -> ast.FunctionDef:
    matches = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name]
    assert len(matches) == 1, f"expected one direct owner function {name}"
    return matches[0]


class DirectCallVisitor(ast.NodeVisitor):
    """Collect calls owned by one function body without nested-function counterfeit evidence."""

    def __init__(self):
        self.names: set[str] = set()

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            self.names.add(node.func.id)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        return

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        return

    def visit_Lambda(self, node: ast.Lambda):
        return


def direct_calls(function: ast.FunctionDef) -> set[str]:
    visitor = DirectCallVisitor()
    for statement in function.body:
        visitor.visit(statement)
    return visitor.names


def main() -> int:
    source = OWNER.read_text(encoding="utf-8")
    tree = ast.parse(source)

    imports_gate = "from try_forever_operator_receipt_identity_fieldset import" in source
    final_contract = direct_function(tree, "_require_final_receipt_contract")
    calls = direct_calls(final_contract)

    assert imports_gate, "final receipt owner must import exact identity fieldset custody"
    assert "require_exact_final_receipt_fieldset" in calls, (
        "final receipt contract must close the exact field namespace before identity trust"
    )

    identity = direct_function(tree, "verify_operator_receipt_identity")
    identity_calls = direct_calls(identity)
    assert "_require_final_receipt_contract" in identity_calls

    # Counterfeit wiring hidden in a nested function must not satisfy the direct owner contract.
    counterfeit = ast.parse(
        "def owner():\n"
        "    def decoy():\n"
        "        require_exact_final_receipt_fieldset({})\n"
        "    return True\n"
    )
    assert "require_exact_final_receipt_fieldset" not in direct_calls(
        direct_function(counterfeit, "owner")
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
