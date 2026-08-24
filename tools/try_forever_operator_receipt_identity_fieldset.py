#!/usr/bin/env python3
"""Exact final-v4 field-set custody for receipt identity reverification.

The existing final receipt owner already closes the field namespace when it recomputes projection
derivation from supplied raw evidence. Identity-only and raw-linkage-only reverification are narrower
surfaces, however: a caller can otherwise add an undeclared field, recompute the deterministic final
digest, and retain a mathematically self-consistent receipt until the deeper derivation verifier runs.

This supporting organ owns only the exact current self-integrity receipt field vocabulary. It does not
create a second receipt owner/projector, does not derive values, and grants no authority, TESTED,
runtime, deployment, callability, execution, delivery, acceptance, phone, or P0 state.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping


SCHEMA = "try-forever-operator-receipt-identity-fieldset.v1"

# Exact fields emitted by the existing projector + self-integrity owner before the final v4 envelope
# adds its own metadata/capability closure. A focused regression binds this vocabulary to the real
# existing owner output so drift fails closed when regressions can execute.
SELF_INTEGRITY_RECEIPT_FIELDS = frozenset(
    {
        "schema",
        "sourceSchema",
        "status",
        "summary",
        "canonicalResultSha256",
        "boundarySha256",
        "portableArtifacts",
        "descriptorArtifacts",
        "artifactSetMatch",
        "metricsMatch",
        "contentIdentityMatch",
        "comparisonWork",
        "authorityAdmitted",
        "ownerMutation",
        "regressionExecuted",
        "tested",
        "runtimeUi",
        "runtimeTalkBack",
        "phoneDelivered",
        "receiptSelfIntegritySchema",
        "comparisonEvidenceRecomputed",
        "woundContextValidated",
        "temporalStatus",
        "temporalBindingProven",
        "temporalReceiptContextAdmitted",
    }
)


class OperatorReceiptIdentityFieldsetError(ValueError):
    """The final receipt field namespace is not the exact admitted v4 union."""


def _field_family(values: Iterable[str], *, field: str) -> frozenset[str]:
    items = tuple(values)
    if any(not isinstance(item, str) or not item for item in items):
        raise OperatorReceiptIdentityFieldsetError(
            f"{field} field names must be non-empty strings"
        )
    if len(set(items)) != len(items):
        raise OperatorReceiptIdentityFieldsetError(f"{field} field names must be unique")
    return frozenset(items)


def require_exact_final_receipt_fieldset(
    receipt: Mapping[str, object],
    *,
    operator_owned_fields: Iterable[str],
    denied_capability_fields: Iterable[str],
) -> dict[str, object]:
    """Require one final receipt to carry exactly the admitted v4 field namespace.

    Intentional exact-false capability reassertion is allowed because the contract is a set union,
    not a disjoint namespace. The final owner still owns value/capability semantics separately.
    """

    if not isinstance(receipt, Mapping):
        raise OperatorReceiptIdentityFieldsetError("operator receipt must be one mapping")
    actual_names = tuple(receipt.keys())
    if any(not isinstance(name, str) or not name for name in actual_names):
        raise OperatorReceiptIdentityFieldsetError(
            "operator receipt field names must be non-empty strings"
        )

    operator_fields = _field_family(operator_owned_fields, field="operator-owned")
    denied_fields = _field_family(denied_capability_fields, field="denied-capability")
    expected = SELF_INTEGRITY_RECEIPT_FIELDS | operator_fields | denied_fields
    actual = frozenset(actual_names)

    unexpected = sorted(actual - expected)
    missing = sorted(expected - actual)
    if unexpected:
        raise OperatorReceiptIdentityFieldsetError(
            "operator receipt carries undeclared final field(s): " + ", ".join(unexpected)
        )
    if missing:
        raise OperatorReceiptIdentityFieldsetError(
            "operator receipt is missing declared final field(s): " + ", ".join(missing)
        )

    return {
        "schema": SCHEMA,
        "finalFieldsetExact": True,
        "fieldCount": len(expected),
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
