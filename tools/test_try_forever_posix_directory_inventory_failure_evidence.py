#!/usr/bin/env python3
"""SOURCE / UNEXECUTED regression for bounded descriptor inventory failure evidence.

The descriptor organ must fail closed without returning partial candidate authority, while its typed
inventory wound retains only bounded non-authoritative work counts already observed before failure.
This supporting-organ contract lets canonical v10 preserve receipt evidence without rescanning.
"""

from pathlib import Path

import pytest

from try_forever_directory_handle_binding_capability import (
    current_directory_handle_binding_capability,
)
from try_forever_posix_directory_handle_custody import (
    DescriptorInventoryCustodyError,
    HeldDirectoryCustody,
)


def _require_descriptor_backend() -> None:
    if current_directory_handle_binding_capability().status != "SUPPORTED_POSIX_PRIMITIVES":
        pytest.skip("descriptor backend primitives unavailable on this runtime")


def test_candidate_overflow_carries_bounded_observed_work_without_partial_inventory(tmp_path: Path):
    _require_descriptor_backend()
    root = tmp_path / "patches"
    root.mkdir()
    (root / "try-forever-a.patch").write_text("a", encoding="utf-8")
    (root / "try-forever-b.patch").write_text("b", encoding="utf-8")

    with HeldDirectoryCustody(root) as held:
        with pytest.raises(DescriptorInventoryCustodyError) as raised:
            held.candidate_inventory(
                is_candidate=lambda name: name.endswith(".patch"),
                max_entries=8,
                max_candidates=1,
            )

    error = raised.value
    assert error.entries_observed == 2
    assert error.candidates_observed == 2
    assert "candidate set exceeds 1" in str(error)


def test_entry_overflow_counts_the_observed_max_plus_one_entry(tmp_path: Path):
    _require_descriptor_backend()
    root = tmp_path / "patches"
    root.mkdir()
    (root / "unrelated-a").write_text("a", encoding="utf-8")
    (root / "unrelated-b").write_text("b", encoding="utf-8")

    with HeldDirectoryCustody(root) as held:
        with pytest.raises(DescriptorInventoryCustodyError) as raised:
            held.candidate_inventory(
                is_candidate=lambda name: False,
                max_entries=1,
                max_candidates=8,
            )

    error = raised.value
    assert error.entries_observed == 2
    assert error.candidates_observed == 0
    assert "scan exceeds 1" in str(error)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
