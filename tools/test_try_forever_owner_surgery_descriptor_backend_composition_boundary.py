#!/usr/bin/env python3
"""SOURCE-ONLY RED owner-boundary fixture for canonical v10 descriptor-backend composition.

The existing canonical owner must select exactly one custody backend from exact platform capability,
consume HeldDirectoryCustody directly when POSIX descriptor primitives are admitted, preserve the
portable v10 path as the primary backend only when those primitives are unavailable, and never
silently fall back to portable pathname custody after a selected descriptor backend wounds.

This file is intentionally RED until the existing canonical owner is surgically composed. Its
presence is not regression execution, TESTED evidence, runtime evidence, or permission to create a
second authority owner.
"""

import ast
from pathlib import Path


OWNER = Path(__file__).with_name("try_forever_owner_surgery_custody_probe.py")


def _imports(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            names.update(alias.name for alias in node.names)
    return names


def main() -> int:
    source = OWNER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = _imports(tree)

    # Canon Auto-Select / Originality Tax: compose the organs that already exist.
    assert "current_directory_handle_binding_capability" in imported
    assert "select_owner_surgery_backend" in imported
    assert "HeldDirectoryCustody" in imported
    assert "DescriptorArtifactCustodyError" in imported
    assert "DescriptorCustodyCleanupError" in imported
    assert "PosixDirectoryHandleCustodyUnavailable" in imported

    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    classify = functions["classify"]
    classify_source = ast.get_source_segment(source, classify)
    assert classify_source is not None

    # One exact selection decides the owner lane before authority is emitted.
    assert "current_directory_handle_binding_capability(" in classify_source
    assert "select_owner_surgery_backend(" in classify_source
    assert "descriptor_selected" in classify_source

    # Descriptor selection must be consumed by the canonical owner itself, not by a sidecar audit.
    assert "HeldDirectoryCustody(" in source
    assert "candidate_inventory(" in source
    assert "observe_utf8_regular_file(" in source
    assert "parse_owner_surgery_observation(" in source

    # Contact preservation: both canonical evidence counters and authority families survive.
    for token in (
        '"artifactDirectoryEntriesObserved"',
        '"artifactCandidatesObserved"',
        '"discoveryErrors"',
        '"currentOwnerBlobs"',
        '"collisionSets"',
        '"staleBaseGroups"',
        '"unverifiedBaseGroups"',
    ):
        assert token in classify_source

    # Recovery/idempotence: descriptor failure is a stop, never a same-attempt weaker retry.
    assert '"portableFallbackAttempted": False' in classify_source
    assert "fallback_after_backend_failure" not in classify_source or "False" in classify_source

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
