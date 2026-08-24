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
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from try_forever_owner_surgery_descriptor_shadow_audit import SCHEMA as RAW_SHADOW_SCHEMA
from try_forever_owner_surgery_shadow_receipt_self_integrity import (
    project_shadow_receipt_with_self_integrity,
)


SCHEMA = "try-forever-operator-receipt-derivation-custody.v1"


class OperatorReceiptDerivationError(ValueError):
    """The bounded receipt does not exactly derive from the supplied raw shadow evidence."""


def require_operator_receipt_projection_derivation(
    repo_root: Path,
    receipt: Mapping[str, object],
    raw_result: Mapping[str, object],
    *,
    allowed_extra_fields: tuple[str, ...] | None = None,
) -> dict[str, object]:
    """Recompute the existing bounded upstream projection and require exact field parity.

    By default this supporting gate owns only the upstream bounded projection fields returned by the
    existing self-integrity/projector chain. Final operator-owned fields may coexist in ``receipt``.
    When the final owner supplies ``allowed_extra_fields``, the complete receipt field namespace must
    equal ``derived projection fields + allowed final fields`` exactly. The final-owner allowlist must
    also be disjoint from derived projection fields so one namespace cannot claim ownership of the
    other's fields. This prevents a counterfeit from adding an undeclared field, re-signing the final
    receipt digest, and passing derivation as a mere subset check.
    """

    if not isinstance(receipt, Mapping):
        raise OperatorReceiptDerivationError("operator receipt must be one mapping")
    if not isinstance(raw_result, Mapping) or raw_result.get("schema") != RAW_SHADOW_SCHEMA:
        raise OperatorReceiptDerivationError(
            "derivation custody requires exact descriptor-shadow raw source schema"
        )

    expected = project_shadow_receipt_with_self_integrity(repo_root, raw_result)
    if not isinstance(expected, Mapping) or not expected:
        raise OperatorReceiptDerivationError(
            "existing self-integrity/projector chain must return one non-empty mapping"
        )
    if any(not isinstance(field, str) for field in expected):
        raise OperatorReceiptDerivationError("derived projection field names must be strings")
    if any(not isinstance(field, str) for field in receipt):
        raise OperatorReceiptDerivationError("operator receipt field names must be strings")

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
        if any(not isinstance(field, str) or not field for field in allowed_extra_fields):
            raise OperatorReceiptDerivationError(
                "allowed final receipt field names must be non-empty strings"
            )
        if len(set(allowed_extra_fields)) != len(allowed_extra_fields):
            raise OperatorReceiptDerivationError("allowed final receipt field names must be unique")

        overlap = sorted(set(expected) & set(allowed_extra_fields))
        if overlap:
            raise OperatorReceiptDerivationError(
                "derived and final-owner field namespaces must be disjoint: " + ", ".join(overlap)
            )

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
