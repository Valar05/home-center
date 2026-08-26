#!/usr/bin/env python3
"""SOURCE-ONLY convergence fixture for exact caller-input admission in held-directory custody.

Callback-capable basename, integer-budget, and expected-candidate subclasses must fail before their
Python callbacks can participate. Presence of this file is not regression execution or TESTED
evidence.
"""

from try_forever_posix_directory_handle_custody import (
    DescriptorArtifactCustodyError,
    DescriptorCandidate,
    DescriptorIdentity,
    HeldDirectoryCustody,
    _require_non_negative_budget,
    _require_simple_name,
)


class CallbackName(str):
    callbacks = 0

    def __bool__(self) -> bool:
        type(self).callbacks += 1
        return True

    def __hash__(self) -> int:
        type(self).callbacks += 1
        return super().__hash__()

    def __eq__(self, other: object) -> bool:
        type(self).callbacks += 1
        return super().__eq__(other)

    def __contains__(self, item: object) -> bool:
        type(self).callbacks += 1
        return super().__contains__(item)


class CallbackInt(int):
    callbacks = 0

    def __lt__(self, other: object) -> bool:
        type(self).callbacks += 1
        return super().__lt__(other)

    def __gt__(self, other: object) -> bool:
        type(self).callbacks += 1
        return super().__gt__(other)


class CallbackCandidate(DescriptorCandidate):
    callbacks = 0

    def __getattribute__(self, name: str):
        if name in {"name", "identity", "mode"}:
            type(self).callbacks += 1
        return super().__getattribute__(name)


def main() -> int:
    CallbackName.callbacks = 0
    try:
        _require_simple_name(CallbackName("candidate.patch"))
    except DescriptorArtifactCustodyError:
        pass
    else:
        raise AssertionError("candidate basename subclass must fail closed")
    assert CallbackName.callbacks == 0

    CallbackInt.callbacks = 0
    try:
        _require_non_negative_budget(CallbackInt(1), field="budget")
    except ValueError:
        pass
    else:
        raise AssertionError("integer budget subclass must fail closed")
    assert CallbackInt.callbacks == 0

    candidate = CallbackCandidate(
        name="candidate.patch",
        identity=DescriptorIdentity(device=1, inode=1, size=1, mtime_ns=1),
        mode=0,
    )
    CallbackCandidate.callbacks = 0
    custody = object.__new__(HeldDirectoryCustody)
    try:
        custody.observe_utf8_regular_file(
            "candidate.patch",
            max_bytes=0,
            expected_candidate=candidate,
        )
    except DescriptorArtifactCustodyError:
        pass
    else:
        raise AssertionError("DescriptorCandidate subclass must fail closed")
    assert CallbackCandidate.callbacks == 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
