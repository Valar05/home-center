#!/usr/bin/env python3
"""RED source boundary for direct programmatic main(argv) exact-container custody.

SOURCE ONLY. This fixture is intentionally RED against the current owner: non-None ``main(argv)``
still materializes arbitrary Iterable input with ``list(argv)`` before exact admission. No authorized
execution receipt exists for this file.
"""

from try_forever_owner_surgery_custody_probe import main as custody_main


class CallbackList(list):
    iter_calls = 0

    def __iter__(self):
        type(self).iter_calls += 1
        raise AssertionError("caller-owned argv iteration executed before programmatic main admission")


def main() -> int:
    CallbackList.iter_calls = 0
    try:
        custody_main(CallbackList([]))
    except ValueError as exc:
        assert "exact built-in list" in str(exc)
    else:
        raise AssertionError("caller-owned argv list subclass entered direct programmatic main")
    assert CallbackList.iter_calls == 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
