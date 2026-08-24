#!/usr/bin/env python3
"""RED / UNEXECUTED owner boundary for one-observation final-receipt verification custody.

The final v4 receipt owner currently accepts arbitrary Mapping instances and validates/hash-links them
across multiple reads. Promotion is complete only when identity, raw-linkage, and derivation
verification snapshot caller-owned receipt/raw mappings once before semantic/digest work.
"""

import ast
from pathlib import Path


OWNER = Path(__file__).with_name(
    "try_forever_owner_surgery_descriptor_shadow_operator_receipt.py"
)
REQUIRED_FUNCTIONS = {
    "verify_operator_receipt_identity": {"receipt"},
    "verify_operator_receipt_against_raw_evidence": {"receipt", "raw_result"},
    "verify_operator_receipt_derivation_against_raw_evidence": {"receipt", "raw_result"},
}


def direct_calls(function: ast.FunctionDef) -> list[ast.Call]:
    calls: list[ast.Call] = []
    for statement in function.body:
        for node in ast.walk(statement):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)) and node is not function:
                continue
            if isinstance(node, ast.Call):
                calls.append(node)
    return calls


def call_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    return None


def main() -> int:
    source = OWNER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports_snapshot = "try_forever_operator_receipt_snapshot_custody" in source
    assert imports_snapshot, "final receipt owner does not import snapshot custody"

    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    for name, required_inputs in REQUIRED_FUNCTIONS.items():
        function = functions.get(name)
        assert function is not None, f"missing owner verifier {name}"
        calls = direct_calls(function)
        snapshots = [
            call
            for call in calls
            if call_name(call) in {"snapshot_json_mapping", "snapshot_verification_inputs"}
        ]
        assert snapshots, f"{name} does not establish one-observation snapshot custody"

        referenced_inputs = {
            argument.id
            for call in snapshots
            for argument in call.args
            if isinstance(argument, ast.Name)
        }
        missing = required_inputs - referenced_inputs
        assert not missing, f"{name} does not snapshot owner input(s): {sorted(missing)}"

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
