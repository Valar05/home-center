#!/usr/bin/env python3
"""RED source regression for final descriptor-shadow receipt public container contracts.

SOURCE ONLY / UNEXECUTED. Runtime snapshot custody already rejects arbitrary Mapping callbacks, so
public verification APIs must not advertise a broader Mapping capability than the exact built-in dict
boundary they consume. Projector/self-integrity are included as convergence controls.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path
import unittest

from try_forever_owner_surgery_descriptor_shadow_operator_receipt import (
    verify_operator_receipt_identity,
)


ROOT = Path(__file__).resolve().parents[1]


class CallbackMapping(Mapping[str, object]):
    def __init__(self) -> None:
        self.callbacks = 0

    def __getitem__(self, key: str) -> object:
        self.callbacks += 1
        raise AssertionError("caller Mapping callback executed")

    def __iter__(self):
        self.callbacks += 1
        raise AssertionError("caller Mapping callback executed")

    def __len__(self) -> int:
        self.callbacks += 1
        raise AssertionError("caller Mapping callback executed")

    def get(self, key: str, default=None):
        self.callbacks += 1
        raise AssertionError("caller Mapping callback executed")


class FinalReceiptPublicTypeContractTest(unittest.TestCase):
    def test_identity_runtime_rejects_mapping_before_callbacks(self) -> None:
        hostile = CallbackMapping()
        with self.assertRaises(ValueError):
            verify_operator_receipt_identity(hostile)  # type: ignore[arg-type]
        self.assertEqual(hostile.callbacks, 0)

    def test_public_receipt_surfaces_advertise_exact_dicts(self) -> None:
        expectations = {
            "tools/try_forever_owner_surgery_shadow_receipt_projection.py": {
                "project_shadow_receipt": {"result": "dict[str, object]"},
            },
            "tools/try_forever_owner_surgery_shadow_receipt_self_integrity.py": {
                "project_shadow_receipt_with_self_integrity": {"result": "dict[str, object]"},
            },
            "tools/try_forever_owner_surgery_descriptor_shadow_operator_receipt.py": {
                "verify_operator_receipt_identity": {"receipt": "dict[str, object]"},
                "verify_operator_receipt_against_raw_evidence": {
                    "receipt": "dict[str, object]",
                    "raw_result": "dict[str, object]",
                },
                "verify_operator_receipt_derivation_against_raw_evidence": {
                    "receipt": "dict[str, object]",
                    "raw_result": "dict[str, object]",
                },
            },
        }

        for relative_path, function_expectations in expectations.items():
            module = ast.parse((ROOT / relative_path).read_text(encoding="utf-8"))
            functions = {
                node.name: node
                for node in module.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            for function_name, expected_parameters in function_expectations.items():
                function = functions[function_name]
                args = [*function.args.args, *function.args.kwonlyargs]
                annotations = {
                    argument.arg: ast.unparse(argument.annotation)
                    for argument in args
                    if argument.annotation is not None
                }
                for parameter, expected_annotation in expected_parameters.items():
                    self.assertEqual(
                        annotations.get(parameter),
                        expected_annotation,
                        f"{relative_path}:{function_name} advertises stale container capability",
                    )


if __name__ == "__main__":
    unittest.main()
