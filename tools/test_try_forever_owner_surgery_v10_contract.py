#!/usr/bin/env python3
"""Focused SOURCE-ONLY regression for the current owner-surgery custody v10 contract.

The canonical owner now selects either held-descriptor custody or the portable primary path from
exact platform capability. This fixture pins the common evidence membrane plus backend-conditional
root evidence without pretending its presence is regression execution or TESTED/runtime proof.
"""

from pathlib import Path
from tempfile import TemporaryDirectory

from try_forever_owner_surgery_backend_policy import (
    DESCRIPTOR_BACKEND,
    PORTABLE_BACKEND,
)
from try_forever_owner_surgery_custody_probe import (
    MAX_CURRENT_OWNER_ASSIGNMENT_CODEPOINTS,
    MAX_PROGRAMMATIC_ARGV_ITEMS,
    MAX_PROGRAMMATIC_ARG_CODEPOINTS,
    MAX_PROGRAMMATIC_ARGV_TOTAL_CODEPOINTS,
    classify,
)


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
        assert result["backend"] in {DESCRIPTOR_BACKEND, PORTABLE_BACKEND}
        assert result["portableFallbackAttempted"] is False
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
            "sameObservationArtifactContentWitnesses",
            "exactOwnerSurgeryStateAdmission",
            "nonNormalizingPatchStateHeader",
            "exactCurrentOwnerMapAdmission",
            "exactCurrentOwnerBlobAdmission",
            "exactCurrentOwnerCliListAdmission",
            "boundedCurrentOwnerCliAssignmentAdmission",
            "exactProgrammaticArgvAdmission",
            "boundedProgrammaticArgvAdmission",
            "currentOwnerCustodyPresencePreserved",
            "exactClassificationRootAdmission",
            "exactClassificationBudgetAdmission",
            "boundedArtifactDirectoryScan",
            "boundedArtifactCandidateSet",
            "boundedArtifactRead",
            "finiteRegularArtifactCustody",
            "currentOwnerCustodyProvided",
            "ownerWired",
        )
        for field in expected_true:
            assert capability[field] is True, field

        assert capability["currentOwnerCliAssignmentCodepointCeiling"] == (
            MAX_CURRENT_OWNER_ASSIGNMENT_CODEPOINTS
        )
        assert capability["programmaticArgvItemCeiling"] == MAX_PROGRAMMATIC_ARGV_ITEMS
        assert capability["programmaticArgCodepointCeiling"] == MAX_PROGRAMMATIC_ARG_CODEPOINTS
        assert capability["programmaticArgvTotalCodepointCeiling"] == (
            MAX_PROGRAMMATIC_ARGV_TOTAL_CODEPOINTS
        )
        assert capability["selectedBackend"] == result["backend"]
        assert capability["portableFallbackAttempted"] is False
        if result["backend"] == DESCRIPTOR_BACKEND:
            assert capability["descriptorRootCustody"] is True
            assert capability["artifactRootIdentityRevalidation"] is False
            assert capability["artifactRootFinalRevalidation"] is False
        else:
            assert capability["descriptorRootCustody"] is False
            assert capability["artifactRootIdentityRevalidation"] is True
            assert capability["artifactRootFinalRevalidation"] is True

        expected_false = (
            "substringPromotionAuthority",
            "artifactRootAtomicBinding",
            "patchApplied",
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
