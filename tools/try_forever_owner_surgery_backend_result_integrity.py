#!/usr/bin/env python3
"""Source-only integrity gate for future owner-surgery backend results.

This organ does not replace ``admit_selected_backend_result`` and does not own promotion authority.
It closes supporting-source evidence gaps before the existing backend result-admission policy is
called:

1. every public result entrypoint first captures one bounded exact-JSON snapshot, so caller-owned
   Mapping/scalar subclasses cannot execute callbacks during integrity reads;
2. the result must identify the exact canonical owner-surgery custody schema it claims to preserve;
3. every admitted Surgery must carry canonical same-observation byte-count/SHA-256 evidence;
4. every promotion-group member must already exist as that exact Surgery evidence in the result's
   ``surgeries`` inventory, including content identity; and
5. ``artifactContentWitnesses`` must equal the canonical Surgery path/byte-count/SHA-256 set before
   the existing authority-admission policy may see the detached result.

Witness parity is part of this existing backend-result integrity owner. It is not a second backend
authority owner, and later descriptor-shadow agreement cannot repair a contradictory canonical
result after it has crossed this boundary. Snapshot custody is delegated to the existing operator
receipt exact-JSON organ; this module does not mint a neighboring validator.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from try_forever_operator_receipt_snapshot_custody import (
    OperatorReceiptSnapshotCustodyError,
    snapshot_json_mapping,
)
from try_forever_owner_surgery_backend_policy import (
    OWNER_AUTHORITY_FIELDS,
    OwnerSurgeryBackendSelection,
    admit_selected_backend_result,
)
from try_forever_owner_surgery_state_policy import admit_owner_surgery_state


CANONICAL_CUSTODY_SCHEMA = "try-forever-owner-surgery-custody.v10"
INVENTORY_INTEGRITY_SCHEMA = "try-forever-owner-surgery-backend-result-integrity.v1"
WITNESS_INTEGRITY_SCHEMA = "try-forever-owner-surgery-backend-result-witness-integrity.v1"
WITNESS_FIELD = "artifactContentWitnesses"
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class BackendWitnessParityError(ValueError):
    """Canonical Surgery content evidence and artifact witnesses disagree or are malformed."""


@dataclass(frozen=True)
class SurgeryIdentity:
    path: str
    artifact_kind: str
    owner: str
    base_blob: str
    state: str
    promotion_candidate: bool
    artifact_byte_count: int
    artifact_sha256: str


def _snapshot_backend_result(result: dict[str, object], *, context: str) -> dict[str, object]:
    """Detach one exact bounded JSON observation before any semantic result reads."""

    try:
        return snapshot_json_mapping(result, field=context)
    except OperatorReceiptSnapshotCustodyError as exc:
        raise ValueError(
            f"{context} must be one bounded exact JSON object before backend integrity reads"
        ) from exc


def _admit_surgery(record: object, *, context: str) -> SurgeryIdentity:
    if type(record) is not dict:
        raise ValueError(f"{context} must be one exact surgery object")

    path = record.get("path")
    if type(path) is not str or not path:
        raise ValueError(f"{context} path must be one non-empty string")

    artifact_kind = record.get("artifact_kind")
    if artifact_kind not in {"patch", "delta_json"}:
        raise ValueError(f"{context} artifact_kind is unsupported")
    expected_suffix = ".patch" if artifact_kind == "patch" else ".delta.json"
    if not path.endswith(expected_suffix):
        raise ValueError(
            f"{context} artifact_kind must agree with the exact artifact path suffix"
        )

    owner = record.get("owner")
    if type(owner) is not str or not owner:
        raise ValueError(f"{context} owner must be one non-empty string")

    base_blob = record.get("base_blob")
    if type(base_blob) is not str or SHA1_RE.fullmatch(base_blob) is None:
        raise ValueError(f"{context} base_blob must be 40 lowercase hexadecimal")

    state = record.get("state")
    if type(state) is not str or not state:
        raise ValueError(f"{context} state must be one non-empty string")
    try:
        state_admission = admit_owner_surgery_state(state)
    except ValueError as exc:
        raise ValueError(f"{context} state is not admitted") from exc

    promotion_candidate = record.get("promotion_candidate")
    if type(promotion_candidate) is not bool:
        raise ValueError(f"{context} promotion_candidate must be one boolean")
    if promotion_candidate != state_admission.promotion_candidate:
        raise ValueError(
            f"{context} promotion_candidate must agree with exact admitted surgery state"
        )

    artifact_byte_count = record.get("artifact_byte_count")
    if type(artifact_byte_count) is not int or artifact_byte_count < 0:
        raise ValueError(
            f"{context} artifact_byte_count must be one non-negative integer"
        )

    artifact_sha256 = record.get("artifact_sha256")
    if type(artifact_sha256) is not str or SHA256_RE.fullmatch(artifact_sha256) is None:
        raise ValueError(
            f"{context} artifact_sha256 must be 64 lowercase hexadecimal"
        )

    return SurgeryIdentity(
        path=path,
        artifact_kind=artifact_kind,
        owner=owner,
        base_blob=base_blob,
        state=state_admission.state,
        promotion_candidate=promotion_candidate,
        artifact_byte_count=artifact_byte_count,
        artifact_sha256=artifact_sha256,
    )


def _audit_backend_result_inventory_snapshot(result: dict[str, object]) -> dict[str, object]:
    """Audit one already-detached exact JSON result without revisiting caller-owned evidence."""

    schema = result.get("schema")
    if schema != CANONICAL_CUSTODY_SCHEMA:
        raise ValueError(
            "backend result schema must be exact canonical owner-surgery custody v10"
        )

    raw_surgeries = result.get("surgeries")
    if type(raw_surgeries) is not list:
        raise ValueError("surgeries must be one list")

    surgeries: list[SurgeryIdentity] = []
    by_path: dict[str, SurgeryIdentity] = {}
    exact_members: set[SurgeryIdentity] = set()
    for index, record in enumerate(raw_surgeries):
        admitted = _admit_surgery(record, context=f"surgeries[{index}]")
        if admitted.path in by_path:
            raise ValueError(
                "surgeries path identity must be unique across the admitted inventory"
            )
        by_path[admitted.path] = admitted
        surgeries.append(admitted)
        exact_members.add(admitted)

    group_member_count = 0
    for field in OWNER_AUTHORITY_FIELDS:
        groups = result.get(field)
        if type(groups) is not list:
            raise ValueError(f"{field} must be one list")
        for group_index, group in enumerate(groups):
            if type(group) is not dict:
                raise ValueError(f"{field}[{group_index}] must be one exact object")
            members = group.get("promotionCandidates")
            if type(members) is not list:
                raise ValueError(
                    f"{field}[{group_index}] promotionCandidates must be one list"
                )
            for member_index, member in enumerate(members):
                admitted_member = _admit_surgery(
                    member,
                    context=(
                        f"{field}[{group_index}].promotionCandidates[{member_index}]"
                    ),
                )
                if not admitted_member.promotion_candidate:
                    raise ValueError(
                        f"{field} promotion member must be promotion-ready"
                    )
                if admitted_member not in exact_members:
                    raise ValueError(
                        f"{field} promotion member must exist exactly in surgeries inventory"
                    )
                group_member_count += 1

    return {
        "schema": INVENTORY_INTEGRITY_SCHEMA,
        "canonicalCustodySchema": schema,
        "surgeriesAdmitted": len(surgeries),
        "authorityGroupMembersAdmitted": group_member_count,
        "phantomPromotionMembers": 0,
        "contentEvidenceDriftMembers": 0,
        "callerEvidenceSnapshotted": True,
        "authorityAdmitted": False,
        "ownerMutation": False,
        "regressionExecuted": False,
        "tested": False,
        "runtimeUi": False,
        "runtimeTalkBack": False,
        "phoneDelivered": False,
    }


def audit_backend_result_inventory(result: dict[str, object]) -> dict[str, object]:
    """Snapshot once, then validate schema custody and exact promotion-group membership."""

    snapshot = _snapshot_backend_result(result, context="backend result inventory")
    return _audit_backend_result_inventory_snapshot(snapshot)


def _canonical_surgery_content_map(
    result: dict[str, object],
) -> dict[str, tuple[int, str]]:
    """Project exact Surgery content evidence from an already-detached result."""

    surgeries = result.get("surgeries")
    if type(surgeries) is not list:
        raise BackendWitnessParityError("surgeries must be one list")

    expected: dict[str, tuple[int, str]] = {}
    for index, item in enumerate(surgeries):
        if type(item) is not dict:
            raise BackendWitnessParityError(f"surgeries[{index}] must be one exact object")
        path = item.get("path")
        byte_count = item.get("artifact_byte_count")
        sha256 = item.get("artifact_sha256")
        if type(path) is not str or not path:
            raise BackendWitnessParityError(
                f"surgeries[{index}].path must be one non-empty string"
            )
        if path in expected:
            raise BackendWitnessParityError(
                f"surgeries path identity must be unique: {path}"
            )
        if type(byte_count) is not int or byte_count < 0:
            raise BackendWitnessParityError(
                f"surgeries[{index}].artifact_byte_count must be one non-negative integer"
            )
        if type(sha256) is not str or SHA256_RE.fullmatch(sha256) is None:
            raise BackendWitnessParityError(
                f"surgeries[{index}].artifact_sha256 must be 64 lowercase hexadecimal"
            )
        expected[path] = (byte_count, sha256)
    return expected


def _artifact_witness_content_map(
    result: dict[str, object],
) -> dict[str, tuple[int, str]]:
    witnesses = result.get(WITNESS_FIELD)
    if type(witnesses) is not list:
        raise BackendWitnessParityError(f"{WITNESS_FIELD} must be one list")

    observed: dict[str, tuple[int, str]] = {}
    for index, item in enumerate(witnesses):
        if type(item) is not dict:
            raise BackendWitnessParityError(
                f"{WITNESS_FIELD}[{index}] must be one exact object"
            )
        path = item.get("path")
        byte_count = item.get("byteCount")
        sha256 = item.get("sha256")
        if type(path) is not str or not path:
            raise BackendWitnessParityError(
                f"{WITNESS_FIELD}[{index}].path must be one non-empty string"
            )
        if path in observed:
            raise BackendWitnessParityError(
                f"{WITNESS_FIELD} path identity must be unique: {path}"
            )
        if type(byte_count) is not int or byte_count < 0:
            raise BackendWitnessParityError(
                f"{WITNESS_FIELD}[{index}].byteCount must be one non-negative integer"
            )
        if type(sha256) is not str or SHA256_RE.fullmatch(sha256) is None:
            raise BackendWitnessParityError(
                f"{WITNESS_FIELD}[{index}].sha256 must be 64 lowercase hexadecimal"
            )
        observed[path] = (byte_count, sha256)
    return observed


def _audit_backend_result_witness_parity_snapshot(
    result: dict[str, object],
) -> dict[str, object]:
    """Require inventory + witness parity over one already-detached result."""

    integrity = _audit_backend_result_inventory_snapshot(result)
    expected = _canonical_surgery_content_map(result)
    observed = _artifact_witness_content_map(result)

    expected_paths = set(expected)
    observed_paths = set(observed)
    if expected_paths != observed_paths:
        missing = sorted(expected_paths - observed_paths)
        phantom = sorted(observed_paths - expected_paths)
        raise BackendWitnessParityError(
            f"{WITNESS_FIELD} path set must equal surgeries path set; "
            f"missing={missing!r} phantom={phantom!r}"
        )

    drifted = sorted(path for path in expected if expected[path] != observed[path])
    if drifted:
        raise BackendWitnessParityError(
            f"{WITNESS_FIELD} content identity must equal Surgery content evidence: {drifted!r}"
        )

    return {
        **integrity,
        "schema": WITNESS_INTEGRITY_SCHEMA,
        "inventoryIntegritySchema": integrity["schema"],
        "artifactContentWitnessesAdmitted": len(observed),
        "witnessParity": True,
        "witnessParityOwnerWired": True,
    }


def audit_backend_result_witness_parity(result: dict[str, object]) -> dict[str, object]:
    """Snapshot caller evidence once, then require exact Surgery↔artifact witness parity."""

    snapshot = _snapshot_backend_result(result, context="backend result witness parity")
    try:
        return _audit_backend_result_witness_parity_snapshot(snapshot)
    except BackendWitnessParityError:
        raise
    except ValueError as exc:
        raise BackendWitnessParityError(str(exc)) from exc


def admit_backend_result_with_inventory_custody(
    selection: OwnerSurgeryBackendSelection,
    result: dict[str, object],
) -> dict[str, object]:
    """Snapshot once, require integrity, then delegate detached evidence to existing authority policy."""

    snapshot = _snapshot_backend_result(result, context="backend result authority admission")
    integrity = _audit_backend_result_witness_parity_snapshot(snapshot)
    # The existing backend policy receives only our detached plain JSON tree. Its broader direct
    # public Mapping contract remains a separate supporting-source boundary; this composition no
    # longer exposes caller-owned Mapping callbacks to that policy.
    admitted = admit_selected_backend_result(selection, snapshot)
    return {
        **admitted,
        "integritySchema": integrity["schema"],
        "inventoryIntegritySchema": integrity["inventoryIntegritySchema"],
        "canonicalCustodySchema": integrity["canonicalCustodySchema"],
        "surgeriesAdmitted": integrity["surgeriesAdmitted"],
        "authorityGroupMembersAdmitted": integrity["authorityGroupMembersAdmitted"],
        "artifactContentWitnessesAdmitted": integrity["artifactContentWitnessesAdmitted"],
        "callerEvidenceSnapshotted": True,
        "witnessParity": True,
        "witnessParityOwnerWired": True,
        "phantomPromotionMembers": 0,
        "contentEvidenceDriftMembers": 0,
    }
