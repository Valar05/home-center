#!/usr/bin/env python3
"""Regression source for exact-container receipt evidence boundaries.

SOURCE ONLY / UNEXECUTED. This fixture proves repaired receipt/temporal surfaces reject caller-owned
Mapping/dict-subclass/tuple-subclass callbacks before evidence traversal. It does not establish
TESTED, runtime, deployment, delivery, acceptance, phone, or P0 capability.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path
import unittest

from try_forever_operator_receipt_derivation_custody import (
    OperatorReceiptDerivationError,
    require_operator_receipt_projection_derivation,
)
from try_forever_operator_receipt_identity_fieldset import (
    OperatorReceiptIdentityFieldsetError,
    require_exact_final_receipt_fieldset,
)
from try_forever_owner_surgery_shadow_temporal_binding import (
    TemporalBindingEvidenceError,
    evaluate_temporal_content_binding,
)
from try_forever_owner_surgery_shadow_temporal_receipt_integrity import (
    ShadowTemporalReceiptIntegrityError,
    evaluate_temporal_content_binding_with_receipt_integrity,
)


ROOT = Path(__file__).resolve().parents[1]


class CallbackMapping(Mapping[str, object]):
    def __init__(self) -> None:
        self.callbacks = 0

    def __getitem__(self, key: str) -> object:
        self.callbacks += 1
        raise AssertionError("caller mapping callback executed")

    def __iter__(self):
        self.callbacks += 1
        raise AssertionError("caller mapping callback executed")

    def __len__(self) -> int:
        self.callbacks += 1
        raise AssertionError("caller mapping callback executed")

    def get(self, key: str, default=None):
        self.callbacks += 1
        raise AssertionError("caller mapping callback executed")

    def items(self):
        self.callbacks += 1
        raise AssertionError("caller mapping callback executed")

    def keys(self):
        self.callbacks += 1
        raise AssertionError("caller mapping callback executed")


class CallbackDict(dict):
    callbacks = 0

    def get(self, key, default=None):
        type(self).callbacks += 1
        raise AssertionError("caller dict-subclass callback executed")

    def items(self):
        type(self).callbacks += 1
        raise AssertionError("caller dict-subclass callback executed")


class CallbackTuple(tuple):
    callbacks = 0

    def __iter__(self):
        type(self).callbacks += 1
        raise AssertionError("caller tuple callback executed")


class ExactContainerReceiptSurfaceTest(unittest.TestCase):
    def test_derivation_rejects_mapping_before_callbacks(self) -> None:
        hostile = CallbackMapping()
        with self.assertRaises(OperatorReceiptDerivationError):
            require_operator_receipt_projection_derivation(
                ROOT,
                hostile,  # type: ignore[arg-type]
                {},
            )
        self.assertEqual(hostile.callbacks, 0)

    def test_derivation_rejects_hostile_raw_mapping_before_callbacks(self) -> None:
        hostile = CallbackMapping()
        with self.assertRaises(OperatorReceiptDerivationError):
            require_operator_receipt_projection_derivation(
                ROOT,
                {},
                hostile,  # type: ignore[arg-type]
            )
        self.assertEqual(hostile.callbacks, 0)

    def test_fieldset_rejects_mapping_before_callbacks(self) -> None:
        hostile = CallbackMapping()
        with self.assertRaises(OperatorReceiptIdentityFieldsetError):
            require_exact_final_receipt_fieldset(
                hostile,  # type: ignore[arg-type]
                operator_owned_fields=(),
                denied_capability_fields=(),
            )
        self.assertEqual(hostile.callbacks, 0)

    def test_field_family_rejects_tuple_subclass_before_iteration(self) -> None:
        CallbackTuple.callbacks = 0
        hostile = CallbackTuple(("operatorReceiptSha256",))
        with self.assertRaises(OperatorReceiptIdentityFieldsetError):
            require_exact_final_receipt_fieldset(
                {},
                operator_owned_fields=hostile,  # type: ignore[arg-type]
                denied_capability_fields=(),
            )
        self.assertEqual(CallbackTuple.callbacks, 0)

    def test_temporal_binding_rejects_root_mapping_before_callbacks(self) -> None:
        hostile = CallbackMapping()
        with self.assertRaises(TemporalBindingEvidenceError):
            evaluate_temporal_content_binding(
                hostile,  # type: ignore[arg-type]
                {},
            )
        self.assertEqual(hostile.callbacks, 0)

    def test_temporal_receipt_integrity_rejects_root_mapping_before_callbacks(self) -> None:
        hostile = CallbackMapping()
        with self.assertRaises(ShadowTemporalReceiptIntegrityError):
            evaluate_temporal_content_binding_with_receipt_integrity(
                {},
                hostile,  # type: ignore[arg-type]
            )
        self.assertEqual(hostile.callbacks, 0)

    def test_temporal_binding_rejects_nested_dict_subclass_before_callbacks(self) -> None:
        CallbackDict.callbacks = 0
        hostile_nested = CallbackDict({"path": "patches/example.patch"})
        with self.assertRaises(TemporalBindingEvidenceError):
            evaluate_temporal_content_binding(
                {
                    "schema": "try-forever-owner-surgery-custody.v10",
                    "nestedHostile": hostile_nested,
                },
                {},
            )
        self.assertEqual(CallbackDict.callbacks, 0)

    def test_temporal_receipt_integrity_rejects_nested_dict_subclass_before_callbacks(self) -> None:
        CallbackDict.callbacks = 0
        hostile_nested = CallbackDict({"status": "SHADOW_MATCH"})
        with self.assertRaises(ShadowTemporalReceiptIntegrityError):
            evaluate_temporal_content_binding_with_receipt_integrity(
                {},
                {
                    "schema": "try-forever-owner-surgery-descriptor-shadow.v3",
                    "nestedHostile": hostile_nested,
                },
            )
        self.assertEqual(CallbackDict.callbacks, 0)

    def test_plain_temporal_dict_reaches_semantic_schema_gate(self) -> None:
        with self.assertRaisesRegex(
            TemporalBindingEvidenceError,
            "exact canonical custody v10",
        ):
            evaluate_temporal_content_binding({}, {})
        with self.assertRaisesRegex(
            ShadowTemporalReceiptIntegrityError,
            "exact canonical owner-surgery custody v10",
        ):
            evaluate_temporal_content_binding_with_receipt_integrity({}, {})

    def test_public_repaired_surfaces_advertise_exact_containers(self) -> None:
        expectations = {
            "tools/try_forever_operator_receipt_derivation_custody.py": {
                "require_operator_receipt_projection_derivation": {
                    "receipt": "dict[str, object]",
                    "raw_result": "dict[str, object]",
                    "allowed_extra_fields": "tuple[str, ...] | None",
                }
            },
            "tools/try_forever_operator_receipt_identity_fieldset.py": {
                "require_exact_final_receipt_fieldset": {
                    "receipt": "dict[str, object]",
                    "operator_owned_fields": "tuple[str, ...]",
                    "denied_capability_fields": "tuple[str, ...]",
                }
            },
            "tools/try_forever_owner_surgery_shadow_temporal_binding.py": {
                "evaluate_temporal_content_binding": {
                    "canonical_result": "dict[str, object]",
                    "shadow_result": "dict[str, object]",
                }
            },
            "tools/try_forever_owner_surgery_shadow_temporal_receipt_integrity.py": {
                "evaluate_temporal_content_binding_with_receipt_integrity": {
                    "canonical_result": "dict[str, object]",
                    "shadow_result": "dict[str, object]",
                }
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
                    self.assertEqual(annotations.get(parameter), expected_annotation)


if __name__ == "__main__":
    unittest.main()
