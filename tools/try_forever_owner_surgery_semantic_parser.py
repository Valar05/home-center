#!/usr/bin/env python3
"""Pure semantic producer for already-custodied TRY FOREVER owner-surgery bytes.

This module turns one exact, already-observed UTF-8 artifact plus its byte/SHA witness into the same
semantic fields used by canonical ``Surgery`` records. It performs no filesystem lookup, root
selection, backend selection, authority grouping, patch application, overlay mutation, phone work,
or P0 work.

Canonical v10 now consumes this producer after its own bounded artifact observation for both patch
and delta semantics. That is SOURCE_WIRED composition only: regression execution, TESTED, descriptor
backend composition, runtime, deployment, delivery, and acceptance remain separate capability
states.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass

from try_forever_owner_surgery_default_owner_binding import (
    DEFAULT_OWNER,
    admit_default_owner_from_patch,
)
from try_forever_owner_surgery_metadata_exactness import (
    admit_owner_identity,
    admit_patch_metadata,
)
from try_forever_owner_surgery_state_policy import admit_owner_surgery_state


SCHEMA = "try-forever-owner-surgery-semantic-parser.v1"
DELTA_SCHEMA = "try-forever-owner-delta.v1"
DELTA_BASE_KEYS = ("baseBlob", "ownerBaseBlob", "baseOwnerBlob")
DELTA_STATE_KEYS = ("state", "status")
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class OwnerSurgerySemanticError(ValueError):
    """Already-custodied bytes cannot produce one exact owner-surgery semantic record."""


@dataclass(frozen=True)
class OwnerSurgerySemanticRecord:
    path: str
    artifact_kind: str
    owner: str
    base_blob: str
    state: str
    promotion_candidate: bool
    artifact_byte_count: int
    artifact_sha256: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _reject_duplicate_json_members(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise OwnerSurgerySemanticError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def _consistent_delta_string(
    payload: dict[str, object],
    keys: tuple[str, ...],
    field_name: str,
) -> str:
    present = [(key, payload[key]) for key in keys if key in payload]
    if not present:
        raise OwnerSurgerySemanticError(f"missing {field_name}")

    values: list[str] = []
    for key, raw in present:
        if type(raw) is not str or not raw:
            raise OwnerSurgerySemanticError(f"{key} must be one non-empty exact built-in string")
        values.append(raw)
    if len(set(values)) != 1:
        raise OwnerSurgerySemanticError(f"conflicting {field_name} aliases")
    return values[0]


def _admit_exact_observation(
    *,
    path: str,
    artifact_kind: str,
    utf8_text: str,
    byte_count: int,
    sha256: str,
) -> bytes:
    """Bind semantic parsing to one exact already-observed text/content witness."""

    if type(path) is not str or not path:
        raise OwnerSurgerySemanticError("path must be one non-empty exact built-in string")
    if type(artifact_kind) is not str or artifact_kind not in {"patch", "delta_json"}:
        raise OwnerSurgerySemanticError("artifact_kind must be exact 'patch' or 'delta_json'")
    if type(utf8_text) is not str:
        raise OwnerSurgerySemanticError("utf8_text must be one exact built-in string")
    if type(byte_count) is not int or byte_count < 0:
        raise OwnerSurgerySemanticError("byte_count must be one non-negative exact built-in integer")
    if type(sha256) is not str or SHA256_RE.fullmatch(sha256) is None:
        raise OwnerSurgerySemanticError("sha256 must be one exact lowercase SHA-256 string")

    try:
        encoded = utf8_text.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise OwnerSurgerySemanticError(
            f"utf8_text is not strict UTF-8 encodable at code point index {exc.start}"
        ) from exc
    if len(encoded) != byte_count:
        raise OwnerSurgerySemanticError("byte_count does not match the admitted UTF-8 content")
    if hashlib.sha256(encoded).hexdigest() != sha256:
        raise OwnerSurgerySemanticError("sha256 does not match the admitted UTF-8 content")
    return encoded


def _parse_patch(
    *,
    path: str,
    text: str,
    byte_count: int,
    sha256: str,
) -> OwnerSurgerySemanticRecord:
    metadata = admit_patch_metadata(text)
    owner = (
        metadata.explicit_owner
        if metadata.explicit_owner is not None
        else admit_default_owner_from_patch(text, default_owner=DEFAULT_OWNER).owner
    )
    return OwnerSurgerySemanticRecord(
        path=path,
        artifact_kind="patch",
        owner=owner,
        base_blob=metadata.base_blob,
        state=metadata.state,
        promotion_candidate=metadata.promotion_candidate,
        artifact_byte_count=byte_count,
        artifact_sha256=sha256,
    )


def _parse_delta(
    *,
    path: str,
    text: str,
    byte_count: int,
    sha256: str,
) -> OwnerSurgerySemanticRecord:
    try:
        payload = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_json_members,
            parse_constant=lambda value: (_ for _ in ()).throw(
                OwnerSurgerySemanticError(f"non-standard JSON constant: {value}")
            ),
        )
    except json.JSONDecodeError as exc:
        raise OwnerSurgerySemanticError(f"malformed owner delta JSON: {exc.msg}") from exc

    if type(payload) is not dict:
        raise OwnerSurgerySemanticError("owner delta root must be one exact JSON object")
    if payload.get("schema") != DELTA_SCHEMA:
        raise OwnerSurgerySemanticError(f"unsupported owner delta schema: {payload.get('schema')!r}")

    owner = admit_owner_identity(payload.get("owner"), field="delta owner")
    base_blob = _consistent_delta_string(payload, DELTA_BASE_KEYS, "base owner blob")
    if SHA1_RE.fullmatch(base_blob) is None:
        raise OwnerSurgerySemanticError(
            "base owner blob must be 40 lowercase hexadecimal characters"
        )
    state_admission = admit_owner_surgery_state(
        _consistent_delta_string(payload, DELTA_STATE_KEYS, "state/status")
    )

    return OwnerSurgerySemanticRecord(
        path=path,
        artifact_kind="delta_json",
        owner=owner,
        base_blob=base_blob,
        state=state_admission.state,
        promotion_candidate=state_admission.promotion_candidate,
        artifact_byte_count=byte_count,
        artifact_sha256=sha256,
    )


def parse_owner_surgery_observation(
    *,
    path: str,
    artifact_kind: str,
    utf8_text: str,
    byte_count: int,
    sha256: str,
) -> OwnerSurgerySemanticRecord:
    """Produce semantics from one exact observation without any filesystem re-read."""

    _admit_exact_observation(
        path=path,
        artifact_kind=artifact_kind,
        utf8_text=utf8_text,
        byte_count=byte_count,
        sha256=sha256,
    )
    try:
        if artifact_kind == "patch":
            return _parse_patch(
                path=path,
                text=utf8_text,
                byte_count=byte_count,
                sha256=sha256,
            )
        return _parse_delta(
            path=path,
            text=utf8_text,
            byte_count=byte_count,
            sha256=sha256,
        )
    except OwnerSurgerySemanticError:
        raise
    except (UnicodeError, ValueError) as exc:
        raise OwnerSurgerySemanticError(f"semantic admission failed: {type(exc).__name__}: {exc}") from exc


def source_receipt() -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "filesystemReads": False,
        "exactBuiltinObservationInputs": True,
        "contentWitnessRecomputedBeforeSemantics": True,
        "strictUtf8EncodeFailureTyped": True,
        "patchSemanticProduction": True,
        "deltaSemanticProduction": True,
        "canonicalOwnerConsumption": True,
        "descriptorBackendConsumption": False,
        "regressionExecuted": False,
        "tested": False,
        "runtimeUi": False,
        "runtimeTalkBack": False,
        "deployed": False,
        "callable": False,
        "executed": False,
        "delivered": False,
        "accepted": False,
        "phoneDelivered": False,
    }
