#!/usr/bin/env python3
"""Bounded operator receipt command for the existing descriptor-shadow organs.

This is a thin composition surface, not a second descriptor authority and not a second receipt
projector. ``audit_descriptor_shadow`` remains the raw machine-evidence producer. The operator path
always routes that raw result through the existing self-integrity gate, which in turn delegates to
the existing bounded display projector.

Raw machine evidence remains a separate callable source record. The operator receipt carries only a
deterministic SHA-256 binding to that exact raw payload; it does not embed the raw machine evidence
or raw boundary prose. ``operatorReceiptSha256`` identifies the complete bounded operator payload
emitted by this source command; neither digest is canonical artifact identity, promotion authority,
TESTED evidence, runtime identity, filesystem atomicity, phone delivery, or acceptance.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

from try_forever_owner_surgery_descriptor_shadow_audit import audit_descriptor_shadow
from try_forever_owner_surgery_shadow_receipt_self_integrity import (
    project_shadow_receipt_with_self_integrity,
)


SCHEMA = "try-forever-owner-surgery-descriptor-shadow-operator-receipt.v3"


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


def build_descriptor_shadow_operator_receipt(
    repo_root: Path = Path("."),
    **audit_kwargs,
) -> dict[str, object]:
    """Produce one self-audited operator receipt from the existing raw shadow owner."""

    raw_result = audit_descriptor_shadow(**audit_kwargs)
    raw_machine_evidence_sha256 = _raw_machine_evidence_sha256(raw_result)
    receipt = project_shadow_receipt_with_self_integrity(repo_root, raw_result)
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
    }
    return {
        **payload,
        "operatorReceiptSha256": _operator_receipt_sha256(payload),
    }


if __name__ == "__main__":
    print(json.dumps(build_descriptor_shadow_operator_receipt(), indent=2, sort_keys=True))
