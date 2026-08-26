#!/usr/bin/env python3
"""SOURCE-ONLY convergence fixture for canonical v10 descriptor-backend composition.

The existing canonical owner must select exactly one custody backend from exact platform capability,
consume HeldDirectoryCustody directly when POSIX descriptor primitives are admitted, preserve the
portable v10 path as the primary backend only when those primitives are unavailable, and never
silently fall back to portable pathname custody after a selected descriptor backend wounds.

Classification root/budget controls must also cross exact built-in admission before backend dispatch
or portable comparison work. This file is SOURCE / UNEXECUTED: source convergence is not regression
execution, TESTED evidence, runtime evidence, or permission to create a second authority owner.
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

    # Exact machine controls are admitted before selection or callback-capable comparison work.
    assert "_admit_classification_root(root)" in classify_source
    assert classify_source.count("_admit_classification_budget(") == 2
    root_gate = classify_source.index("_admit_classification_root(root)")
    candidate_gate = classify_source.index("_admit_classification_budget(")
    capability_read = classify_source.index("current_directory_handle_binding_capability(")
    assert root_gate < capability_read
    assert candidate_gate < capability_read

    # One exact selection decides the owner lane before authority is emitted.
    assert "select_owner_surgery_backend(" in classify_source
    assert "descriptor_selected" in classify_source

    # Descriptor selection is consumed by the canonical owner itself, not by a sidecar audit.
    descriptor = functions["_discover_descriptor_surgeries"]
    descriptor_source = ast.get_source_segment(source, descriptor)
    assert descriptor_source is not None
    assert "HeldDirectoryCustody(" in descriptor_source
    assert "candidate_inventory(" in descriptor_source
    assert "observe_utf8_regular_file(" in descriptor_source
    assert "parse_owner_surgery_observation(" in descriptor_source
    for error_name in (
        "PosixDirectoryHandleCustodyUnavailable",
        "DescriptorArtifactCustodyError",
        "DescriptorCustodyCleanupError",
    ):
        assert error_name in descriptor_source

    # Contact preservation: canonical evidence counters, witnesses, and authority families survive.
    for token in (
        '"artifactDirectoryEntriesObserved"',
        '"artifactCandidatesObserved"',
        '"artifactContentWitnesses"',
        '"discoveryErrors"',
        '"currentOwnerBlobs"',
        '"collisionSets"',
        '"staleBaseGroups"',
        '"unverifiedBaseGroups"',
    ):
        assert token in classify_source

    # Recovery/idempotence: descriptor failure is a stop, never a same-attempt weaker retry.
    assert '"portableFallbackAttempted": False' in classify_source
    assert '"descriptorRootCustody": selection.descriptor_selected' in classify_source
    assert '"ownerWired": True' in classify_source

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
