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


def main() -> int:
    ordinary = {
        "schema": "try-forever-owner-surgery-custody.v10",
        "path": "patches/🦢-warm-wall.patch",
        "evidenceComplete": True,
    }
    reordered = dict(reversed(list(ordinary.items())))

    # Valid Unicode retains the current fingerprint algorithm exactly.
    assert canonical_result_sha256(ordinary) == legacy_valid_unicode_sha256(ordinary)
    assert canonical_result_sha256(reordered) == canonical_result_sha256(ordinary)

    changed = dict(ordinary)
    changed["evidenceComplete"] = False
    assert canonical_result_sha256(changed) != canonical_result_sha256(ordinary)

    # The fingerprint boundary owns one detached exact JSON object. A dict subclass is still
    # caller-owned Python behavior, even if it looks JSON-shaped, and must be rejected before any
    # overridden mapping callback can participate in evidence work.
    callback_touched = {"value": False}

    class HostileDict(dict):
        def items(self):
            callback_touched["value"] = True
            raise AssertionError("caller-owned dict callback executed")

    try:
        canonical_result_sha256(HostileDict(ordinary))
    except CanonicalResultFingerprintError:
        pass
    else:
        raise AssertionError("dict-subclass evidence earned a canonical result fingerprint")
    assert callback_touched["value"] is False

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
    try:
        canonical_result_sha256({"value": float("nan")})
    except CanonicalResultFingerprintError:
        pass
    else:
        raise AssertionError("non-finite canonical evidence earned a result fingerprint")

    # Deep hostile evidence must fail inside the fingerprint organ instead of leaking a raw
    # RecursionError through the receipt-verification chain. The exact depth is intentionally far
    # beyond the normal Python JSON recursion boundary while construction itself remains iterative.
    deep = []
    cursor = deep
    for _ in range(2_048):
        child = []
        cursor.append(child)
        cursor = child
    try:
        canonical_result_sha256({"deep": deep})
    except CanonicalResultFingerprintError:
        pass
    else:
        raise AssertionError("deep recursive evidence escaped the typed fingerprint boundary")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
