#!/usr/bin/env python3
"""SOURCE-ONLY regression for exact-observation owner-surgery semantic production.

The fixture is intentionally not execution evidence. It pins patch/delta semantic parity, content-
witness binding, duplicate-member rejection, callback-free exact scalar admission, bounded direct
semantic work, and typed strict-UTF-8 failure for the producer consumed by canonical portable and
descriptor custody paths.
"""

import hashlib
import json

from try_forever_owner_surgery_default_owner_binding import DEFAULT_OWNER
from try_forever_owner_surgery_semantic_parser import (
    MAX_SEMANTIC_OBSERVATION_BYTES,
    OwnerSurgerySemanticError,
    parse_owner_surgery_observation,
    source_receipt,
)


BASE = "0123456789abcdef0123456789abcdef01234567"


class CallbackString(str):
    callbacks = 0

    def __str__(self) -> str:
        type(self).callbacks += 1
        return super().__str__()

    def __eq__(self, other: object) -> bool:
        type(self).callbacks += 1
        return super().__eq__(other)

    def __hash__(self) -> int:
        type(self).callbacks += 1
        return super().__hash__()

    def encode(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        type(self).callbacks += 1
        return super().encode(*args, **kwargs)


def _witness(text: str) -> tuple[int, str]:
    raw = text.encode("utf-8")
    return len(raw), hashlib.sha256(raw).hexdigest()


def _parse(*, path: object, kind: object, text: object, byte_count: object, sha256: object):
    return parse_owner_surgery_observation(
        path=path,  # type: ignore[arg-type]
        artifact_kind=kind,  # type: ignore[arg-type]
        utf8_text=text,  # type: ignore[arg-type]
        byte_count=byte_count,  # type: ignore[arg-type]
        sha256=sha256,  # type: ignore[arg-type]
    )


def _must_reject_without_callbacks(**kwargs: object) -> None:
    CallbackString.callbacks = 0
    try:
        _parse(**kwargs)
    except OwnerSurgerySemanticError:
        pass
    else:
        raise AssertionError("hostile observation input must fail closed")
    assert CallbackString.callbacks == 0


def main() -> int:
    receipt = source_receipt()
    assert receipt["strictUtf8EncodeFailureTyped"] is True
    assert receipt["boundedObservationAdmission"] is True
    assert receipt["observationByteCeiling"] == MAX_SEMANTIC_OBSERVATION_BYTES
    assert receipt["preEncodeCodepointCeiling"] == MAX_SEMANTIC_OBSERVATION_BYTES
    assert receipt["canonicalOwnerConsumption"] is True
    assert receipt["descriptorBackendConsumption"] is True
    assert receipt["regressionExecuted"] is False
    assert receipt["tested"] is False

    patch = (
        f"# STATUS: APPLIED_SOURCE\n"
        f"# BASE OWNER BLOB: {BASE}\n"
        f"diff --git a/{DEFAULT_OWNER} b/{DEFAULT_OWNER}\n"
    )
    patch_count, patch_sha = _witness(patch)
    patch_record = _parse(
        path="patches/try-forever-example.patch",
        kind="patch",
        text=patch,
        byte_count=patch_count,
        sha256=patch_sha,
    )
    assert patch_record.owner == DEFAULT_OWNER
    assert patch_record.base_blob == BASE
    assert patch_record.artifact_byte_count == patch_count
    assert patch_record.artifact_sha256 == patch_sha

    delta = json.dumps(
        {
            "schema": "try-forever-owner-delta.v1",
            "owner": DEFAULT_OWNER,
            "baseBlob": BASE,
            "status": "APPLIED_SOURCE",
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    delta_count, delta_sha = _witness(delta)
    delta_record = _parse(
        path="patches/try-forever-example.delta.json",
        kind="delta_json",
        text=delta,
        byte_count=delta_count,
        sha256=delta_sha,
    )
    assert delta_record.owner == DEFAULT_OWNER
    assert delta_record.base_blob == BASE
    assert delta_record.artifact_byte_count == delta_count
    assert delta_record.artifact_sha256 == delta_sha

    for hostile_field in ("path", "kind", "text", "sha256"):
        values: dict[str, object] = {
            "path": "patches/try-forever-example.patch",
            "kind": "patch",
            "text": patch,
            "byte_count": patch_count,
            "sha256": patch_sha,
        }
        values[hostile_field] = CallbackString(str(values[hostile_field]))
        _must_reject_without_callbacks(**values)

    bad_count = {
        "path": "patches/try-forever-example.patch",
        "kind": "patch",
        "text": patch,
        "byte_count": patch_count + 1,
        "sha256": patch_sha,
    }
    try:
        _parse(**bad_count)
    except OwnerSurgerySemanticError:
        pass
    else:
        raise AssertionError("mismatched byte witness must fail closed")

    bad_sha = {
        "path": "patches/try-forever-example.patch",
        "kind": "patch",
        "text": patch,
        "byte_count": patch_count,
        "sha256": "0" * 64,
    }
    try:
        _parse(**bad_sha)
    except OwnerSurgerySemanticError:
        pass
    else:
        raise AssertionError("mismatched SHA witness must fail closed")

    # Direct callers cannot turn the pure producer into an unbounded encode/hash surface. The
    # claimed byte witness and a definitely-over-budget code-point string fail before encoding, and
    # multibyte text is checked again after a bounded encode.
    try:
        _parse(
            path="patches/try-forever-over-budget-count.patch",
            kind="patch",
            text=patch,
            byte_count=MAX_SEMANTIC_OBSERVATION_BYTES + 1,
            sha256=patch_sha,
        )
    except OwnerSurgerySemanticError as exc:
        assert "byte_count exceeds semantic observation byte ceiling" in str(exc)
    else:
        raise AssertionError("over-budget claimed byte witness must fail before semantic work")

    oversized_text = "x" * (MAX_SEMANTIC_OBSERVATION_BYTES + 1)
    try:
        _parse(
            path="patches/try-forever-over-budget-text.patch",
            kind="patch",
            text=oversized_text,
            byte_count=0,
            sha256=hashlib.sha256(b"").hexdigest(),
        )
    except OwnerSurgerySemanticError as exc:
        assert "pre-encode code-point ceiling" in str(exc)
    else:
        raise AssertionError("over-budget source text must fail before UTF-8 encode")

    multibyte_text = "é" * ((MAX_SEMANTIC_OBSERVATION_BYTES // 2) + 1)
    try:
        _parse(
            path="patches/try-forever-over-budget-multibyte.patch",
            kind="patch",
            text=multibyte_text,
            byte_count=MAX_SEMANTIC_OBSERVATION_BYTES,
            sha256="0" * 64,
        )
    except OwnerSurgerySemanticError as exc:
        assert "UTF-8 content exceeds semantic observation byte ceiling" in str(exc)
    else:
        raise AssertionError("multibyte UTF-8 expansion must remain inside the semantic byte throat")

    lone_surrogate = "\ud800"
    try:
        _parse(
            path="patches/try-forever-surrogate.patch",
            kind="patch",
            text=lone_surrogate,
            byte_count=0,
            sha256=hashlib.sha256(b"").hexdigest(),
        )
    except OwnerSurgerySemanticError as exc:
        assert "strict UTF-8 encodable" in str(exc)
    else:
        raise AssertionError("lone surrogate text must fail inside semantic error custody")

    duplicate_delta = (
        '{"schema":"try-forever-owner-delta.v1",'
        f'"owner":"{DEFAULT_OWNER}",'
        f'"baseBlob":"{BASE}","baseBlob":"{BASE}",'
        '"status":"APPLIED_SOURCE"}'
    )
    duplicate_count, duplicate_sha = _witness(duplicate_delta)
    try:
        _parse(
            path="patches/try-forever-duplicate.delta.json",
            kind="delta_json",
            text=duplicate_delta,
            byte_count=duplicate_count,
            sha256=duplicate_sha,
        )
    except OwnerSurgerySemanticError:
        pass
    else:
        raise AssertionError("duplicate delta members must fail closed")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
