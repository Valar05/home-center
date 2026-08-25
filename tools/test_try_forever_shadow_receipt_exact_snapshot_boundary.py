#!/usr/bin/env python3
"""Hostile regression source for descriptor-shadow one-observation exact-JSON custody.

SOURCE ONLY. This fixture has not been observed executing in an authorized regression lane.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from pathlib import Path

from try_forever_owner_surgery_descriptor_shadow_audit import (
    CANONICAL_SCHEMA,
    SCHEMA as SHADOW_SCHEMA,
    SUPPORTED,
)
from try_forever_owner_surgery_shadow_receipt_projection import project_shadow_receipt
from try_forever_owner_surgery_shadow_receipt_self_integrity import (
    TEMPORAL_BINDING_SCHEMA,
    TEMPORAL_RECEIPT_INTEGRITY_SCHEMA,
    project_shadow_receipt_with_self_integrity,
)


ROOT = Path("/repo")
CANONICAL_SHA = "1" * 64
ARTIFACT_SHA = "a" * 64


class CallbackMapping(Mapping[str, object]):
    """Caller-owned Mapping that records any attempted observation."""

    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.callbacks = 0

    def __getitem__(self, key: str) -> object:
        self.callbacks += 1
        return self.payload[key]

    def __iter__(self) -> Iterator[str]:
        self.callbacks += 1
        return iter(self.payload)

    def __len__(self) -> int:
        self.callbacks += 1
        return len(self.payload)

    def get(self, key: str, default=None):
        self.callbacks += 1
        return self.payload.get(key, default)


class CallbackDict(dict):
    """A dict subclass that must be rejected before its traversal callback executes."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.callbacks = 0

    def items(self):
        self.callbacks += 1
        return super().items()


def artifact() -> dict[str, object]:
    return {
        "path": "patches/a.patch",
        "byteCount": 10,
        "sha256": ARTIFACT_SHA,
    }


def temporal() -> dict[str, object]:
    return {
        "schema": TEMPORAL_BINDING_SCHEMA,
        "status": "TEMPORAL_CONTENT_BOUND",
        "canonicalResultSha256": CANONICAL_SHA,
        "shadowCanonicalResultSha256": CANONICAL_SHA,
        "temporalBindingProven": True,
        "authorityAdmitted": False,
        "ownerMutation": False,
        "regressionExecuted": False,
        "tested": False,
        "runtimeUi": False,
        "runtimeTalkBack": False,
        "phoneDelivered": False,
        "boundary": "bounded semantic result only",
        "receiptIntegritySchema": TEMPORAL_RECEIPT_INTEGRITY_SCHEMA,
        "shadowReceiptContextAdmitted": True,
    }


def raw_match() -> dict[str, object]:
    return {
        "schema": SHADOW_SCHEMA,
        "status": "SHADOW_MATCH",
        "canonicalAuthorityBackend": "PORTABLE_PATHNAME_REVALIDATION",
        "canonicalAuthoritySchema": CANONICAL_SCHEMA,
        "canonicalResultSha256": CANONICAL_SHA,
        "canonicalEvidenceComplete": True,
        "canonicalArtifactDirectoryEntriesObserved": 2,
        "canonicalArtifactCandidatesObserved": 1,
        "descriptorCapabilityStatus": SUPPORTED,
        "descriptorAuthorityAdmitted": False,
        "ownerMutation": False,
        "boundary": "exact comparison completed",
        "portableShadowArtifacts": [artifact()],
        "descriptorArtifacts": [artifact()],
        "descriptorArtifactDirectoryEntriesObserved": 2,
        "descriptorArtifactCandidatesObserved": 1,
        "artifactSetMatch": True,
        "metricsMatch": True,
        "contentIdentityMatch": True,
        "temporalContentBinding": temporal(),
        "temporalBindingProven": True,
    }


def expect_rejected_without_callbacks(fn, hostile, needle: str) -> None:
    try:
        fn(hostile)
    except ValueError as exc:
        assert needle in str(exc), (needle, str(exc))
    else:
        raise AssertionError("caller-owned mapping escaped exact snapshot admission")
    assert hostile.callbacks == 0, "caller-owned mapping callback executed before rejection"


def main() -> int:
    raw = raw_match()

    # Ordinary exact-dict behavior remains admitted on both existing owners.
    projected = project_shadow_receipt(ROOT, raw)
    assert projected["status"] == "SHADOW_MATCH"
    audited = project_shadow_receipt_with_self_integrity(ROOT, raw)
    assert audited["status"] == "SHADOW_MATCH"
    assert audited["comparisonEvidenceRecomputed"] is True

    # Root Mapping implementations must be rejected before get/iter/len/item callbacks execute.
    projector_mapping = CallbackMapping(raw_match())
    expect_rejected_without_callbacks(
        lambda value: project_shadow_receipt(ROOT, value),
        projector_mapping,
        "exact built-in dict",
    )
    integrity_mapping = CallbackMapping(raw_match())
    expect_rejected_without_callbacks(
        lambda value: project_shadow_receipt_with_self_integrity(ROOT, value),
        integrity_mapping,
        "exact built-in dict",
    )

    # Nested dict subclasses are not exact JSON objects either; their traversal callbacks stay cold.
    nested = CallbackDict(artifact())
    projector_nested = raw_match()
    projector_nested["portableShadowArtifacts"] = [nested]
    try:
        project_shadow_receipt(ROOT, projector_nested)
    except ValueError as exc:
        assert "exact JSON" in str(exc), str(exc)
    else:
        raise AssertionError("nested dict subclass escaped projector snapshot custody")
    assert nested.callbacks == 0

    nested_integrity = CallbackDict(artifact())
    integrity_nested = raw_match()
    integrity_nested["descriptorArtifacts"] = [nested_integrity]
    try:
        project_shadow_receipt_with_self_integrity(ROOT, integrity_nested)
    except ValueError as exc:
        assert "exact JSON" in str(exc), str(exc)
    else:
        raise AssertionError("nested dict subclass escaped self-integrity snapshot custody")
    assert nested_integrity.callbacks == 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
