#!/usr/bin/env python3
"""RED regression source for direct backend-policy exact machine-input admission.

SOURCE ONLY. The current backend policy does not satisfy this fixture yet. This file deliberately
preserves the remaining direct-policy wound instead of letting the safer integrity composition make
the whole supporting stack look converged.
"""

from try_forever_owner_surgery_backend_policy import (
    SUPPORTED_POSIX,
    admit_selected_backend_result,
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



def ordinary_result():
    return {
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



def main() -> int:
    descriptor = select_owner_surgery_backend(SUPPORTED_POSIX)

    CallbackDict.get_calls = 0
    CallbackDict.items_calls = 0
    try:
        admit_selected_backend_result(descriptor, CallbackDict(ordinary_result()))
    except ValueError as exc:
        assert "exact built-in dict" in str(exc)
    else:
        raise AssertionError("direct backend policy accepted a callback-capable dict subclass")
    assert CallbackDict.get_calls == 0
    assert CallbackDict.items_calls == 0

    CapabilityString.eq_calls = 0
    try:
        select_owner_surgery_backend(CapabilityString(SUPPORTED_POSIX))
    except ValueError as exc:
        assert "exact built-in string" in str(exc)
    else:
        raise AssertionError("backend selection accepted a callback-capable string subclass")
    assert CapabilityString.eq_calls == 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
