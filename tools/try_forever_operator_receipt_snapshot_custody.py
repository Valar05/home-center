#!/usr/bin/env python3
"""One-observation JSON snapshot custody for operator receipt verification.

Verification code must not validate one view of a stateful ``Mapping`` and later hash/derive from a
second view of that same object. This supporting organ materializes one plain JSON-shaped ``dict``
once, then all semantic, digest, linkage, and derivation checks can consume that snapshot.

The snapshot is evidence custody only. It creates no receipt owner/projector, grants no authority,
TESTED/runtime/deployment/callability/execution/delivery/acceptance state, and has no phone/P0
mutation authority.
"""

from __future__ import annotations

import json
from collections.abc import Mapping


SCHEMA = "try-forever-operator-receipt-snapshot-custody.v1"


class OperatorReceiptSnapshotCustodyError(ValueError):
    """A verification input could not be captured as one stable JSON-shaped mapping."""


def snapshot_json_mapping(value: Mapping[str, object], *, field: str) -> dict[str, object]:
    """Capture one stable plain-dict observation of a JSON-shaped mapping.

    ``dict(value)`` intentionally snapshots the top-level mapping once before semantic checks. The
    JSON round-trip then detaches nested list/mapping structure from caller-owned mutable objects and
    rejects non-finite/non-JSON/over-nested values rather than allowing later verification stages to
    observe a different object graph. ``ensure_ascii=True`` keeps hostile surrogate-shaped strings
    bounded and representable during snapshotting without changing their decoded string identity.
    """

    if not isinstance(value, Mapping):
        raise OperatorReceiptSnapshotCustodyError(f"{field} must be one mapping")
    try:
        top_level = dict(value)
        encoded = json.dumps(
            top_level,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
        )
        snapshot = json.loads(encoded)
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise OperatorReceiptSnapshotCustodyError(
            f"{field} must be one finite JSON-shaped mapping"
        ) from exc

    if not isinstance(snapshot, dict):
        raise OperatorReceiptSnapshotCustodyError(f"{field} snapshot must remain one object")
    if any(not isinstance(name, str) or not name for name in snapshot):
        raise OperatorReceiptSnapshotCustodyError(
            f"{field} field names must be non-empty strings"
        )
    return snapshot


def snapshot_verification_inputs(
    receipt: Mapping[str, object],
    raw_result: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Return stable verification inputs and an explicit capability membrane."""

    receipt_snapshot = snapshot_json_mapping(receipt, field="operator receipt")
    raw_snapshot = (
        None
        if raw_result is None
        else snapshot_json_mapping(raw_result, field="raw machine evidence")
    )
    return {
        "schema": SCHEMA,
        "receipt": receipt_snapshot,
        "rawMachineEvidence": raw_snapshot,
        "oneObservationSnapshot": True,
        "authorityAdmitted": False,
        "ownerMutation": False,
        "regressionExecuted": False,
        "tested": False,
        "runtimeUi": False,
        "runtimeTalkBack": False,
        "deployed": False,
        "callable": False,
        "executed": False,
        "delivered": False,
        "accepted": False,
        "phoneP0MutationAuthority": False,
    }
