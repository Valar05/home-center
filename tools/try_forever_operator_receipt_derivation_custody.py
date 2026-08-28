#!/usr/bin/env python3
"""Supporting derivation-custody gate for bounded descriptor-shadow operator receipts.

This module does not create a second receipt owner, projector, or descriptor authority. It reuses the
existing self-integrity/projector chain to answer one narrower question that digest linkage alone
cannot answer: did the bounded upstream receipt fields actually derive from this supplied raw
machine-evidence mapping?

Raw machine evidence remains separate. Final operator-envelope identity, raw-evidence SHA linkage,
capability closure, deployment, runtime, phone delivery, and acceptance remain owned elsewhere.
When the final owner supplies ``allowed_extra_fields``, this gate also closes the field namespace:
exact derivation is then exact fields, not merely an expected-field subset inside a re-signed envelope.

Caller-owned receipt/raw mappings cross the already-owned one-observation exact-JSON snapshot throat
before this module reads schema, fields, or nested evidence. The public contract therefore advertises
exact built-in ``dict`` inputs rather than arbitrary ``Mapping`` capability. Final-field vocabulary is
likewise admitted as one exact tuple before iteration. These are evidence-custody gates, not authority
or TESTED/runtime promotion.
"""

from __future__ import annotations

from pathlib import Path

from try_forever_operator_receipt_snapshot_custody import (
    OperatorReceiptSnapshotCustodyError,
    snapshot_json_mapping,
)
from try_forever_owner_surgery_descriptor_shadow_audit import SCHEMA as RAW_SHADOW_SCHEMA
from try_forever_owner_surgery_shadow_receipt_self_integrity import (
    project_shadow_receipt_with_self_integrity,
)


SCHEMA = "try-forever-operator-receipt-derivation-custody.v1"


class OperatorReceiptDerivationError(ValueError):
    """The bounded receipt does not exactly derive from the supplied raw shadow evidence."""


def require_operator_receipt_projection_derivation(
    repo_root: Path,
    receipt: dict[str, object],
    raw_result: dict[str, object],
    *,
    allowed_extra_fields: tuple[str, ...] | None = None,
) -> dict[str, object]:
    """Recompute the existing bounded upstream projection and require exact field parity.

    By default this supporting gate owns only the upstream bounded projection fields returned by the
    existing self-integrity/projector chain. Final operator-owned fields may coexist in ``receipt``.
    When the final owner supplies ``allowed_extra_fields``, the complete receipt field namespace must
    equal ``derived projection fields + allowed final fields`` exactly. An allowed final field may
    intentionally reassert a field already derived upstream (for example, an exact-false capability
    membrane); upstream derivation still owns value parity, while the final envelope separately owns
    its final capability contract. This prevents an undeclared field from being added, re-signed, and
    accepted merely because every expected projector field still appears as a subset.

    ``receipt`` and ``raw_result`` are snapshotted before any semantic read. Arbitrary Mapping or dict
    subclass callbacks are not an admitted part of this public evidence contract.
    """

    try:
        receipt = snapshot_json_mapping(receipt, field="operator receipt derivation input")
        raw_result = snapshot_json_mapping(raw_result, field="raw derivation evidence")
    except OperatorReceiptSnapshotCustodyError as exc:
        raise OperatorReceiptDerivationError(
            "derivation custody requires bounded exact built-in-dict evidence"
        ) from exc

    if raw_result.get("schema") != RAW_SHADOW_SCHEMA:
        raise OperatorReceiptDerivationError(
            "derivation custody requires exact descriptor-shadow raw source schema"
        )

    expected = project_shadow_receipt_with_self_integrity(repo_root, raw_result)
    if type(expected) is not dict or not expected:
        raise OperatorReceiptDerivationError(
            "existing self-integrity/projector chain must return one non-empty exact dict"
        )
    if any(type(field) is not str for field in expected):
        raise OperatorReceiptDerivationError("derived projection field names must be exact strings")
    if any(type(field) is not str for field in receipt):
        raise OperatorReceiptDerivationError("operator receipt field names must be exact strings")

    for field, expected_value in expected.items():
        if field not in receipt:
            raise OperatorReceiptDerivationError(
                f"operator receipt is missing derived upstream field {field}"
            )
        if receipt.get(field) != expected_value:
            raise OperatorReceiptDerivationError(
                f"operator receipt upstream field {field} does not derive from supplied raw evidence"
            )

    fieldset_closed = allowed_extra_fields is not None
    if fieldset_closed:
        if type(allowed_extra_fields) is not tuple:
            raise OperatorReceiptDerivationError(
                "allowed final receipt fields must be one exact tuple"
            )
        if any(type(field) is not str or not field for field in allowed_extra_fields):
            raise OperatorReceiptDerivationError(
                "allowed final receipt field names must be non-empty exact strings"
            )
        if len(set(allowed_extra_fields)) != len(allowed_extra_fields):
            raise OperatorReceiptDerivationError("allowed final receipt field names must be unique")

        allowed_fields = set(expected) | set(allowed_extra_fields)
        actual_fields = set(receipt)
        unexpected = sorted(actual_fields - allowed_fields)
        missing = sorted(allowed_fields - actual_fields)
        if unexpected:
            raise OperatorReceiptDerivationError(
                "operator receipt carries undeclared field(s): " + ", ".join(unexpected)
            )
        if missing:
            raise OperatorReceiptDerivationError(
                "operator receipt is missing declared field(s): " + ", ".join(missing)
            )

    return {
        "schema": SCHEMA,
        "projectionFieldsVerified": len(expected),
        "projectionDerivedFromRaw": True,
        "receiptFieldsetClosed": fieldset_closed,
        "rawMachineEvidenceEmbedded": False,
        "secondReceiptProjectorCreated": False,
        "secondDescriptorAuthorityCreated": False,
        "authorityAdmitted": False,
        "ownerMutation": False,
        "regressionExecuted": False,
        "tested": False,
        "runtimeUi": False,
        "runtimeTalkBack": False,
        "phoneDelivered": False,
        "deployed": False,
        "callable": False,
        "executed": False,
        "delivered": False,
        "accepted": False,
    }
