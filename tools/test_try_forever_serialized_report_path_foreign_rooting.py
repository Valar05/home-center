#!/usr/bin/env python3
"""SOURCE / UNEXECUTED hostile fixtures for foreign-platform serialized path rooting."""

from pathlib import Path

from try_forever_provenance_report_path import (
    project_repository_relative_report_path,
    project_serialized_report_path,
)


ROOT = Path("/srv/home-center")


def _assert_external(text: str) -> None:
    projection = project_serialized_report_path(ROOT, text)
    assert projection.scope == "EXTERNAL", (text, projection)
    assert projection.display_path == "<external-path>", (text, projection)


def main() -> int:
    for hostile in (
        r"C:\Users\alice\private\receipt.json",
        r"C:private\receipt.json",
        r"\Users\alice\private\receipt.json",
        r"\\server\share\private\receipt.json",
        r"\\?\C:\private\receipt.json",
        "/home/alice/private/receipt.json",
    ):
        _assert_external(hostile)

    # Once repository-relative authority is already established, legal Windows-looking characters
    # remain displayable through the explicit relative channel. The serialized-path gate must not
    # force callers to throw away a legitimate repository identity merely because it contains a colon.
    relative = project_repository_relative_report_path(r"C:literal-name.patch")
    assert relative.scope == "REPOSITORY"
    assert relative.display_path == r"C:literal-name.patch"

    nested = project_serialized_report_path(ROOT, r"patches/C:\literal-name.patch")
    assert nested.scope == "REPOSITORY"
    assert nested.display_path == r"patches/C:\\literal-name.patch"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
