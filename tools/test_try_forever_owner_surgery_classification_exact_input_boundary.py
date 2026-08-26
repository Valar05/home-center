#!/usr/bin/env python3
"""SOURCE-ONLY hostile fixture for canonical owner classification control admission.

The canonical owner must reject callback-capable Path/int subclasses before backend capability
selection, filesystem work, comparison, or truthiness can execute caller code. This fixture is
UNEXECUTED and is not TESTED/runtime/deployment/phone evidence.
"""

from pathlib import Path
from tempfile import TemporaryDirectory

import try_forever_owner_surgery_custody_probe as custody


class HostileInt(int):
    callbacks = 0

    def _hit(self):
        type(self).callbacks += 1
        raise AssertionError("hostile integer callback executed")

    def __lt__(self, other):
        self._hit()

    def __gt__(self, other):
        self._hit()

    def __bool__(self):
        self._hit()


class HostilePath(type(Path())):
    callbacks = 0

    def _hit(self):
        type(self).callbacks += 1
        raise AssertionError("hostile path callback executed")

    def __fspath__(self):
        self._hit()

    def as_posix(self):
        self._hit()

    def __truediv__(self, key):
        self._hit()


def main() -> int:
    capability_calls = 0
    real_capability = custody.current_directory_handle_binding_capability

    def capability_probe():
        nonlocal capability_calls
        capability_calls += 1
        return real_capability()

    custody.current_directory_handle_binding_capability = capability_probe
    try:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)

            HostileInt.callbacks = 0
            try:
                custody.classify(root, max_candidates=HostileInt(1))
            except ValueError as exc:
                assert "max_candidates must be one exact built-in integer" in str(exc)
            else:
                raise AssertionError("hostile max_candidates unexpectedly admitted")
            assert HostileInt.callbacks == 0
            assert capability_calls == 0

            HostileInt.callbacks = 0
            try:
                custody.classify(root, max_entries=HostileInt(1))
            except ValueError as exc:
                assert "max_entries must be one exact built-in integer" in str(exc)
            else:
                raise AssertionError("hostile max_entries unexpectedly admitted")
            assert HostileInt.callbacks == 0
            assert capability_calls == 0

            HostilePath.callbacks = 0
            hostile_root = HostilePath(tmp)
            try:
                custody.classify(hostile_root)
            except ValueError as exc:
                assert "root must be one exact platform Path" in str(exc)
            else:
                raise AssertionError("hostile root unexpectedly admitted")
            assert HostilePath.callbacks == 0
            assert capability_calls == 0
    finally:
        custody.current_directory_handle_binding_capability = real_capability

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
