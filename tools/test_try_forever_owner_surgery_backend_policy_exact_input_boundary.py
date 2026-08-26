#!/usr/bin/env python3
"""Convergence regression source for direct backend-policy exact machine-input admission.

SOURCE ONLY. This fixture has not been observed executing in an authorized test lane. It pins the
source contract that direct backend-policy controls and result evidence are admitted before caller-
owned Python behavior can participate in semantic selection or authority checks.
"""

import inspect

from try_forever_owner_surgery_backend_policy import (
    DESCRIPTOR_BACKEND,
    REQUIRED_OWNER_EVIDENCE_FIELDS,
    SUPPORTED_POSIX,
    OwnerSurgeryBackendSelection,
    admit_selected_backend_result,
    classify_selected_backend_failure,
    select_owner_surgery_backend,
)


OWNER = "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
BASE = "c5de1411a6b68087ae17aff83c032af754587150"


class CallbackDict(dict):
    get_calls = 0
    items_calls = 0

    def get(self, *args, **kwargs):
        type(self).get_calls += 1
        raise AssertionError("direct backend policy executed caller-owned get() before exact admission")

    def items(self):
        type(self).items_calls += 1
        raise AssertionError("direct backend policy executed caller-owned items() before exact admission")


class CapabilityString(str):
    eq_calls = 0

    def __eq__(self, other):
        type(self).eq_calls += 1
        raise AssertionError("backend selection executed caller-owned equality before exact admission")


class FailureBoundaryString(str):
    len_calls = 0

    def __len__(self):
        type(self).len_calls += 1
        raise AssertionError("failure projection executed caller-owned truthiness before exact admission")


class SelectionSubclass(OwnerSurgeryBackendSelection):
    pass


def ordinary_result():
    return {
        "backend": DESCRIPTOR_BACKEND,
        "artifactDirectoryEntriesObserved": 0,
        "artifactCandidatesObserved": 0,
        "discoveryErrors": [],
        "evidenceComplete": True,
        "currentOwnerBlobs": {OWNER: BASE},
        "collisionSets": [],
        "staleBaseGroups": [],
        "unverifiedBaseGroups": [],
        "portableFallbackAttempted": False,
    }


def promotion_candidate(path: str, artifact_kind: object):
    return {
        "owner": OWNER,
        "base_blob": BASE,
        "path": path,
        "artifact_kind": artifact_kind,
        "state": "PROPOSED_NOT_APPLIED",
        "promotion_candidate": True,
    }


def reset_callback_dict() -> None:
    CallbackDict.get_calls = 0
    CallbackDict.items_calls = 0


def expect_exact_dict_rejection(descriptor, result) -> None:
    reset_callback_dict()
    try:
        admit_selected_backend_result(descriptor, result)
    except ValueError as exc:
        assert "exact" in str(exc) and "dict" in str(exc), str(exc)
    else:
        raise AssertionError("direct backend policy accepted callback-capable Python mapping evidence")
    assert CallbackDict.get_calls == 0
    assert CallbackDict.items_calls == 0


def main() -> int:
    descriptor = select_owner_surgery_backend(SUPPORTED_POSIX)

    # Public capability matches runtime admission rather than promising arbitrary Mapping input.
    result_annotation = str(
        inspect.signature(admit_selected_backend_result).parameters["result"].annotation
    )
    assert result_annotation == "dict[str, object]"

    # Ordinary exact evidence preserves the existing semantic result and carries required controls.
    admitted = admit_selected_backend_result(descriptor, ordinary_result())
    assert admitted["backend"] == DESCRIPTOR_BACKEND
    assert admitted["status"] == "EVIDENCE_ADMITTED"
    assert admitted["ownerEvidenceAdmitted"] is True

    # Root caller-owned mappings are rejected before get()/items() can execute.
    expect_exact_dict_rejection(descriptor, CallbackDict(ordinary_result()))

    # Nested caller-owned mappings are equally outside exact JSON evidence custody.
    nested = ordinary_result()
    nested["currentOwnerBlobs"] = CallbackDict({OWNER: BASE})
    expect_exact_dict_rejection(descriptor, nested)

    # Capability selection must reject a str subclass before equality dispatch.
    CapabilityString.eq_calls = 0
    try:
        select_owner_surgery_backend(CapabilityString(SUPPORTED_POSIX))
    except ValueError as exc:
        assert "exact built-in string" in str(exc)
    else:
        raise AssertionError("backend selection accepted a callback-capable string subclass")
    assert CapabilityString.eq_calls == 0

    # Failure projection must not ask caller-owned string truthiness before admission.
    FailureBoundaryString.len_calls = 0
    try:
        classify_selected_backend_failure(
            descriptor,
            FailureBoundaryString("descriptor custody failed"),
        )
    except ValueError as exc:
        assert "exact built-in string" in str(exc)
    else:
        raise AssertionError("failure projection accepted a callback-capable boundary string")
    assert FailureBoundaryString.len_calls == 0

    # The selection object itself is a machine-control record, not an extensible Python protocol.
    subclass_selection = SelectionSubclass(
        backend=descriptor.backend,
        capability_status=descriptor.capability_status,
        descriptor_selected=descriptor.descriptor_selected,
        portable_is_primary=descriptor.portable_is_primary,
        fallback_after_backend_failure=descriptor.fallback_after_backend_failure,
        required_owner_evidence_fields=descriptor.required_owner_evidence_fields,
        boundary=descriptor.boundary,
    )
    try:
        classify_selected_backend_failure(subclass_selection, "descriptor custody failed")
    except ValueError as exc:
        assert "exact OwnerSurgeryBackendSelection" in str(exc)
    else:
        raise AssertionError("failure projection accepted a selection subclass")

    # Even an exact dataclass instance must not smuggle callback-capable fields into control flow.
    CapabilityString.eq_calls = 0
    forged_selection = OwnerSurgeryBackendSelection(
        backend=CapabilityString(descriptor.backend),
        capability_status=descriptor.capability_status,
        descriptor_selected=descriptor.descriptor_selected,
        portable_is_primary=descriptor.portable_is_primary,
        fallback_after_backend_failure=descriptor.fallback_after_backend_failure,
        required_owner_evidence_fields=REQUIRED_OWNER_EVIDENCE_FIELDS,
        boundary=descriptor.boundary,
    )
    try:
        admit_selected_backend_result(forged_selection, ordinary_result())
    except ValueError as exc:
        assert "selection backend must be one exact built-in string" in str(exc)
    else:
        raise AssertionError("direct backend policy accepted a callback-bearing selection field")
    assert CapabilityString.eq_calls == 0

    # JSON-shaped but semantically invalid artifact_kind containers must stay in the typed policy
    # failure domain; a list must never escape as raw unhashable-TypeError evidence.
    malformed_kind = ordinary_result()
    malformed_kind["collisionSets"] = [
        {
            "owner": OWNER,
            "baseBlob": BASE,
            "status": "CURRENT_BASE_COLLISION_SET",
            "currentOwnerBlob": BASE,
            "promotionCandidates": [
                promotion_candidate("patches/try-forever-a.patch", ["patch"]),
                promotion_candidate("patches/try-forever-b.patch", "patch"),
            ],
        }
    ]
    try:
        admit_selected_backend_result(descriptor, malformed_kind)
    except ValueError as exc:
        assert "artifact_kind is unsupported" in str(exc), str(exc)
    except TypeError as exc:
        raise AssertionError("backend policy leaked raw unhashable artifact_kind failure") from exc
    else:
        raise AssertionError("backend policy accepted a non-string artifact_kind container")

    # Ordinary exact failure projection remains behaviorally stable.
    failure = classify_selected_backend_failure(descriptor, "descriptor custody failed")
    assert failure == {
        "backend": DESCRIPTOR_BACKEND,
        "status": "FAIL_CLOSED",
        "boundary": "descriptor custody failed",
        "portableFallbackAttempted": False,
        "ownerEvidenceAdmitted": False,
    }

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
