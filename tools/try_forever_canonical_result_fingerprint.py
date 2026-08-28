#!/usr/bin/env python3
"""Deterministic evidence identity for canonical owner-surgery result payloads.

This supporting organ exists for one narrow distinction: a canonical-result receipt fingerprint must
remain deterministic even when JSON-shaped source evidence contains a Python surrogate code point
(for example, a POSIX filename decoded through surrogateescape). It does not grant schema admission,
promotion authority, TESTED, runtime, deployment, phone delivery, filesystem atomicity, or
acceptance.

Canonical fingerprint custody now reuses the existing one-observation bounded JSON snapshot organ.
The root and every nested object/list/scalar must already be exact JSON-shaped Python evidence before
serialization: tuples, dict subclasses, non-string keys, non-finite numbers, and other Python shapes
cannot be normalized by ``json.dumps`` into an identity they did not originally possess. The snapshot
organ also supplies the finite depth/node/text/integer/encoded-size throat before fingerprint work.

For ordinary exact JSON with valid Unicode, fingerprint bytes are intentionally unchanged: sorted
compact JSON, ``ensure_ascii=False``, encoded as UTF-8. ``surrogatepass`` changes only the otherwise
unencodable surrogate case, so valid-Unicode fingerprints do not churn merely to close hostile-path
wounds.

Hostile recursive/deep evidence and JSON encoder failures stay inside this organ's typed failure
boundary. This module owns no second snapshot, receipt owner, projector, phone surface, or P0 lane.
"""

from __future__ import annotations

import hashlib
import json

from try_forever_operator_receipt_snapshot_custody import (
    OperatorReceiptSnapshotCustodyError,
    snapshot_json_mapping,
)


SCHEMA = "try-forever-canonical-result-fingerprint.v1"


class CanonicalResultFingerprintError(ValueError):
    """Canonical result cannot be represented as deterministic exact JSON-shaped evidence."""


def canonical_result_sha256(result: dict[str, object]) -> str:
    """Return deterministic SHA-256 identity for one exact built-in-dict result payload.

    The public type contract intentionally matches the runtime admission contract owned by
    ``snapshot_json_mapping``: arbitrary ``Mapping`` implementations are not accepted evidence.
    This hash is receipt/evidence association only. It is not canonical artifact identity and must
    never be used as promotion authority or proof of filesystem atomicity.
    """

    try:
        snapshot = snapshot_json_mapping(result, field="canonical result")
        text = json.dumps(
            snapshot,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        encoded = text.encode("utf-8", errors="surrogatepass")
    except OperatorReceiptSnapshotCustodyError as exc:
        raise CanonicalResultFingerprintError(
            "canonical result failed exact bounded JSON snapshot custody"
        ) from exc
    except (TypeError, ValueError, UnicodeError, OverflowError, RecursionError) as exc:
        raise CanonicalResultFingerprintError(
            "canonical result is not deterministic JSON evidence"
        ) from exc

    return hashlib.sha256(encoded).hexdigest()
