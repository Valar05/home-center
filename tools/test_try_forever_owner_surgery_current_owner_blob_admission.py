#!/usr/bin/env python3
"""Regression source for exact authenticated current-owner blob admission.

SOURCE ONLY. No authorized execution receipt exists for this file.
"""

from try_forever_owner_surgery_custody_probe import _admit_current_owner_blobs


OWNER = "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
BLOB = "a" * 40


class CallbackDict(dict):
    items_calls = 0

    def items(self):
        type(self).items_calls += 1
        raise AssertionError("caller-owned items() callback executed before custody admission")


class BlobSubclass(str):
    pass


def main() -> int:
    admitted = _admit_current_owner_blobs({OWNER: BLOB})
    assert admitted == {OWNER: BLOB}
    assert type(admitted) is dict
    assert type(next(iter(admitted))) is str
    assert type(admitted[OWNER]) is str

    CallbackDict.items_calls = 0
    hostile = CallbackDict({OWNER: BLOB})
    try:
        _admit_current_owner_blobs(hostile)
    except ValueError as exc:
        assert "exact built-in dict" in str(exc)
    else:
        raise AssertionError("caller-owned dict subclass entered current-owner custody")
    assert CallbackDict.items_calls == 0

    try:
        _admit_current_owner_blobs({OWNER: BlobSubclass(BLOB)})
    except ValueError as exc:
        assert "exact built-in" in str(exc)
    else:
        raise AssertionError("str subclass entered authenticated current-owner blob custody")

    for malformed in ("A" * 40, "a" * 39, "a" * 41, " a" + "a" * 39, "a" * 39 + "\n"):
        try:
            _admit_current_owner_blobs({OWNER: malformed})
        except ValueError:
            pass
        else:
            raise AssertionError(f"normalization-dependent blob entered custody: {malformed!r}")

    assert _admit_current_owner_blobs(None) == {}
    assert _admit_current_owner_blobs({}) == {}
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
