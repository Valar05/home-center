#!/usr/bin/env python3
"""Deterministic evidence identity for canonical owner-surgery result payloads.

This supporting organ exists for one narrow distinction: a canonical-result receipt fingerprint must
remain deterministic even when JSON-shaped source evidence contains a Python surrogate code point
(for example, a POSIX filename decoded through surrogateescape). It does not grant schema admission,
promotion authority, TESTED, runtime, deployment, phone delivery, filesystem atomicity, or
acceptance.

For ordinary Unicode text the encoding is intentionally identical to the current descriptor-shadow
fingerprint: sorted compact JSON, ``ensure_ascii=False``, encoded as UTF-8. ``surrogatepass`` changes
only the otherwise-unencodable surrogate case, so valid-Unicode fingerprints do not churn merely to
close the hostile-path wound.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping


SCHEMA = "try-forever-canonical-result-fingerprint.v1"


class CanonicalResultFingerprintError(ValueError):
    """Canonical result cannot be represented as deterministic JSON-shaped evidence."""


def canonical_result_sha256(result: Mapping[str, object]) -> str:
    """Return deterministic SHA-256 identity for one canonical result payload.

    This hash is receipt/evidence association only. It is not canonical artifact identity and must
    never be used as promotion authority or proof of filesystem atomicity.
    """

    if not isinstance(result, Mapping):
        raise CanonicalResultFingerprintError("canonical result must be one mapping")

    try:
        text = json.dumps(
            result,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        encoded = text.encode("utf-8", errors="surrogatepass")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise CanonicalResultFingerprintError(
            f"canonical result is not deterministic JSON evidence: {exc}"
        ) from exc

    return hashlib.sha256(encoded).hexdigest()
