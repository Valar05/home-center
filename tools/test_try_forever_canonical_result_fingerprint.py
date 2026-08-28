#!/usr/bin/env python3
"""Regression source for surrogate-safe canonical result fingerprint custody.

SOURCE ONLY. This file has not been observed executing in an authorized test lane.
"""

import hashlib
import json

from try_forever_canonical_result_fingerprint import (
    CanonicalResultFingerprintError,
    canonical_result_sha256,
)


def legacy_valid_unicode_sha256(payload):
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def expect_rejected(payload, message: str) -> None:
    try:
        canonical_result_sha256(payload)
    except CanonicalResultFingerprintError:
        return
    raise AssertionError(message)


def main() -> int:
    ordinary = {
        "schema": "try-forever-owner-surgery-custody.v10",
        "path": "patches/🦢-warm-wall.patch",
        "evidenceComplete": True,
        "nested": {"items": [1, 2, {"ok": True}]},
    }
    reordered = dict(reversed(list(ordinary.items())))

    # Exact valid JSON with ordinary Unicode retains the current fingerprint algorithm exactly.
    assert canonical_result_sha256(ordinary) == legacy_valid_unicode_sha256(ordinary)
    assert canonical_result_sha256(reordered) == canonical_result_sha256(ordinary)

    changed = dict(ordinary)
    changed["evidenceComplete"] = False
    assert canonical_result_sha256(changed) != canonical_result_sha256(ordinary)

    # The fingerprint boundary owns one detached exact JSON object. A root dict subclass is still
    # caller-owned Python behavior and must be rejected before overridden mapping callbacks run.
    callback_touched = {"root": False, "nested": False}

    class HostileRootDict(dict):
        def items(self):
            callback_touched["root"] = True
            raise AssertionError("caller-owned root dict callback executed")

    expect_rejected(
        HostileRootDict(ordinary),
        "dict-subclass root evidence earned a canonical result fingerprint",
    )
    assert callback_touched["root"] is False

    # Root exactness is not enough: nested Python containers must not normalize into JSON identity.
    class HostileNestedDict(dict):
        def items(self):
            callback_touched["nested"] = True
            raise AssertionError("caller-owned nested dict callback executed")

    expect_rejected(
        {"nested": HostileNestedDict({"value": 1})},
        "nested dict-subclass evidence earned a canonical result fingerprint",
    )
    assert callback_touched["nested"] is False

    # json.dumps would otherwise normalize tuple->array and integer object key->string key. The
    # fingerprint must represent exact JSON-shaped source evidence, not Python shapes after repair.
    expect_rejected(
        {"normalized": (1, 2)},
        "tuple evidence was normalized into a canonical JSON-array fingerprint",
    )
    expect_rejected(
        {"nested": {1: "value"}},
        "integer mapping key was normalized into canonical string-key evidence",
    )

    # A POSIX surrogateescape-shaped path is still deterministic evidence rather than an encoding
    # crash. The surrogate is evidence text here; this does not grant filesystem or promotion authority.
    hostile = {
        "schema": "try-forever-owner-surgery-custody.v10",
        "path": "patches/hostile-\udcff.patch",
        "evidenceComplete": True,
    }
    hostile_reordered = dict(reversed(list(hostile.items())))
    hostile_sha = canonical_result_sha256(hostile)
    assert len(hostile_sha) == 64
    assert set(hostile_sha) <= set("0123456789abcdef")
    assert canonical_result_sha256(hostile_reordered) == hostile_sha

    # Non-standard numeric evidence remains rejected rather than normalized into an identity.
    expect_rejected(
        {"value": float("nan")},
        "non-finite canonical evidence earned a result fingerprint",
    )

    # Deep hostile evidence must fail inside the fingerprint organ instead of leaking a raw
    # RecursionError through the receipt-verification chain. Construction itself remains iterative.
    deep = []
    cursor = deep
    for _ in range(2_048):
        child = []
        cursor.append(child)
        cursor = child
    expect_rejected(
        {"deep": deep},
        "deep recursive evidence escaped the typed fingerprint boundary",
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
