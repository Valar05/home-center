#!/usr/bin/env python3
"""RED source fixture for canonical owner-surgery discovery diagnostic projection.

SOURCE ONLY / UNEXECUTED. Canonical evidence fields remain exact; only the human-facing
DiscoveryError.boundary projection is required to be bounded ASCII-safe. This fixture proves no
runtime, deployment, phone delivery, or P0 capability.
"""

from pathlib import Path

import try_forever_owner_surgery_custody_probe as custody


MAX_BOUNDARY_CODEPOINTS = 320


def _assert_projected(exc: Exception) -> None:
    error = custody._error(
        Path("patches/try-forever-diagnostic-projection.patch"),
        "patch",
        exc,
    )
    boundary = error.boundary
    assert len(boundary) <= MAX_BOUNDARY_CODEPOINTS
    assert all(ord(ch) < 128 for ch in boundary)
    assert "\n" not in boundary
    assert "\r" not in boundary
    assert "\u202e" not in boundary.lower()
    assert "\ud800" not in boundary.lower()


def main() -> int:
    _assert_projected(ValueError("line-one\nline-two"))
    _assert_projected(ValueError("bidi:\u202eattack"))
    _assert_projected(ValueError("surrogate:\ud800"))
    _assert_projected(ValueError("x" * 50_000))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
