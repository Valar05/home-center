#!/usr/bin/env python3
"""CONVERGENCE SOURCE fixture for direct held-directory root exact-input admission.

Canonical v10 already supplies one exact platform Path. The descriptor organ's direct constructor now
admits only an exact built-in string or the exact platform Path before capability lookup, Path/os.fspath,
or filesystem semantics can execute caller-owned code. Presence is not execution or TESTED evidence.
"""

import try_forever_posix_directory_handle_custody as custody_module
from try_forever_posix_directory_handle_custody import HeldDirectoryCustody


class CallbackPathLike:
    callbacks = 0

    def __fspath__(self) -> str:
        type(self).callbacks += 1
        return "."


class CallbackStr(str):
    callbacks = 0

    def __fspath__(self) -> str:
        type(self).callbacks += 1
        return "."


def _fail_capability():
    raise AssertionError("capability lookup reached before exact root admission")


def _fail_open(*args, **kwargs):
    raise AssertionError("filesystem open reached before exact root admission")


def _require_rejected_without_callbacks(value) -> None:
    CallbackPathLike.callbacks = 0
    CallbackStr.callbacks = 0
    try:
        HeldDirectoryCustody(value)
    except ValueError as exc:
        assert "exact built-in string or exact platform Path" in str(exc)
    else:
        raise AssertionError("non-exact root entered descriptor root custody")
    assert CallbackPathLike.callbacks == 0
    assert CallbackStr.callbacks == 0


def main() -> int:
    original_capability = custody_module.current_directory_handle_binding_capability
    original_open = custody_module.os.open
    try:
        custody_module.current_directory_handle_binding_capability = _fail_capability
        custody_module.os.open = _fail_open
        _require_rejected_without_callbacks(CallbackPathLike())
        _require_rejected_without_callbacks(CallbackStr("."))
    finally:
        custody_module.current_directory_handle_binding_capability = original_capability
        custody_module.os.open = original_open
    return 0


if __name__ == "__main__":
    raise SystemExit(main())