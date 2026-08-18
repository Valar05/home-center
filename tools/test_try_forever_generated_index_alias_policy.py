#!/usr/bin/env python3

import sys
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from try_forever_generated_index_alias_policy import (
    GeneratedIndexAliasConflictError,
    GeneratedIndexAliasResourceLimitError,
    GeneratedIndexAliasTypeError,
    MAX_GENERATED_INDEX_SCALAR_TEXT_CHARS,
    resolve_consistent_alias,
)


SOURCE_HEAD_KEYS = ("sourceHead", "source_head", "gitHead", "git_head")
GENERATED_AT_KEYS = (
    "generatedAt",
    "generated_at",
    "generatedAtMs",
    "generated_at_ms",
    "updatedAt",
    "updated_at",
)
DIRTY_KEYS = ("dirtySource", "dirty_source", "sourceDirty", "source_dirty")


class GeneratedIndexAliasPolicyTest(unittest.TestCase):
    def test_one_source_head_alias_is_admitted(self):
        resolved = resolve_consistent_alias(
            {"sourceHead": "abc123"},
            SOURCE_HEAD_KEYS,
            field="sourceHead",
            allowed_types=(str,),
        )
        self.assertEqual(("sourceHead",), resolved.present_keys)
        self.assertEqual("abc123", resolved.value)

    def test_equal_typed_aliases_are_unambiguous(self):
        resolved = resolve_consistent_alias(
            {"sourceHead": "abc123", "git_head": "abc123"},
            SOURCE_HEAD_KEYS,
            field="sourceHead",
            allowed_types=(str,),
        )
        self.assertEqual("abc123", resolved.value)

    def test_conflicting_source_head_aliases_fail_closed(self):
        with self.assertRaises(GeneratedIndexAliasConflictError):
            resolve_consistent_alias(
                {"sourceHead": "good", "git_head": "stale"},
                SOURCE_HEAD_KEYS,
                field="sourceHead",
                allowed_types=(str,),
            )

    def test_bool_timestamp_does_not_sneak_through_int_subclassing(self):
        with self.assertRaises(GeneratedIndexAliasTypeError):
            resolve_consistent_alias(
                {"generatedAt": True},
                GENERATED_AT_KEYS,
                field="generatedAt",
                allowed_types=(str, int, float),
            )

    def test_numeric_aliases_must_match_type_as_well_as_value(self):
        with self.assertRaises(GeneratedIndexAliasConflictError):
            resolve_consistent_alias(
                {"generatedAtMs": 1, "updatedAt": 1.0},
                GENERATED_AT_KEYS,
                field="generatedAt",
                allowed_types=(str, int, float),
            )

    def test_dirty_source_requires_boolean_shape(self):
        with self.assertRaises(GeneratedIndexAliasTypeError):
            resolve_consistent_alias(
                {"dirtySource": "false"},
                DIRTY_KEYS,
                field="dirtySource",
                allowed_types=(bool,),
            )

    def test_scalar_text_budget_is_hard(self):
        hostile = "x" * (MAX_GENERATED_INDEX_SCALAR_TEXT_CHARS + 1)
        with self.assertRaises(GeneratedIndexAliasResourceLimitError):
            resolve_consistent_alias(
                {"sourceHead": hostile},
                SOURCE_HEAD_KEYS,
                field="sourceHead",
                allowed_types=(str,),
            )

    def test_missing_alias_family_remains_missing(self):
        resolved = resolve_consistent_alias(
            {},
            SOURCE_HEAD_KEYS,
            field="sourceHead",
            allowed_types=(str,),
        )
        self.assertEqual((), resolved.present_keys)
        self.assertIsNone(resolved.value)


if __name__ == "__main__":
    unittest.main()
