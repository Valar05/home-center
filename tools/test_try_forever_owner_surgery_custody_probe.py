#!/usr/bin/env python3
"""Broad SOURCE-ONLY regression for current TRY FOREVER owner-surgery custody v10.

This fixture intentionally follows the canonical backend selected by current platform capability.
It preserves common authority/collision semantics while treating descriptor-vs-portable root custody
as backend-conditional evidence. Focused regressions own stronger desired contracts such as exact
programmatic argv admission and descriptor failure-evidence parity.

Source existence is not regression execution, TESTED, runtime, deployment, phone delivery, or
acceptance evidence.
"""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from try_forever_owner_surgery_backend_policy import DESCRIPTOR_BACKEND, PORTABLE_BACKEND
from try_forever_owner_surgery_custody_probe import (
    MAX_ARTIFACT_BYTES,
    MAX_CUSTODY_ARTIFACTS,
    MAX_CUSTODY_DIRECTORY_ENTRIES,
    classify,
)


OWNER = "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
BASE = "c5de1411a6b68087ae17aff83c032af754587150"
STALE = "1111111111111111111111111111111111111111"


def patch(state: str, name: str, base: str = BASE) -> str:
    return (
        f"# STATUS: {state}\n"
        f"# BASE OWNER BLOB: {base}\n"
        f"# OWNER: {OWNER}\n"
        f"# fixture: {name}\n"
        "diff --git a/owner b/owner\n"
    )


def delta(
    state: str,
    name: str,
    base: str = BASE,
    *,
    base_key: str = "baseBlob",
    state_key: str = "state",
) -> str:
    return json.dumps(
        {
            "schema": "try-forever-owner-delta.v1",
            "owner": OWNER,
            base_key: base,
            state_key: state,
            "fixture": name,
        },
        indent=2,
    ) + "\n"


def assert_zero_partial_authority(result: dict[str, object]) -> None:
    assert result["surgeries"] == []
    assert result["collisionSets"] == []
    assert result["staleBaseGroups"] == []
    assert result["unverifiedBaseGroups"] == []
    assert result["evidenceComplete"] is False


def assert_current_capability(result: dict[str, object]) -> None:
    capability = result["capability"]
    assert result["schema"] == "try-forever-owner-surgery-custody.v10"
    assert result["backend"] in {DESCRIPTOR_BACKEND, PORTABLE_BACKEND}
    assert result["portableFallbackAttempted"] is False
    assert capability["selectedBackend"] == result["backend"]
    assert capability["portableFallbackAttempted"] is False
    assert capability["sourceInspection"] is True
    assert capability["patchArtifactInspection"] is True
    assert capability["deltaArtifactInspection"] is True
    assert capability["artifactRootAtomicBinding"] is False
    assert capability["boundedArtifactDirectoryScan"] is True
    assert capability["boundedArtifactCandidateSet"] is True
    assert capability["boundedArtifactRead"] is True
    assert capability["finiteRegularArtifactCustody"] is True
    assert capability["currentOwnerCustodyProvided"] is True
    assert capability["ownerWired"] is True
    assert capability["patchApplied"] is False
    assert capability["regressionExecuted"] is False
    assert capability["tested"] is False
    assert capability["runtimeUi"] is False
    assert capability["runtimeTalkBack"] is False
    assert capability["phoneDelivered"] is False

    if result["backend"] == DESCRIPTOR_BACKEND:
        assert capability["descriptorRootCustody"] is True
        assert capability["artifactRootIdentityRevalidation"] is False
        assert capability["artifactRootFinalRevalidation"] is False
    else:
        assert capability["descriptorRootCustody"] is False
        assert capability["artifactRootIdentityRevalidation"] is True
        assert capability["artifactRootFinalRevalidation"] is True


def main() -> int:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "try-forever-a.patch").write_text(
            patch("CORRECTED_PROPOSED_NOT_APPLIED", "a"), encoding="utf-8"
        )
        (root / "try-forever-b.patch").write_text(
            patch("CANONICAL_PROPOSED_NOT_APPLIED", "b"), encoding="utf-8"
        )
        (root / "try-forever-c.delta.json").write_text(
            delta(
                "CORRECTED_PROPOSED_NOT_APPLIED",
                "c",
                base_key="ownerBaseBlob",
                state_key="status",
            ),
            encoding="utf-8",
        )
        (root / "try-forever-stale-a.patch").write_text(
            patch("CORRECTED_PROPOSED_NOT_APPLIED", "stale-a", STALE), encoding="utf-8"
        )
        (root / "try-forever-stale-b.patch").write_text(
            patch("CANONICAL_PROPOSED_NOT_APPLIED", "stale-b", STALE), encoding="utf-8"
        )
        (root / "try-forever-stale-c.delta.json").write_text(
            delta("CANONICAL_PROPOSED_NOT_APPLIED", "stale-c", STALE, base_key="baseOwnerBlob"),
            encoding="utf-8",
        )
        (root / "try-forever-old.patch").write_text(
            patch("SUPERSEDED_BY_COMBINED_PATCH__DO_NOT_APPLY_ALONE", "old"), encoding="utf-8"
        )
        (root / "try-forever-rejected.patch").write_text(
            patch("REJECTED_SUPERSEDED__DO_NOT_APPLY", "rejected"), encoding="utf-8"
        )
        (root / "try-forever-applied.patch").write_text(
            patch("APPLIED_SOURCE", "applied"), encoding="utf-8"
        )
        (root / "try-forever-applied.delta.json").write_text(
            delta("APPLIED_SOURCE", "applied-delta"), encoding="utf-8"
        )

        result = classify(root, {OWNER: BASE})
        assert_current_capability(result)
        backend = result["backend"]
        assert result["artifactKindsScanned"] == ["patch", "delta_json"]
        assert result["artifactReadBudgetBytes"] == MAX_ARTIFACT_BYTES
        assert result["artifactCandidateBudget"] == MAX_CUSTODY_ARTIFACTS
        assert result["artifactCandidatesObserved"] == 10
        assert result["artifactDirectoryEntryBudget"] == MAX_CUSTODY_DIRECTORY_ENTRIES
        assert result["artifactDirectoryEntriesObserved"] == 10
        assert result["discoveryErrors"] == []
        assert result["evidenceComplete"] is True

        collisions = result["collisionSets"]
        assert len(collisions) == 1, collisions
        collision = collisions[0]
        assert collision["owner"] == OWNER
        assert collision["baseBlob"] == BASE
        assert collision["currentOwnerBlob"] == BASE
        assert collision["status"] == "CURRENT_BASE_COLLISION_SET"
        assert [Path(item["path"]).name for item in collision["promotionCandidates"]] == [
            "try-forever-a.patch",
            "try-forever-b.patch",
            "try-forever-c.delta.json",
        ]

        stale = result["staleBaseGroups"]
        assert len(stale) == 1, stale
        assert stale[0]["status"] == "STALE_BASE_GROUP"
        assert stale[0]["baseBlob"] == STALE
        assert stale[0]["currentOwnerBlob"] == BASE
        assert [Path(item["path"]).name for item in stale[0]["promotionCandidates"]] == [
            "try-forever-stale-a.patch",
            "try-forever-stale-b.patch",
            "try-forever-stale-c.delta.json",
        ]

        excluded = {
            Path(item["path"]).name
            for group in collisions + stale
            for item in group["promotionCandidates"]
        }
        assert "try-forever-old.patch" not in excluded
        assert "try-forever-rejected.patch" not in excluded
        assert "try-forever-applied.patch" not in excluded
        assert "try-forever-applied.delta.json" not in excluded

        unverified = classify(root)
        assert unverified["collisionSets"] == []
        assert unverified["staleBaseGroups"] == []
        assert len(unverified["unverifiedBaseGroups"]) == 2
        assert all(
            group["status"] == "UNVERIFIED_BASE_GROUP"
            for group in unverified["unverifiedBaseGroups"]
        )

        moved_owner = classify(root, {OWNER: "2222222222222222222222222222222222222222"})
        assert moved_owner["collisionSets"] == []
        assert len(moved_owner["staleBaseGroups"]) == 2

    # Root redirectors fail closed on both backends. Error taxonomy is backend-conditional because
    # descriptor selection rejects during held-root open while portable custody rejects root topology.
    with TemporaryDirectory() as tmp:
        base_root = Path(tmp)
        target = base_root / "real-patches"
        target.mkdir()
        (target / "try-forever-a.patch").write_text(
            patch("CORRECTED_PROPOSED_NOT_APPLIED", "a"), encoding="utf-8"
        )
        link = base_root / "patches-link"
        try:
            link.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            pass
        else:
            result = classify(link, {OWNER: BASE})
            assert_zero_partial_authority(result)
            assert result["artifactDirectoryEntriesObserved"] == 0
            assert result["artifactCandidatesObserved"] == 0
            assert len(result["discoveryErrors"]) == 1
            error = result["discoveryErrors"][0]
            if backend == DESCRIPTOR_BACKEND:
                assert error["artifact_kind"] == "descriptor_backend"
                assert "held directory" in error["boundary"]
            else:
                assert error["artifact_kind"] == "artifact_root"
                assert "symlink" in error["boundary"]

    # Candidate-set max+1 fails the whole authority set. Portable custody currently preserves
    # observed-work counts; descriptor failure-evidence parity is pinned by a separate RED fixture.
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "try-forever-a.patch").write_text(
            patch("CORRECTED_PROPOSED_NOT_APPLIED", "a"), encoding="utf-8"
        )
        (root / "try-forever-b.patch").write_text(
            patch("CORRECTED_PROPOSED_NOT_APPLIED", "b"), encoding="utf-8"
        )
        (root / "try-forever-c.delta.json").write_text(
            delta("CORRECTED_PROPOSED_NOT_APPLIED", "c"), encoding="utf-8"
        )
        result = classify(root, {OWNER: BASE}, max_candidates=2)
        assert result["artifactCandidateBudget"] == 2
        assert_zero_partial_authority(result)
        assert len(result["discoveryErrors"]) == 1
        if result["backend"] == PORTABLE_BACKEND:
            assert result["artifactCandidatesObserved"] == 3
            assert result["artifactDirectoryEntriesObserved"] == 3
            assert result["discoveryErrors"][0]["artifact_kind"] == "artifact_inventory"
            assert "candidate set exceeds 2" in result["discoveryErrors"][0]["boundary"]
        else:
            assert result["artifactCandidatesObserved"] == 0
            assert result["artifactDirectoryEntriesObserved"] == 0
            assert result["discoveryErrors"][0]["artifact_kind"] == "descriptor_backend"

    # Unrelated entries consume traversal work too. The same descriptor evidence-parity boundary
    # applies to max+1 failure receipts and is deliberately not hidden here.
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "junk-a.txt").write_text("a", encoding="utf-8")
        (root / "junk-b.txt").write_text("b", encoding="utf-8")
        (root / "try-forever-a.patch").write_text(
            patch("CORRECTED_PROPOSED_NOT_APPLIED", "a"), encoding="utf-8"
        )
        result = classify(root, {OWNER: BASE}, max_entries=2)
        assert result["artifactDirectoryEntryBudget"] == 2
        assert_zero_partial_authority(result)
        assert len(result["discoveryErrors"]) == 1
        if result["backend"] == PORTABLE_BACKEND:
            assert result["artifactDirectoryEntriesObserved"] == 3
            assert result["discoveryErrors"][0]["artifact_kind"] == "artifact_inventory"
            assert "directory scan exceeds 2" in result["discoveryErrors"][0]["boundary"]
        else:
            assert result["artifactCandidatesObserved"] == 0
            assert result["artifactDirectoryEntriesObserved"] == 0
            assert result["discoveryErrors"][0]["artifact_kind"] == "descriptor_backend"

    # Special topology, strict UTF-8, and finite-byte admission all fail closed. Descriptor custody
    # currently collapses artifact-custody failures to one descriptor-backend diagnostic; a focused
    # RED fixture owns the desired per-artifact failure evidence contract.
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "try-forever-special.patch").mkdir()
        result = classify(root, {OWNER: BASE})
        assert_zero_partial_authority(result)
        assert len(result["discoveryErrors"]) == 1

    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "try-forever-bad-utf8.patch").write_bytes(
            b"# STATUS: CORRECTED_PROPOSED_NOT_APPLIED\n# BASE OWNER BLOB: "
            + BASE.encode("ascii")
            + b"\n# OWNER: "
            + OWNER.encode("ascii")
            + b"\n\xff\n"
        )
        result = classify(root, {OWNER: BASE})
        assert_zero_partial_authority(result)
        assert len(result["discoveryErrors"]) == 1
        assert "UTF-8" in result["discoveryErrors"][0]["boundary"]

    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "try-forever-oversized.patch").write_bytes(b"x" * (MAX_ARTIFACT_BYTES + 1))
        (root / "try-forever-oversized.delta.json").write_bytes(b"{" + b"x" * MAX_ARTIFACT_BYTES)
        result = classify(root, {OWNER: BASE})
        assert_zero_partial_authority(result)
        if result["backend"] == PORTABLE_BACKEND:
            assert len(result["discoveryErrors"]) == 2
            assert {item["artifact_kind"] for item in result["discoveryErrors"]} == {
                "patch",
                "delta_json",
            }
        else:
            assert len(result["discoveryErrors"]) == 1
            assert result["discoveryErrors"][0]["artifact_kind"] == "descriptor_backend"

    # Semantic conflicts remain artifact-addressable on both backends because exact observation
    # succeeded and the shared semantic producer owns the rejection.
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        malformed = {
            "schema": "try-forever-owner-delta.v1",
            "owner": OWNER,
            "baseBlob": BASE,
            "ownerBaseBlob": STALE,
            "state": "CORRECTED_PROPOSED_NOT_APPLIED",
        }
        (root / "try-forever-conflicting.delta.json").write_text(
            json.dumps(malformed), encoding="utf-8"
        )
        result = classify(root, {OWNER: BASE})
        assert_zero_partial_authority(result)
        assert len(result["discoveryErrors"]) == 1
        assert result["discoveryErrors"][0]["artifact_kind"] == "delta_json"
        assert "conflicting base owner blob aliases" in result["discoveryErrors"][0]["boundary"]

    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "try-forever-duplicate.delta.json").write_text(
            '{"schema":"try-forever-owner-delta.v1","owner":"a","owner":"b",'
            f'"baseBlob":"{BASE}","state":"CORRECTED_PROPOSED_NOT_APPLIED"}}',
            encoding="utf-8",
        )
        result = classify(root)
        assert_zero_partial_authority(result)
        assert len(result["discoveryErrors"]) == 1
        assert result["discoveryErrors"][0]["artifact_kind"] == "delta_json"
        assert "duplicate JSON member" in result["discoveryErrors"][0]["boundary"]

    print("TRY FOREVER owner surgery custody v10 broad regression source converged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
