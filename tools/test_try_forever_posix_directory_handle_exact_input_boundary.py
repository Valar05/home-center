#!/usr/bin/env python3
"""RED SOURCE-ONLY boundary for exact caller-input admission in held-directory custody.

This fixture is expected to remain RED until the existing POSIX custody owner is mutated in place.
It proves that callback-capable basename and integer-subclass inputs must fail before their Python
callbacks can participate. Presence of this file is not regression execution or TESTED evidence.
"""

from try_forever_posix_directory_handle_custody import (
    DescriptorArtifactCustodyError,
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


def main() -> int:
    CallbackName.callbacks = 0
    try:
        _require_simple_name(CallbackName("candidate.patch"))
    except DescriptorArtifactCustodyError:
        pass
    else:
        raise AssertionError("candidate basename subclass must fail closed")
    assert CallbackName.callbacks == 0

    source = __import__("inspect").getsource(
        __import__("try_forever_posix_directory_handle_custody")._require_simple_name
    )
    assert "type(name) is not str" in source

    module_source = __import__("inspect").getsource(
        __import__("try_forever_posix_directory_handle_custody")
    )
    assert "def _require_non_negative_budget" in module_source
    assert "type(value) is not int" in module_source
    assert "type(expected_candidate) is not DescriptorCandidate" in module_source
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
