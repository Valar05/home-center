#!/usr/bin/env python3
"""SOURCE-ONLY regression for explicit backend-result control presence.

Backend identity and portable-fallback state are authority-bearing machine evidence. Omission must
fail closed rather than being repaired from the selected backend or a default false value. Presence
of this fixture is not regression execution or TESTED evidence.
"""

from try_forever_owner_surgery_backend_policy import (
    DESCRIPTOR_BACKEND,
    SUPPORTED_POSIX,
    admit_selected_backend_result,
    select_owner_surgery_backend,
)


OWNER = "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
BASE = "c5de1411a6b68087ae17aff83c032af754587150"


def complete_result() -> dict[str, object]:
    return {
        "backend": DESCRIPTOR_BACKEND,
        "portableFallbackAttempted": False,
        "artifactDirectoryEntriesObserved": 0,
        "artifactCandidatesObserved": 0,
        "discoveryErrors": [],
        "evidenceComplete": True,
        "currentOwnerBlobs": {OWNER: BASE},
        "collisionSets": [],
        "staleBaseGroups": [],
        "unverifiedBaseGroups": [],
    }


def expect_rejected(result: dict[str, object], needle: str) -> None:
    selection = select_owner_surgery_backend(SUPPORTED_POSIX)
    try:
        admit_selected_backend_result(selection, result)
    except ValueError as exc:
        assert needle in str(exc), (needle, str(exc))
    else:
        raise AssertionError(f"omitted authority-bearing backend control was synthesized: {result!r}")


def main() -> int:
    selection = select_owner_surgery_backend(SUPPORTED_POSIX)
    admitted = admit_selected_backend_result(selection, complete_result())
    assert admitted["backend"] == DESCRIPTOR_BACKEND
    assert admitted["portableFallbackAttempted"] is False

    missing_backend = complete_result()
    missing_backend.pop("backend")
    expect_rejected(missing_backend, "explicitly carry backend identity")

    missing_fallback = complete_result()
    missing_fallback.pop("portableFallbackAttempted")
    expect_rejected(missing_fallback, "explicitly carry portableFallbackAttempted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())