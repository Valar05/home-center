#!/usr/bin/env python3
"""Regression source for operator-facing descriptor-shadow receipt projection.

SOURCE ONLY. This file has not been observed executing in an authorized test lane.
"""

import hashlib
from pathlib import Path

from try_forever_owner_surgery_shadow_receipt_projection import (
    SHADOW_SCHEMA,
    project_shadow_receipt,
)


ROOT = Path("/repo")
CANONICAL_SHA = "1" * 64
ARTIFACT_SHA = "a" * 64


def artifact(path: str, *, byte_count: int = 10, sha256: str = ARTIFACT_SHA):
    return {
        "path": path,
        "byteCount": byte_count,
        "sha256": sha256,
    }


def shadow_result(**overrides):
    boundary = "descriptor staging matched exact content identity"
    result = {
        "schema": SHADOW_SCHEMA,
        "status": "SHADOW_MATCH",
        "canonicalResultSha256": CANONICAL_SHA,
        "boundary": boundary,
        "portableShadowArtifacts": [artifact("/repo/patches/try-forever-a.patch")],
        "descriptorArtifacts": [artifact("/repo/patches/try-forever-a.patch")],
        "artifactSetMatch": True,
        "metricsMatch": True,
        "contentIdentityMatch": True,
        "descriptorAuthorityAdmitted": False,
        "ownerMutation": False,
    }
    result.update(overrides)
    return result


def expect_rejected(result, needle: str) -> None:
    try:
        project_shadow_receipt(ROOT, result)
    except ValueError as exc:
        assert needle in str(exc), (needle, str(exc))
    else:
        raise AssertionError(f"unsafe shadow result earned a display receipt: {result!r}")


def main() -> int:
    raw = shadow_result()
    receipt = project_shadow_receipt(ROOT, raw)
    assert receipt["status"] == "SHADOW_MATCH"
    assert receipt["portableArtifacts"] == [
        {
            "path": "patches/try-forever-a.patch",
            "pathScope": "REPOSITORY",
            "byteCount": 10,
            "sha256": ARTIFACT_SHA,
        }
    ]
    assert receipt["descriptorArtifacts"] == receipt["portableArtifacts"]
    assert receipt["canonicalResultSha256"] == CANONICAL_SHA
    assert receipt["boundarySha256"] == hashlib.sha256(
        raw["boundary"].encode("utf-8")
    ).hexdigest()
    assert raw["boundary"] not in str(receipt)
    assert receipt["authorityAdmitted"] is False
    assert receipt["tested"] is False

    # Repository control/layout evidence is revealed, not emitted raw.
    separated_path = "/repo/patches/a\u2028b.patch"
    separated = project_shadow_receipt(
        ROOT,
        shadow_result(
            portableShadowArtifacts=[artifact(separated_path)],
            descriptorArtifacts=[artifact(separated_path)],
        ),
    )
    assert separated["portableArtifacts"][0]["path"] == "patches/a\\u{2028}b.patch"

    # External host topology becomes one constant marker with no host fingerprint oracle.
    external = project_shadow_receipt(
        ROOT,
        shadow_result(
            portableShadowArtifacts=[artifact("/tmp/user-secret/a.patch")],
            descriptorArtifacts=[artifact("/tmp/user-secret/a.patch")],
        ),
    )
    assert external["portableArtifacts"][0]["path"] == "<external-path>"
    assert external["portableArtifacts"][0]["pathScope"] == "EXTERNAL"
    assert "user-secret" not in str(external)

    # Long repository paths collapse to whole-identity evidence rather than a grapheme-cut prefix.
    long_name = "swan-" * 80 + ".patch"
    long_path = f"/repo/patches/{long_name}"
    collapsed = project_shadow_receipt(
        ROOT,
        shadow_result(
            portableShadowArtifacts=[artifact(long_path)],
            descriptorArtifacts=[artifact(long_path)],
        ),
    )
    projected = collapsed["portableArtifacts"][0]["path"]
    assert projected.startswith("<repo-path>...#")
    assert long_name not in projected

    # Raw exception/control prose never becomes routine display text.
    hostile_boundary = "decoder failed\nsecret path /home/drew/x \u202e"
    wounded = project_shadow_receipt(
        ROOT,
        shadow_result(
            status="DESCRIPTOR_WOUND",
            boundary=hostile_boundary,
            portableShadowArtifacts=[],
            descriptorArtifacts=[],
            artifactSetMatch=False,
            metricsMatch=False,
            contentIdentityMatch=False,
        ),
    )
    assert hostile_boundary not in str(wounded)
    assert "/home/drew" not in str(wounded)
    assert wounded["boundarySha256"] == hashlib.sha256(
        hostile_boundary.encode("utf-8")
    ).hexdigest()

    wrong_schema = shadow_result(schema="try-forever-owner-surgery-descriptor-shadow.v4")
    expect_rejected(wrong_schema, "exact descriptor-shadow v3")
    expect_rejected(shadow_result(status="UNKNOWN"), "not one admitted receipt state")
    expect_rejected(shadow_result(canonicalResultSha256="A" * 64), "64 lowercase hexadecimal")
    expect_rejected(shadow_result(descriptorAuthorityAdmitted=True), "never carry descriptor authority")
    expect_rejected(shadow_result(ownerMutation=True), "never claim owner mutation")
    expect_rejected(
        shadow_result(portableShadowArtifacts=[artifact("/repo/a.patch", byte_count=True)]),
        "non-negative integer",
    )
    expect_rejected(
        shadow_result(portableShadowArtifacts=[artifact("/repo/a.patch", sha256="B" * 64)]),
        "64 lowercase hexadecimal",
    )
    expect_rejected(shadow_result(artifactSetMatch="true"), "boolean or null")
    expect_rejected(shadow_result(metricsMatch=1), "boolean or null")
    expect_rejected(shadow_result(contentIdentityMatch=[]), "boolean or null")
    expect_rejected(shadow_result(artifactSetMatch=False), "all three exact comparison booleans true")
    expect_rejected(
        shadow_result(status="SHADOW_DIVERGED"),
        "requires at least one comparison not true",
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
