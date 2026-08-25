#!/usr/bin/env python3
"""Hostile source fixture for final-v4 operator receipt Unicode fingerprint custody.

SOURCE ONLY. The existing final-v4 receipt owner is now SOURCE_WIRED to the shared fingerprint organ,
but this regression has not been observed executing in an authorized lane and therefore is not
TESTED evidence.

The existing canonical-result fingerprint organ preserves ordinary valid-Unicode digest identity
while making surrogate-bearing JSON-shaped evidence deterministic through UTF-8 ``surrogatepass``.
The final operator receipt owner now delegates to that same organ, so this fixture locks valid-Unicode
parity, deterministic surrogate evidence, material-drift sensitivity, and non-finite rejection.

This fixture requires continued composition of the existing fingerprint organ; it does not authorize
a second digest implementation, receipt owner, projector, authority path, TESTED state, runtime
capability, phone delivery, or acceptance.
"""

import hashlib
import json

import try_forever_owner_surgery_descriptor_shadow_operator_receipt as owner
from try_forever_canonical_result_fingerprint import (
    CanonicalResultFingerprintError,
    canonical_result_sha256,
)


def legacy_valid_unicode_digest(payload):
    text = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def expect_reject(callable_):
    try:
        callable_()
    except (ValueError, CanonicalResultFingerprintError):
        return
    raise AssertionError("expected non-finite evidence rejection")


def main() -> int:
    ordinary = {
        "summary": "Swan veil — café — 🦢",
        "tested": False,
        "counter": 3,
    }
    expected_legacy = legacy_valid_unicode_digest(ordinary)
    assert canonical_result_sha256(ordinary) == expected_legacy
    assert owner._operator_receipt_sha256(ordinary) == expected_legacy

    # Construct the hostile source value at runtime so this UTF-8 source file itself remains valid.
    hostile_surrogate = chr(0xDCFF)
    hostile = {
        "summary": f"surrogate-boundary:{hostile_surrogate}:held",
        "tested": False,
        "counter": 3,
    }
    first = owner._operator_receipt_sha256(hostile)
    second = owner._operator_receipt_sha256(dict(reversed(tuple(hostile.items()))))
    assert first == second
    assert first == canonical_result_sha256(hostile)
    assert len(first) == 64
    assert all(character in "0123456789abcdef" for character in first)

    material_drift = {**hostile, "counter": 4}
    assert owner._operator_receipt_sha256(material_drift) != first

    expect_reject(lambda: owner._operator_receipt_sha256({"value": float("nan")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
