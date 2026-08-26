#!/usr/bin/env python3
"""Source-only convergence boundary for direct programmatic main(argv) custody.

SOURCE ONLY / UNEXECUTED. Canonical v10 now exact-admits and bounds non-None programmatic argv
before argparse may traverse caller evidence. This fixture does not establish TESTED/runtime/device
truth.
"""

from try_forever_owner_surgery_custody_probe import (
    MAX_PROGRAMMATIC_ARGV_ITEMS,
    MAX_PROGRAMMATIC_ARG_CODEPOINTS,
    MAX_PROGRAMMATIC_ARGV_TOTAL_CODEPOINTS,
    _admit_programmatic_argv,
    main as custody_main,
)


class CallbackList(list):
    iter_calls = 0

    def __iter__(self):
        type(self).iter_calls += 1
        raise AssertionError("caller-owned argv iteration executed before programmatic main admission")


class CallbackStr(str):
    len_calls = 0

    def __len__(self):
        type(self).len_calls += 1
        raise AssertionError("caller-owned argv string callback executed before scalar admission")


def main() -> int:
    CallbackList.iter_calls = 0
    try:
        custody_main(CallbackList([]))
    except ValueError as exc:
        assert "exact built-in list" in str(exc)
    else:
        raise AssertionError("caller-owned argv list subclass entered direct programmatic main")
    assert CallbackList.iter_calls == 0

    CallbackStr.len_calls = 0
    try:
        _admit_programmatic_argv([CallbackStr("--help")])
    except ValueError as exc:
        assert "exact built-in strings" in str(exc)
    else:
        raise AssertionError("caller-owned argv string subclass entered bounded argv custody")
    assert CallbackStr.len_calls == 0

    try:
        _admit_programmatic_argv(["x"] * (MAX_PROGRAMMATIC_ARGV_ITEMS + 1))
    except ValueError as exc:
        assert "item ceiling" in str(exc)
    else:
        raise AssertionError("programmatic argv max+1 item count entered argparse custody")

    try:
        _admit_programmatic_argv(["x" * (MAX_PROGRAMMATIC_ARG_CODEPOINTS + 1)])
    except ValueError as exc:
        assert "member exceeds source ceiling" in str(exc)
    else:
        raise AssertionError("programmatic argv max+1 member entered argparse custody")

    chunk = "x" * MAX_PROGRAMMATIC_ARG_CODEPOINTS
    enough_chunks = (MAX_PROGRAMMATIC_ARGV_TOTAL_CODEPOINTS // len(chunk)) + 1
    assert enough_chunks <= MAX_PROGRAMMATIC_ARGV_ITEMS
    try:
        _admit_programmatic_argv([chunk] * enough_chunks)
    except ValueError as exc:
        assert "total source ceiling" in str(exc)
    else:
        raise AssertionError("programmatic argv aggregate max+1 entered argparse custody")

    source = ["--patch-root", "patches"]
    admitted = _admit_programmatic_argv(source)
    assert admitted == source
    assert admitted is not source
    assert type(admitted) is list
    assert all(type(item) is str for item in admitted)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
