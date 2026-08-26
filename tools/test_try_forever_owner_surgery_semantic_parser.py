#!/usr/bin/env python3
"""SOURCE-ONLY regression for exact-observation owner-surgery semantic production.

The fixture is intentionally not execution evidence. It pins patch/delta semantic parity, content-
witness binding, duplicate-member rejection, and callback-free exact scalar admission for the pure
producer that a future canonical descriptor composition may consume.
"""

import hashlib
import json

from try_forever_owner_surgery_default_owner_binding import DEFAULT_OWNER
from try_forever_owner_surgery_semantic_parser import (
    OwnerSurgerySemanticError,
    parse_owner_surgery_observation,
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
