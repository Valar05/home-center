#!/usr/bin/env python3
"""Owner-boundary regression for descriptor-shadow canonical-result fingerprint custody.

SOURCE ONLY / UNEXECUTED. Authenticated descriptor-shadow owner source now consumes the shared
surrogate-safe fingerprint policy. This fixture preserves that source boundary without promoting it
to regression execution, TESTED, runtime, deployment, or delivery.
"""

import try_forever_owner_surgery_descriptor_shadow_audit as shadow
from try_forever_canonical_result_fingerprint import canonical_result_sha256


def main() -> int:
    hostile = {
        "schema": "try-forever-owner-surgery-custody.v10",
        "artifactDirectoryEntriesObserved": 1,
        "artifactCandidatesObserved": 1,
        "surgeries": [
            {
                "path": "patches/hostile-\udcff.patch",
                "artifact_kind": "patch",
                "owner": "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java",
                "base_blob": "1" * 40,
                "state": "CORRECTED_PROPOSED_NOT_APPLIED",
                "promotion_candidate": True,
            }
        ],
        "discoveryErrors": [],
        "evidenceComplete": True,
        "currentOwnerBlobs": {
            "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java": "1" * 40
        },
        "collisionSets": [],
        "staleBaseGroups": [],
        "unverifiedBaseGroups": [],
    }

    expected = canonical_result_sha256(hostile)
    actual = shadow._canonical_result_sha256(hostile)
    assert actual == expected
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
