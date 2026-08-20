#!/usr/bin/env python3
"""Hostile source fixtures for strict generated-index JSON admission.

These fixtures are regression source until an authorized runner executes them.
"""

import math
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from try_forever_generated_index_json_policy import (
    MAX_JSON_NUMBER_TOKEN_CHARS,
    GeneratedIndexJsonDuplicateMemberError,
    GeneratedIndexJsonNumberError,
    GeneratedIndexJsonSyntaxError,
    parse_generated_index_json,
)


class GeneratedIndexJsonPolicyTest(unittest.TestCase):
    def test_valid_metadata_preserves_exact_supported_shapes(self):
        value = parse_generated_index_json(
            '{"sourceHead":"0123","generatedAt":1234,"dirtySource":false,"extra":{"note":"x"}}'
        )
        self.assertEqual(value["sourceHead"], "0123")
        self.assertEqual(value["generatedAt"], 1234)
        self.assertIs(value["dirtySource"], False)
        self.assertEqual(value["extra"], {"note": "x"})

    def test_duplicate_member_is_rejected_even_when_values_match(self):
        for text in (
            '{"sourceHead":"a","sourceHead":"b"}',
            '{"sourceHead":"a","sourceHead":"a"}',
            '{"outer":{"x":1,"x":1}}',
        ):
            with self.subTest(text=text):
                with self.assertRaises(GeneratedIndexJsonDuplicateMemberError):
                    parse_generated_index_json(text)

    def test_nonstandard_numeric_constants_are_rejected(self):
        for token in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(token=token):
                with self.assertRaises(GeneratedIndexJsonNumberError):
                    parse_generated_index_json('{"generatedAt":' + token + "}")

    def test_nonfinite_standard_float_is_rejected(self):
        with self.assertRaises(GeneratedIndexJsonNumberError):
            parse_generated_index_json('{"generatedAt":1e9999}')

    def test_numeric_token_budget_rejects_before_large_int_conversion(self):
        token = "1" * (MAX_JSON_NUMBER_TOKEN_CHARS + 1)
        with self.assertRaises(GeneratedIndexJsonNumberError):
            parse_generated_index_json('{"generatedAt":' + token + "}")

    def test_syntax_and_decoder_recursion_fail_inside_typed_boundary(self):
        with self.assertRaises(GeneratedIndexJsonSyntaxError):
            parse_generated_index_json('{"sourceHead":')

        # Do not depend on the runner's global recursion limit. Pin the owner's
        # required failure-containment behavior directly.
        with patch(
            "try_forever_generated_index_json_policy.json.loads",
            side_effect=RecursionError("host parser recursion limit"),
        ):
            with self.assertRaises(GeneratedIndexJsonSyntaxError):
                parse_generated_index_json("{}")

    def test_duplicate_like_text_inside_string_is_inert(self):
        value = parse_generated_index_json(
            '{"note":"\\\"x\\\":1, \\\"x\\\":2","generatedAt":1.5}'
        )
        self.assertEqual(value["note"], '"x":1, "x":2')
        self.assertTrue(math.isfinite(value["generatedAt"]))

    def test_non_string_input_fails_closed(self):
        with self.assertRaises(GeneratedIndexJsonSyntaxError):
            parse_generated_index_json(b'{"x":1}')  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
