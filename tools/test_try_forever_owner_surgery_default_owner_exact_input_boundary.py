#!/usr/bin/env python3
"""SOURCE-ONLY regression for default-owner machine-input exactness.

This file is durable hostile fixture source. Its presence does not mean it has executed or that the
repository is TESTED. It pins the public fallback-owner boundary so caller-owned string subclasses
cannot participate in regex, formatting, equality, or owner authority.
"""

from try_forever_owner_surgery_default_owner_binding import (
    DEFAULT_OWNER,
    DefaultOwnerBindingError,
    admit_default_owner_from_patch,
)


class CallbackString(str):
    callbacks = 0

    def __str__(self) -> str:
        type(self).callbacks += 1
        return super().__str__()

    def __eq__(self, other: object) -> bool:
        type(self).callbacks += 1
        return super().__eq__(other)

    def __hash__(self) -> int:
        type(self).callbacks += 1
        return super().__hash__()


def _patch(owner: str = DEFAULT_OWNER) -> str:
    return f"diff --git a/{owner} b/{owner}\n"


def _must_reject_without_callbacks(*, text: object, default_owner: object = DEFAULT_OWNER) -> None:
    CallbackString.callbacks = 0
    try:
        admit_default_owner_from_patch(text, default_owner=default_owner)  # type: ignore[arg-type]
    except DefaultOwnerBindingError:
        pass
    else:
        raise AssertionError("callback-capable machine evidence must fail closed")
    assert CallbackString.callbacks == 0


def main() -> int:
    admitted = admit_default_owner_from_patch(_patch())
    assert admitted.owner == DEFAULT_OWNER
    assert admitted.exact_diff_header == f"diff --git a/{DEFAULT_OWNER} b/{DEFAULT_OWNER}"

    _must_reject_without_callbacks(text=CallbackString(_patch()))
    _must_reject_without_callbacks(
        text=_patch(),
        default_owner=CallbackString(DEFAULT_OWNER),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
