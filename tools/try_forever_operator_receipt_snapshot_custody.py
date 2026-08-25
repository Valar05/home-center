#!/usr/bin/env python3
"""One-observation bounded JSON snapshot custody for operator receipt verification.

Verification code must not validate one view of a stateful ``Mapping`` and later hash/derive from a
second view of that same object. It also must not let caller-owned evidence consume unbounded memory
or change identity because Python's JSON encoder helpfully normalizes a non-JSON shape.

This organ therefore performs one bounded recursive observation into plain ``dict``/``list`` JSON
values. Every mapping level requires non-empty string keys; tuples, non-string keys, non-finite
numbers, cycles/over-depth trees, and resource-over-budget evidence fail closed before later receipt
verification. Integer evidence also has a pre-serialization magnitude throat, so one otherwise-valid
JSON scalar cannot force disproportionate decimal conversion work before the encoded-byte ceiling is
checked. A final deterministic JSON serialization checks the detached observation against an encoded-
byte ceiling without re-reading caller-owned objects.

The snapshot is evidence custody only. It creates no receipt owner/projector, grants no authority,
TESTED/runtime/deployment/callability/execution/delivery/acceptance state, and has no phone/P0
mutation authority.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping


SCHEMA = "try-forever-operator-receipt-snapshot-custody.v2"
MAX_SNAPSHOT_DEPTH = 64
MAX_SNAPSHOT_NODES = 50_000
MAX_SNAPSHOT_STRING_CODEPOINTS = 1_048_576
MAX_SNAPSHOT_ENCODED_BYTES = 8 * 1024 * 1024
# 14,284 binary bits are sufficient for at most 4,300 decimal digits. This mirrors CPython's
# default large-int string-conversion safety order of magnitude without relying on process-global
# ``sys.set_int_max_str_digits`` state, and keeps the bound enforceable before decimal serialization.
MAX_SNAPSHOT_INTEGER_BITS = 14_284


class OperatorReceiptSnapshotCustodyError(ValueError):
    """A verification input could not be captured as one bounded exact JSON-shaped mapping."""


class _SnapshotBudget:
    def __init__(self) -> None:
        self.nodes = 0
        self.string_codepoints = 0

    def consume_node(self, *, field: str) -> None:
        self.nodes += 1
        if self.nodes > MAX_SNAPSHOT_NODES:
            raise OperatorReceiptSnapshotCustodyError(
                f"{field} exceeds snapshot node budget {MAX_SNAPSHOT_NODES}"
            )

    def consume_text(self, value: str, *, field: str) -> None:
        self.string_codepoints += len(value)
        if self.string_codepoints > MAX_SNAPSHOT_STRING_CODEPOINTS:
            raise OperatorReceiptSnapshotCustodyError(
                f"{field} exceeds snapshot text budget {MAX_SNAPSHOT_STRING_CODEPOINTS} code points"
            )


def _snapshot_json_value(
    value: object,
    *,
    field: str,
    depth: int,
    budget: _SnapshotBudget,
) -> object:
    if depth > MAX_SNAPSHOT_DEPTH:
        raise OperatorReceiptSnapshotCustodyError(
            f"{field} exceeds snapshot depth budget {MAX_SNAPSHOT_DEPTH}"
        )

    budget.consume_node(field=field)

    if value is None or type(value) is bool:
        return value

    if type(value) is int:
        if value.bit_length() > MAX_SNAPSHOT_INTEGER_BITS:
            raise OperatorReceiptSnapshotCustodyError(
                f"{field} exceeds snapshot integer-magnitude budget {MAX_SNAPSHOT_INTEGER_BITS} bits"
            )
        return value

    if type(value) is float:
        if not math.isfinite(value):
            raise OperatorReceiptSnapshotCustodyError(
                f"{field} must contain only finite JSON numbers"
            )
        return value

    if type(value) is str:
        budget.consume_text(value, field=field)
        return value

    if type(value) is list:
        return [
            _snapshot_json_value(
                item,
                field=f"{field}[{index}]",
                depth=depth + 1,
                budget=budget,
            )
            for index, item in enumerate(value)
        ]

    if isinstance(value, Mapping):
        snapshot: dict[str, object] = {}
        for key, item in value.items():
            if type(key) is not str or not key:
                raise OperatorReceiptSnapshotCustodyError(
                    f"{field} field names must be non-empty strings"
                )
            budget.consume_text(key, field=field)
            if key in snapshot:
                raise OperatorReceiptSnapshotCustodyError(
                    f"{field} contains duplicate mapping field {key!r}"
                )
            snapshot[key] = _snapshot_json_value(
                item,
                field=f"{field}.{key}",
                depth=depth + 1,
                budget=budget,
            )
        return snapshot

    # ``json.dumps`` accepts tuples and may stringify non-string mapping keys. Both are identity
    # normalization, not exact JSON evidence, so reject them before the serializer can repair them.
    raise OperatorReceiptSnapshotCustodyError(
        f"{field} must contain only exact JSON null/boolean/number/string/list/object values"
    )


def snapshot_json_mapping(value: Mapping[str, object], *, field: str) -> dict[str, object]:
    """Capture one stable bounded plain-dict observation of an exact JSON-shaped mapping.

    Caller-owned mappings and nested structures are read exactly once by this function. The returned
    tree contains only plain dict/list containers and JSON scalars. The deterministic serialization
    below reads only that detached tree; it never revisits the caller-owned mapping.
    """

    if not isinstance(value, Mapping):
        raise OperatorReceiptSnapshotCustodyError(f"{field} must be one mapping")

    budget = _SnapshotBudget()
    try:
        snapshot = _snapshot_json_value(value, field=field, depth=0, budget=budget)
    except OperatorReceiptSnapshotCustodyError:
        raise
    except Exception as exc:
        raise OperatorReceiptSnapshotCustodyError(
            f"{field} could not be observed as one stable JSON-shaped mapping"
        ) from exc

    if type(snapshot) is not dict:
        raise OperatorReceiptSnapshotCustodyError(f"{field} snapshot must remain one object")

    try:
        encoded = json.dumps(
            snapshot,
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
        )
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise OperatorReceiptSnapshotCustodyError(
            f"{field} must be one finite JSON-shaped mapping"
        ) from exc

    if len(encoded) > MAX_SNAPSHOT_ENCODED_BYTES:
        raise OperatorReceiptSnapshotCustodyError(
            f"{field} exceeds snapshot encoded-byte budget {MAX_SNAPSHOT_ENCODED_BYTES}"
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
        "boundedSnapshot": True,
        "exactJsonShape": True,
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
