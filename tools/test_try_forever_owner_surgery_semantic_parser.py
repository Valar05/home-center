#!/usr/bin/env python3
"""SOURCE-ONLY regression for exact-observation owner-surgery semantic production.

The fixture is intentionally not execution evidence. It pins patch/delta semantic parity, content-
witness binding, duplicate-member rejection, callback-free exact scalar admission, bounded direct
semantic work, bounded ASCII-safe diagnostics, typed strict-UTF-8 failure, and typed deep-JSON
recursion failure for the producer consumed by canonical portable and descriptor custody paths.
"""

import hashlib
import json

from try_forever_owner_surgery_default_owner_binding import DEFAULT_OWNER
from try_forever_owner_surgery_semantic_parser import (
    MAX_SEMANTIC_ARTIFACT_KIND_CODEPOINTS,
    MAX_SEMANTIC_DIAGNOSTIC_SEGMENT_CHARS,
    MAX_SEMANTIC_OBSERVATION_BYTES,
    MAX_SEMANTIC_PATH_CODEPOINTS,
    MAX_SEMANTIC_SHA256_CODEPOINTS,
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


def _assert_safe_bounded_diagnostic(message: str) -> None:
    assert "\n" not in message
    assert "\r" not in message
    assert "\u202e" not in message.lower()
    assert "\ud800" not in message
    assert len(message) <= 192


def main() -> int:
    receipt = source_receipt()
    assert receipt["strictUtf8EncodeFailureTyped"] is True
    assert receipt["deepJsonRecursionFailureTyped"] is True
    assert receipt["boundedObservationAdmission"] is True
    assert receipt["observationByteCeiling"] == MAX_SEMANTIC_OBSERVATION_BYTES
    assert receipt["preEncodeCodepointCeiling"] == MAX_SEMANTIC_OBSERVATION_BYTES
    assert receipt["pathCodepointCeiling"] == MAX_SEMANTIC_PATH_CODEPOINTS
    assert receipt["artifactKindCodepointCeiling"] == MAX_SEMANTIC_ARTIFACT_KIND_CODEPOINTS
    assert receipt["sha256CodepointLength"] == MAX_SEMANTIC_SHA256_CODEPOINTS
    assert receipt["boundedAsciiDiagnosticProjection"] is True
    assert receipt["diagnosticSegmentCharCeiling"] == MAX_SEMANTIC_DIAGNOSTIC_SEGMENT_CHARS
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

    # Direct scalar evidence must cross finite source gates before set hashing or regex work.
    for name, values in (
        (
            "path",
            {
                "path": "p" * (MAX_SEMANTIC_PATH_CODEPOINTS + 1),
                "kind": "patch",
                "text": patch,
                "byte_count": patch_count,
                "sha256": patch_sha,
            },
        ),
        (
            "artifact_kind",
            {
                "path": "patches/try-forever-example.patch",
                "kind": "x" * (MAX_SEMANTIC_ARTIFACT_KIND_CODEPOINTS + 1),
                "text": patch,
                "byte_count": patch_count,
                "sha256": patch_sha,
            },
        ),
        (
            "sha256",
            {
                "path": "patches/try-forever-example.patch",
                "kind": "patch",
                "text": patch,
                "byte_count": patch_count,
                "sha256": "a" * (MAX_SEMANTIC_SHA256_CODEPOINTS + 1),
            },
        ),
    ):
        try:
            _parse(**values)
        except OwnerSurgerySemanticError as exc:
            assert "source ceiling" in str(exc) or "exactly 64" in str(exc)
        else:
            raise AssertionError(f"over-budget {name} must fail before semantic work")

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

    # The observation byte throat alone does not guarantee typed parser failure: deeply nested but
    # sub-megabyte JSON can exceed CPython's decoder recursion capacity. That failure must remain in
    # OwnerSurgerySemanticError rather than leaking raw RecursionError across the semantic boundary.
    deeply_nested_delta = ("[" * 10_000) + "0" + ("]" * 10_000)
    deep_count, deep_sha = _witness(deeply_nested_delta)
    assert deep_count < MAX_SEMANTIC_OBSERVATION_BYTES
    try:
        _parse(
            path="patches/try-forever-deep.delta.json",
            kind="delta_json",
            text=deeply_nested_delta,
            byte_count=deep_count,
            sha256=deep_sha,
        )
    except OwnerSurgerySemanticError as exc:
        assert "semantic nesting capacity" in str(exc)
    except RecursionError as exc:
        raise AssertionError("deep bounded JSON must not escape typed semantic failure custody") from exc
    else:
        raise AssertionError("deep non-object delta JSON must fail closed")

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

    # Hostile member/schema text remains exact in the JSON evidence but is projected as bounded
    # ASCII-only diagnostic prose. It must not become newline/bidi/surrogate log or TalkBack poison.
    hostile_key = "field\n\u202e\ud800" + ("x" * 256)
    hostile_duplicate = json.dumps(
        {
            "schema": "try-forever-owner-delta.v1",
            "owner": DEFAULT_OWNER,
            "baseBlob": BASE,
            "status": "APPLIED_SOURCE",
        },
        ensure_ascii=True,
        separators=(",", ":"),
    )[:-1] + f',{json.dumps(hostile_key, ensure_ascii=True)}:1,{json.dumps(hostile_key, ensure_ascii=True)}:2}}'
    hostile_count, hostile_sha = _witness(hostile_duplicate)
    try:
        _parse(
            path="patches/try-forever-hostile-key.delta.json",
            kind="delta_json",
            text=hostile_duplicate,
            byte_count=hostile_count,
            sha256=hostile_sha,
        )
    except OwnerSurgerySemanticError as exc:
        message = str(exc)
        _assert_safe_bounded_diagnostic(message)
        assert "<text>...#" in message
    else:
        raise AssertionError("hostile duplicate member must fail inside bounded diagnostic custody")

    hostile_schema = "schema\n\u202e" + ("y" * 256)
    hostile_schema_delta = json.dumps(
        {
            "schema": hostile_schema,
            "owner": DEFAULT_OWNER,
            "baseBlob": BASE,
            "status": "APPLIED_SOURCE",
        },
        ensure_ascii=True,
        separators=(",", ":"),
    )
    hostile_schema_count, hostile_schema_sha = _witness(hostile_schema_delta)
    try:
        _parse(
            path="patches/try-forever-hostile-schema.delta.json",
            kind="delta_json",
            text=hostile_schema_delta,
            byte_count=hostile_schema_count,
            sha256=hostile_schema_sha,
        )
    except OwnerSurgerySemanticError as exc:
        message = str(exc)
        _assert_safe_bounded_diagnostic(message)
        assert "<text>...#" in message
    else:
        raise AssertionError("hostile schema text must fail inside bounded diagnostic custody")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
