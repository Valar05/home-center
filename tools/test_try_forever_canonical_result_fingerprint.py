#!/usr/bin/env python3
"""Regression source for surrogate-safe canonical result fingerprint custody.

SOURCE ONLY. This file has not been observed executing in an authorized test lane.
"""

import hashlib
import json

from try_forever_canonical_result_fingerprint import canonical_result_sha256


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
    except ValueError:
        pass
    else:
        raise AssertionError("non-finite canonical evidence earned a result fingerprint")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
