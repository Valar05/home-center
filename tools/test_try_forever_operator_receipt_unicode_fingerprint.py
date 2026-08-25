#!/usr/bin/env python3
"""Hostile source fixture for final-v4 operator receipt Unicode fingerprint custody.

SOURCE ONLY. This regression has not been observed executing in an authorized lane.

The existing canonical-result fingerprint organ already preserves ordinary valid-Unicode digest
identity while making surrogate-bearing JSON-shaped evidence deterministic through UTF-8
``surrogatepass``. The final operator receipt digest currently uses the same JSON serialization shape
but ordinary UTF-8 encoding, so a hostile allowed-field string containing a Python surrogate can
escape as an encoding failure instead of receiving deterministic evidence identity.

This fixture requires composition of the existing fingerprint organ; it does not authorize a second
digest implementation, receipt owner, projector, authority path, TESTED state, runtime capability,
phone delivery, or acceptance.
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
