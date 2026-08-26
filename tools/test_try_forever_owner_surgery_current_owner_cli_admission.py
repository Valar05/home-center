#!/usr/bin/env python3
"""Regression source for exact bounded repeated current-owner CLI admission.

SOURCE ONLY. No authorized execution receipt exists for this file.
"""

from try_forever_owner_surgery_custody_probe import (
    MAX_CURRENT_OWNER_ASSIGNMENT_CODEPOINTS,
    _parse_owner_blob,
)


OWNER = "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
BLOB = "a" * 40
OTHER_BLOB = "b" * 40


class CallbackList(list):
    iter_calls = 0

    def __iter__(self):
        type(self).iter_calls += 1
        raise AssertionError("caller-owned list iteration executed before CLI custody admission")


class CallbackString(str):
    partition_calls = 0

    def partition(self, separator):
        type(self).partition_calls += 1
        raise AssertionError("caller-owned partition() executed before scalar custody admission")


def main() -> int:
    assert _parse_owner_blob([f"{OWNER}={BLOB}"]) == {OWNER: BLOB}
    assert _parse_owner_blob([f"{OWNER}={BLOB}", f"{OWNER}={BLOB}"]) == {OWNER: BLOB}

    CallbackList.iter_calls = 0
    try:
        _parse_owner_blob(CallbackList([f"{OWNER}={BLOB}"]))
    except ValueError as exc:
        assert "exact built-in list" in str(exc)
    else:
        raise AssertionError("caller-owned list subclass entered current-owner CLI custody")
    assert CallbackList.iter_calls == 0

    CallbackString.partition_calls = 0
    try:
        _parse_owner_blob([CallbackString(f"{OWNER}={BLOB}")])
    except ValueError as exc:
        assert "exact built-in string" in str(exc)
    else:
        raise AssertionError("caller-owned str subclass entered current-owner CLI custody")
    assert CallbackString.partition_calls == 0

    oversized = ("x" * (MAX_CURRENT_OWNER_ASSIGNMENT_CODEPOINTS + 1))
    try:
        _parse_owner_blob([oversized])
    except ValueError as exc:
        assert "source ceiling" in str(exc)
    else:
        raise AssertionError("max+1 current-owner CLI assignment entered custody")

    for malformed in (
        OWNER,
        f"{OWNER}={'A' * 40}",
        f"{OWNER}={'a' * 39}",
        f"{OWNER}={'a' * 41}",
    ):
        try:
            _parse_owner_blob([malformed])
        except ValueError:
            pass
        else:
            raise AssertionError(f"malformed current-owner CLI evidence entered custody: {malformed!r}")

    try:
        _parse_owner_blob([f"{OWNER}={BLOB}", f"{OWNER}={OTHER_BLOB}"])
    except ValueError as exc:
        assert "conflicting current owner blob" in str(exc)
    else:
        raise AssertionError("conflicting duplicate current-owner evidence entered custody")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
