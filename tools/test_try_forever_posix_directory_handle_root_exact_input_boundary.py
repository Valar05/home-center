#!/usr/bin/env python3
"""RED SOURCE fixture for direct held-directory root exact-input admission.

The canonical v10 caller already supplies one exact platform Path, but the descriptor organ's direct
constructor currently accepts arbitrary os.PathLike objects and can execute caller-owned __fspath__
before root evidence is admitted. This fixture is deliberately RED until the existing descriptor
owner applies the base-blob-locked root gate. Presence is not execution or TESTED evidence.
"""

from types import SimpleNamespace

import try_forever_posix_directory_handle_custody as custody_module
from try_forever_posix_directory_handle_custody import HeldDirectoryCustody


class CallbackPathLike:
    callbacks = 0

    def __fspath__(self) -> str:
        type(self).callbacks += 1
        return "."


def main() -> int:
    original_capability = custody_module.current_directory_handle_binding_capability
    original_open = custody_module.os.open
    try:
        custody_module.current_directory_handle_binding_capability = lambda: SimpleNamespace(
            status="SUPPORTED_POSIX_PRIMITIVES",
            boundary="fixture capability",
        )
        custody_module.os.open = lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("filesystem open reached before exact root admission")
        )

        CallbackPathLike.callbacks = 0
        try:
            HeldDirectoryCustody(CallbackPathLike())
        except ValueError as exc:
            assert "exact built-in string or exact platform Path" in str(exc)
        else:
            raise AssertionError("arbitrary os.PathLike entered descriptor root custody")
        assert CallbackPathLike.callbacks == 0
    finally:
        custody_module.current_directory_handle_binding_capability = original_capability
        custody_module.os.open = original_open
    return 0


if __name__ == "__main__":
    raise SystemExit(main())