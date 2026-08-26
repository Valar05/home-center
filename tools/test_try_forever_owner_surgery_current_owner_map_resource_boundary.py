#!/usr/bin/env python3
"""CONVERGENCE SOURCE / UNEXECUTED boundary for finite authenticated current-owner custody.

Canonical v10 rejects arbitrary Mapping implementations and hostile owner/blob scalar subclasses
before caller callbacks can earn authority. It now also bounds both exact current-owner evidence
entrances: direct exact built-in maps have finite cardinality/aggregate machine-text custody, and the
repeated-owner CLI parser has independent collection/aggregate throats before duplicate-same-owner
evidence can collapse into a tiny dict.

This fixture pins the existing-owner repair only. It does not create a second map/parser validator,
execute regressions, claim TESTED/runtime behavior, or touch the phone/P0 chain.
"""

import pytest

from try_forever_owner_surgery_custody_probe import (
    MAX_CURRENT_OWNER_CLI_ITEMS,
    MAX_CURRENT_OWNER_CLI_TOTAL_CODEPOINTS,
    MAX_CURRENT_OWNER_MAP_ITEMS,
    MAX_CURRENT_OWNER_MAP_TOTAL_CODEPOINTS,
    _admit_current_owner_blobs,
    _parse_owner_blob,
)


EXPECTED_MAP_ITEM_CEILING = 2_048
EXPECTED_MAP_TOTAL_CODEPOINT_CEILING = 1_048_576
EXPECTED_CLI_ITEM_CEILING = 2_048
EXPECTED_CLI_TOTAL_CODEPOINT_CEILING = 1_048_576
BLOB = "a" * 40


def _long_owner(index: int) -> str:
    prefix = f"owner-{index:04d}/"
    return prefix + ("x" * (4_096 - len(prefix)))


def test_existing_owner_exposes_the_pinned_finite_resource_throats():
    assert MAX_CURRENT_OWNER_MAP_ITEMS == EXPECTED_MAP_ITEM_CEILING
    assert MAX_CURRENT_OWNER_MAP_TOTAL_CODEPOINTS == EXPECTED_MAP_TOTAL_CODEPOINT_CEILING
    assert MAX_CURRENT_OWNER_CLI_ITEMS == EXPECTED_CLI_ITEM_CEILING
    assert MAX_CURRENT_OWNER_CLI_TOTAL_CODEPOINTS == EXPECTED_CLI_TOTAL_CODEPOINT_CEILING


def test_exact_map_max_plus_one_fails_before_full_pair_traversal():
    values = {f"owner/{index}": BLOB for index in range(EXPECTED_MAP_ITEM_CEILING + 1)}

    with pytest.raises(ValueError, match=r"current owner custody.*2,048.*entries"):
        _admit_current_owner_blobs(values)


def test_exact_map_aggregate_owner_blob_text_has_independent_source_ceiling():
    # 257 maximum-length admitted owner identities plus their exact 40-hex witnesses exceed 1 MiB
    # while remaining far below the item ceiling. The existing owner must stop once aggregate
    # admitted machine text crosses the finite throat.
    values = {_long_owner(index): BLOB for index in range(257)}
    assert len(values) < EXPECTED_MAP_ITEM_CEILING
    assert sum(len(owner) + len(blob) for owner, blob in values.items()) > EXPECTED_MAP_TOTAL_CODEPOINT_CEILING

    with pytest.raises(ValueError, match=r"current owner custody.*aggregate.*1,048,576.*code points"):
        _admit_current_owner_blobs(values)


def test_repeated_owner_parser_max_plus_one_has_its_own_collection_ceiling():
    values = [f"owner/{index}={BLOB}" for index in range(EXPECTED_CLI_ITEM_CEILING + 1)]

    with pytest.raises(ValueError, match=r"--current-owner custody.*2,048.*assignments"):
        _parse_owner_blob(values)


def test_repeated_duplicate_owner_text_cannot_bypass_aggregate_ceiling_by_collapsing_to_one_map_entry():
    owner = "x" * 4_096
    assignment = f"{owner}={BLOB}"
    values = [assignment] * 254
    assert len(values) < EXPECTED_CLI_ITEM_CEILING
    assert sum(map(len, values)) > EXPECTED_CLI_TOTAL_CODEPOINT_CEILING

    with pytest.raises(ValueError, match=r"--current-owner custody.*aggregate.*1,048,576.*code points"):
        _parse_owner_blob(values)


def test_ordinary_small_exact_map_semantics_remain_unchanged():
    values = {
        "android/operator-overlay/A.java": "1" * 40,
        "android/operator-overlay/B.java": "2" * 40,
    }
    admitted = _admit_current_owner_blobs(values)
    assert admitted == values
    assert admitted is not values


def test_ordinary_duplicate_same_owner_assignment_semantics_remain_unchanged():
    assignment = f"android/operator-overlay/A.java={BLOB}"
    assert _parse_owner_blob([assignment, assignment]) == {
        "android/operator-overlay/A.java": BLOB,
    }


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
