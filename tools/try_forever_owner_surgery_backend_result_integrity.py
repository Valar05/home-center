#!/usr/bin/env python3
"""Source-only integrity gate for future owner-surgery backend results.

This organ does not replace ``admit_selected_backend_result`` and does not own promotion authority.
It closes two supporting-source evidence gaps before the existing backend result-admission policy is
called:

1. the result must identify the exact canonical owner-surgery custody schema it claims to preserve;
2. every promotion-group member must already exist as exact admitted surgery evidence in the
   result's ``surgeries`` inventory.

A group may not mint a phantom surgery merely because its member mapping looks plausible. Exact
schema + exact surgery inventory are custody prerequisites, not TESTED/runtime/deployment proof.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from try_forever_owner_surgery_backend_policy import (
    OWNER_AUTHORITY_FIELDS,
    OwnerSurgeryBackendSelection,
    admit_selected_backend_result,
)
from try_forever_owner_surgery_state_policy import admit_owner_surgery_state


CANONICAL_CUSTODY_SCHEMA = "try-forever-owner-surgery-custody.v10"
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class SurgeryIdentity:
    path: str
    artifact_kind: str
    owner: str
    base_blob: str
    state: str
    promotion_candidate: bool


def _admit_surgery(record: object, *, context: str) -> SurgeryIdentity:
    if not isinstance(record, Mapping):
        raise ValueError(f"{context} must be one surgery mapping")

    path = record.get("path")
    if not isinstance(path, str) or not path:
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
    if not isinstance(owner, str) or not owner:
        raise ValueError(f"{context} owner must be one non-empty string")

    base_blob = record.get("base_blob")
    if not isinstance(base_blob, str) or SHA1_RE.fullmatch(base_blob) is None:
        raise ValueError(f"{context} base_blob must be 40 lowercase hexadecimal")

    state = record.get("state")
    if not isinstance(state, str) or not state:
        raise ValueError(f"{context} state must be one non-empty string")
    try:
        state_admission = admit_owner_surgery_state(state)
    except ValueError as exc:
        raise ValueError(f"{context} state is not admitted") from exc

    promotion_candidate = record.get("promotion_candidate")
    if not isinstance(promotion_candidate, bool):
        raise ValueError(f"{context} promotion_candidate must be one boolean")
    if promotion_candidate != state_admission.promotion_candidate:
        raise ValueError(
            f"{context} promotion_candidate must agree with exact admitted surgery state"
        )

    return SurgeryIdentity(
        path=path,
        artifact_kind=artifact_kind,
        owner=owner,
        base_blob=base_blob,
        state=state_admission.state,
        promotion_candidate=promotion_candidate,
    )


def audit_backend_result_inventory(result: Mapping[str, object]) -> dict[str, object]:
    """Validate schema custody and promotion-group membership without granting authority."""

    if not isinstance(result, Mapping):
        raise ValueError("backend result must be one mapping")

    schema = result.get("schema")
    if schema != CANONICAL_CUSTODY_SCHEMA:
        raise ValueError(
            "backend result schema must be exact canonical owner-surgery custody v10"
        )

    raw_surgeries = result.get("surgeries")
    if not isinstance(raw_surgeries, list):
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
        if not isinstance(groups, list):
            raise ValueError(f"{field} must be one list")
        for group_index, group in enumerate(groups):
            if not isinstance(group, Mapping):
                raise ValueError(f"{field}[{group_index}] must be one mapping")
            members = group.get("promotionCandidates")
            if not isinstance(members, list):
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
        "schema": "try-forever-owner-surgery-backend-result-integrity.v1",
        "canonicalCustodySchema": schema,
        "surgeriesAdmitted": len(surgeries),
        "authorityGroupMembersAdmitted": group_member_count,
        "phantomPromotionMembers": 0,
        "authorityAdmitted": False,
        "ownerMutation": False,
        "regressionExecuted": False,
        "tested": False,
        "runtimeUi": False,
        "runtimeTalkBack": False,
        "phoneDelivered": False,
    }


def admit_backend_result_with_inventory_custody(
    selection: OwnerSurgeryBackendSelection,
    result: Mapping[str, object],
) -> dict[str, object]:
    """Audit inventory custody, then delegate authority admission to the existing policy."""

    integrity = audit_backend_result_inventory(result)
    admitted = admit_selected_backend_result(selection, result)
    return {
        **admitted,
        "integritySchema": integrity["schema"],
        "canonicalCustodySchema": integrity["canonicalCustodySchema"],
        "surgeriesAdmitted": integrity["surgeriesAdmitted"],
        "authorityGroupMembersAdmitted": integrity["authorityGroupMembersAdmitted"],
        "phantomPromotionMembers": 0,
    }
