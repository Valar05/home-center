#!/usr/bin/env python3
"""Bounded operator receipt command for the existing descriptor-shadow organs.

This is a thin composition surface, not a second descriptor authority and not a second receipt
projector. ``audit_descriptor_shadow`` remains the raw machine-evidence producer. The operator path
always routes that raw result through the existing self-integrity gate, which in turn delegates to
the existing bounded display projector.

The repository root is one custody input, not merely a display hint: this command binds the raw
descriptor audit to ``repo_root / PATCH_ROOT`` and uses the same ``repo_root`` for bounded path
projection. Callers may tune bounded audit budgets/current-owner evidence through ``audit_kwargs``
but may not override ``root`` independently and create an audit-root/display-root split.

Raw machine evidence remains a separate callable source record. The operator receipt carries only a
deterministic SHA-256 binding to that exact raw payload; it does not embed the raw machine evidence
or raw boundary prose. ``operatorReceiptSha256`` identifies the complete bounded operator payload
emitted by this source command; neither digest is canonical artifact identity, promotion authority,
TESTED evidence, runtime identity, filesystem atomicity, phone delivery, or acceptance.

The final operator envelope closes the whole commissioned capability membrane explicitly. Core
bounded-receipt fields must already exist as exact false before finalization; later deployment/
callability/execution/delivery/acceptance fields remain additive upstream, but if present they must
already be exact false. The final command therefore never manufactures a false-looking receipt by
repairing a missing/positive core claim or overwriting a contradictory later claim.

Operator-owned receipt metadata is a separate namespace boundary. Upstream bounded projection must
not pre-populate the final command's receipt schema, raw-evidence linkage, architecture declarations,
phone/P0 authority declaration, or final receipt digest and then rely on final dictionary ordering
to overwrite the contradiction.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

from try_forever_owner_surgery_custody_probe import PATCH_ROOT
from try_forever_owner_surgery_descriptor_shadow_audit import audit_descriptor_shadow
from try_forever_owner_surgery_shadow_receipt_self_integrity import (
    project_shadow_receipt_with_self_integrity,
)
from try_forever_shadow_raw_capability_membrane import OPTIONAL_DENIED_FALSE_FIELDS


SCHEMA = "try-forever-owner-surgery-descriptor-shadow-operator-receipt.v4"
CORE_DENIED_CAPABILITY_FIELDS = (
    "authorityAdmitted",
    "ownerMutation",
    "regressionExecuted",
    "tested",
    "runtimeUi",
    "runtimeTalkBack",
    "phoneDelivered",
)
FINAL_DENIED_CAPABILITY_FIELDS = (
    *CORE_DENIED_CAPABILITY_FIELDS,
    *OPTIONAL_DENIED_FALSE_FIELDS,
)
OPERATOR_OWNED_RECEIPT_FIELDS = (
    "operatorReceiptSchema",
    "rawMachineEvidenceRemainsSeparate",
    "rawMachineEvidenceIncluded",
    "rawMachineEvidenceBound",
    "rawMachineEvidenceSha256",
    "secondReceiptProjectorCreated",
    "secondDescriptorAuthorityCreated",
    "phoneP0MutationAuthority",
    "operatorReceiptSha256",
)


def _deterministic_json_sha256(payload: Mapping[str, object], *, ensure_ascii: bool) -> str:
    """Hash one JSON-shaped source payload without changing or promoting its semantics."""

    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=ensure_ascii,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _raw_machine_evidence_sha256(raw_result: Mapping[str, object]) -> str:
    """Bind the operator receipt to exact raw shadow evidence without embedding raw evidence.

    ``ensure_ascii=True`` keeps the digest operation deterministic even if a hostile filesystem/error
    boundary contains an unpaired surrogate. The digest is evidence linkage only.
    """

    if not isinstance(raw_result, Mapping):
        raise ValueError("raw descriptor-shadow evidence must be one mapping")
    return _deterministic_json_sha256(raw_result, ensure_ascii=True)


def _operator_receipt_sha256(payload: Mapping[str, object]) -> str:
    """Return deterministic identity for the bounded operator payload, excluding its own digest."""

    return _deterministic_json_sha256(payload, ensure_ascii=False)


def _require_final_capability_closure(receipt: Mapping[str, object]) -> None:
    """Reject missing/contradictory capability state and final-command namespace collisions."""

    for field in OPERATOR_OWNED_RECEIPT_FIELDS:
        if field in receipt:
            raise ValueError(
                f"bounded descriptor-shadow receipt cannot pre-populate operator-owned field {field}"
            )

    for field in CORE_DENIED_CAPABILITY_FIELDS:
        if field not in receipt:
            raise ValueError(
                f"bounded descriptor-shadow receipt must carry explicit upstream {field}=false"
            )
        if receipt.get(field) is not False:
            raise ValueError(
                f"bounded descriptor-shadow receipt cannot sanitize upstream {field} capability"
            )

    for field in OPTIONAL_DENIED_FALSE_FIELDS:
        if field in receipt and receipt.get(field) is not False:
            raise ValueError(
                f"bounded descriptor-shadow receipt cannot sanitize upstream {field} capability"
            )


def build_descriptor_shadow_operator_receipt(
    repo_root: Path = Path("."),
    **audit_kwargs,
) -> dict[str, object]:
    """Produce one self-audited operator receipt from the existing raw shadow owner.

    ``repo_root`` owns both the raw audit root and the display-projection root. Accepting a second
    caller-supplied ``root`` would allow machine evidence from one repository/path tree to be
    projected as though it came from another, so that split fails closed.
    """

    if "root" in audit_kwargs:
        raise ValueError("descriptor-shadow operator receipt root is owned by repo_root")

    audit_root = repo_root / PATCH_ROOT
    raw_result = audit_descriptor_shadow(root=audit_root, **audit_kwargs)
    raw_machine_evidence_sha256 = _raw_machine_evidence_sha256(raw_result)
    receipt = project_shadow_receipt_with_self_integrity(repo_root, raw_result)
    _require_final_capability_closure(receipt)
    payload: dict[str, object] = {
        **receipt,
        "operatorReceiptSchema": SCHEMA,
        "rawMachineEvidenceRemainsSeparate": True,
        "rawMachineEvidenceIncluded": False,
        "rawMachineEvidenceBound": True,
        "rawMachineEvidenceSha256": raw_machine_evidence_sha256,
        "secondReceiptProjectorCreated": False,
        "secondDescriptorAuthorityCreated": False,
        "phoneP0MutationAuthority": False,
        **{field: False for field in FINAL_DENIED_CAPABILITY_FIELDS},
    }
    return {
        **payload,
        "operatorReceiptSha256": _operator_receipt_sha256(payload),
    }


if __name__ == "__main__":
    print(json.dumps(build_descriptor_shadow_operator_receipt(), indent=2, sort_keys=True))
