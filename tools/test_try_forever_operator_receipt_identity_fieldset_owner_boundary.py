#!/usr/bin/env python3
"""RED SOURCE/UNEXECUTED owner boundary for final-v4 identity field-set custody.

This fixture is intentionally red until the existing final receipt owner consumes the supporting
fieldset gate inside its ordinary final-receipt contract, before digest trust. It proves source shape
only; it is not runtime or TESTED evidence.
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


def direct_calls(function: ast.FunctionDef) -> set[str]:
    names = set()
    for statement in function.body:
        for node in ast.walk(statement):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)) and node is not function:
                continue
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                names.add(node.func.id)
    return names


def main() -> int:
    source = OWNER.read_text(encoding="utf-8")
    tree = ast.parse(source)

    imports_gate = "from try_forever_operator_receipt_identity_fieldset import" in source
    final_contract = direct_function(tree, "_require_final_receipt_contract")
    calls = direct_calls(final_contract)

    assert imports_gate, "RED: final receipt owner has not imported exact identity fieldset custody"
    assert "require_exact_final_receipt_fieldset" in calls, (
        "RED: final receipt contract does not close the exact field namespace before identity trust"
    )

    identity = direct_function(tree, "verify_operator_receipt_identity")
    identity_calls = direct_calls(identity)
    assert "_require_final_receipt_contract" in identity_calls

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
