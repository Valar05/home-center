#!/usr/bin/env python3
"""Regression source for omitted-vs-explicit current-owner custody presence truth.

SOURCE ONLY / UNEXECUTED. No authorized execution receipt exists for this file. The direct
classification boundary and the CLI adapter must agree that omitted custody is not the same evidence
as an explicitly supplied empty map; CLI absence must not be silently rewritten into explicit-empty.
"""

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import try_forever_owner_surgery_custody_probe as custody


OWNER = "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
BLOB = "a" * 40


def _main_current_owner_argument(argv: list[str]):
    observed: dict[str, object] = {}
    original_classify = custody.classify

    def capture_classify(root, current_owner_blobs):
        observed["root"] = root
        observed["current_owner_blobs"] = current_owner_blobs
        return {"captured": True}

    custody.classify = capture_classify
    try:
        assert custody.main(argv) == 0
    finally:
        custody.classify = original_classify
    return observed["current_owner_blobs"]


def main() -> int:
    original_capability = custody.current_directory_handle_binding_capability
    original_selector = custody.select_owner_surgery_backend
    custody.current_directory_handle_binding_capability = lambda: SimpleNamespace(status="fixture")
    custody.select_owner_surgery_backend = lambda status: SimpleNamespace(
        descriptor_selected=False,
        portable_is_primary=True,
        backend="portable_pathname",
    )

    try:
        with TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            omitted = custody.classify(
                root,
                None,
                max_candidates=0,
                max_entries=0,
            )
            explicit_empty = custody.classify(
                root,
                {},
                max_candidates=0,
                max_entries=0,
            )
    finally:
        custody.current_directory_handle_binding_capability = original_capability
        custody.select_owner_surgery_backend = original_selector

    assert omitted["currentOwnerBlobs"] == {}
    assert explicit_empty["currentOwnerBlobs"] == {}
    assert omitted["capability"]["currentOwnerCustodyProvided"] is False
    assert explicit_empty["capability"]["currentOwnerCustodyProvided"] is True
    assert omitted["capability"]["currentOwnerCustodyPresencePreserved"] is True
    assert explicit_empty["capability"]["currentOwnerCustodyPresencePreserved"] is True

    assert _main_current_owner_argument(["--patch-root", "."]) is None
    assignment = f"{OWNER}={BLOB}"
    assert _main_current_owner_argument(
        ["--patch-root", ".", "--current-owner", assignment]
    ) == {OWNER: BLOB}
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
