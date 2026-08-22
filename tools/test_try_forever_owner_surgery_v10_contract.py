#!/usr/bin/env python3
"""Focused source regression for the current owner-surgery custody v10 contract.

SOURCE ONLY. This deliberately does not claim the older broad custody fixture is repaired or that any
regression executed. It pins the current public schema/capability membrane so stale historical
expectations cannot silently become the evidence surface for future owner composition.
"""

from pathlib import Path
from tempfile import TemporaryDirectory

from try_forever_owner_surgery_custody_probe import classify


OWNER = "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
BASE = "c5de1411a6b68087ae17aff83c032af754587150"


def _applied_patch() -> str:
    return (
        "# STATUS: APPLIED_SOURCE\n"
        f"# BASE OWNER BLOB: {BASE}\n"
        f"# OWNER: {OWNER}\n"
        "diff --git a/owner b/owner\n"
    )


def main() -> int:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "try-forever-applied.patch").write_text(_applied_patch(), encoding="utf-8")

        result = classify(root, {OWNER: BASE})
        assert result["schema"] == "try-forever-owner-surgery-custody.v10"
        assert result["artifactKindsScanned"] == ["patch", "delta_json"]
        assert result["artifactCandidatesObserved"] == 1
        assert result["artifactDirectoryEntriesObserved"] == 1
        assert result["evidenceComplete"] is True
        assert result["collisionSets"] == []
        assert result["staleBaseGroups"] == []
        assert result["unverifiedBaseGroups"] == []

        capability = result["capability"]
        expected_true = (
            "sourceInspection",
            "patchArtifactInspection",
            "deltaArtifactInspection",
            "artifactRootIdentityRevalidation",
            "artifactRootFinalRevalidation",
            "exactOwnerSurgeryStateAdmission",
            "nonNormalizingPatchStateHeader",
            "exactCurrentOwnerBlobAdmission",
            "boundedArtifactDirectoryScan",
            "boundedArtifactCandidateSet",
            "boundedArtifactRead",
            "finiteRegularArtifactCustody",
            "currentOwnerCustodyProvided",
        )
        for field in expected_true:
            assert capability[field] is True, field

        expected_false = (
            "substringPromotionAuthority",
            "artifactRootAtomicBinding",
            "patchApplied",
            "ownerWired",
            "regressionExecuted",
            "tested",
            "runtimeUi",
            "runtimeTalkBack",
            "phoneDelivered",
        )
        for field in expected_false:
            assert capability[field] is False, field

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
