#!/usr/bin/env python3
"""Source-only parity gate for canonical owner-surgery artifact content witnesses.

Canonical custody v10 emits two content-evidence surfaces for the same bounded artifact observation:

* each Surgery carries ``artifact_byte_count`` + ``artifact_sha256``; and
* ``artifactContentWitnesses`` carries ``path`` + ``byteCount`` + ``sha256``.

Those surfaces must agree exactly before a future backend/result composition may treat the witness
set as evidence. This helper grants no promotion authority, mutates no owner, executes no patch,
and does not replace the existing backend result-integrity/admission policies.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

from try_forever_owner_surgery_backend_result_integrity import (
    CANONICAL_CUSTODY_SCHEMA,
    audit_backend_result_inventory,
)


SCHEMA = "try-forever-owner-surgery-witness-parity.v1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
WITNESS_FIELD = "artifactContentWitnesses"


class CanonicalWitnessParityError(ValueError):
    """Canonical Surgery content evidence and artifact witnesses disagree or are malformed."""


def _nonnegative_int(value: object, *, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CanonicalWitnessParityError(f"{context} must be one non-negative integer")
    return value


def _sha256(value: object, *, context: str) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise CanonicalWitnessParityError(f"{context} must be 64 lowercase hexadecimal")
    return value


def _surgery_content_map(result: Mapping[str, object]) -> dict[str, tuple[int, str]]:
    surgeries = result.get("surgeries")
    # Shape/path/kind/state/member custody is established once by audit_backend_result_inventory
    # before this helper is called. Keep this function focused on the content identity projection.
    if not isinstance(surgeries, list):
        raise CanonicalWitnessParityError("surgeries must be one list")

    expected: dict[str, tuple[int, str]] = {}
    for index, item in enumerate(surgeries):
        if not isinstance(item, Mapping):
            raise CanonicalWitnessParityError(f"surgeries[{index}] must be one mapping")
        path = item.get("path")
        if not isinstance(path, str) or not path:
            raise CanonicalWitnessParityError(
                f"surgeries[{index}].path must be one non-empty string"
            )
        if path in expected:
            raise CanonicalWitnessParityError(
                f"surgeries path identity must be unique: {path}"
            )
        expected[path] = (
            _nonnegative_int(
                item.get("artifact_byte_count"),
                context=f"surgeries[{index}].artifact_byte_count",
            ),
            _sha256(
                item.get("artifact_sha256"),
                context=f"surgeries[{index}].artifact_sha256",
            ),
        )
    return expected


def _witness_content_map(result: Mapping[str, object]) -> dict[str, tuple[int, str]]:
    witnesses = result.get(WITNESS_FIELD)
    if not isinstance(witnesses, list):
        raise CanonicalWitnessParityError(f"{WITNESS_FIELD} must be one list")

    observed: dict[str, tuple[int, str]] = {}
    for index, item in enumerate(witnesses):
        if not isinstance(item, Mapping):
            raise CanonicalWitnessParityError(
                f"{WITNESS_FIELD}[{index}] must be one mapping"
            )
        path = item.get("path")
        if not isinstance(path, str) or not path:
            raise CanonicalWitnessParityError(
                f"{WITNESS_FIELD}[{index}].path must be one non-empty string"
            )
        if path in observed:
            raise CanonicalWitnessParityError(
                f"{WITNESS_FIELD} path identity must be unique: {path}"
            )
        observed[path] = (
            _nonnegative_int(
                item.get("byteCount"),
                context=f"{WITNESS_FIELD}[{index}].byteCount",
            ),
            _sha256(
                item.get("sha256"),
                context=f"{WITNESS_FIELD}[{index}].sha256",
            ),
        )
    return observed


def audit_canonical_witness_parity(result: Mapping[str, object]) -> dict[str, object]:
    """Require one exact witness for every canonical Surgery content identity.

    The existing inventory/group integrity audit runs exactly once here. A future integration may
    replace its direct call to ``audit_backend_result_inventory`` with this stronger superset and
    then delegate to the unchanged authority-admission policy; it does not need to audit twice.
    """

    if not isinstance(result, Mapping):
        raise CanonicalWitnessParityError("canonical result must be one mapping")
    if result.get("schema") != CANONICAL_CUSTODY_SCHEMA:
        raise CanonicalWitnessParityError(
            "witness parity requires exact canonical owner-surgery custody v10"
        )

    integrity = audit_backend_result_inventory(result)
    expected = _surgery_content_map(result)
    observed = _witness_content_map(result)

    expected_paths = set(expected)
    observed_paths = set(observed)
    if expected_paths != observed_paths:
        missing = sorted(expected_paths - observed_paths)
        phantom = sorted(observed_paths - expected_paths)
        raise CanonicalWitnessParityError(
            f"artifactContentWitnesses path set must equal surgeries path set; "
            f"missing={missing!r} phantom={phantom!r}"
        )

    drifted = sorted(path for path in expected if expected[path] != observed[path])
    if drifted:
        raise CanonicalWitnessParityError(
            f"artifactContentWitnesses content identity must equal Surgery content evidence: {drifted!r}"
        )

    return {
        "schema": SCHEMA,
        "canonicalCustodySchema": CANONICAL_CUSTODY_SCHEMA,
        "surgeriesAdmitted": integrity["surgeriesAdmitted"],
        "authorityGroupMembersAdmitted": integrity["authorityGroupMembersAdmitted"],
        "surgeryContentIdentities": len(expected),
        "artifactContentWitnesses": len(observed),
        "witnessParity": True,
        "authorityAdmitted": False,
        "ownerMutation": False,
        "regressionExecuted": False,
        "tested": False,
        "runtimeUi": False,
        "runtimeTalkBack": False,
        "phoneDelivered": False,
        "boundary": (
            "Canonical inventory/group custody plus Surgery↔artifactContentWitness parity are admitted "
            "as supporting evidence. Backend authority admission remains owned by the existing "
            "result-admission policy."
        ),
    }
