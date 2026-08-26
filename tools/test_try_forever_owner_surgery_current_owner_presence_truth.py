#!/usr/bin/env python3
"""Regression source for omitted-vs-explicit current-owner custody presence truth.

SOURCE ONLY. No authorized execution receipt exists for this file.
"""

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import try_forever_owner_surgery_custody_probe as custody


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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
