#!/usr/bin/env python3
"""Intentionally RED source boundary for canonical-result ↔ artifact-content temporal binding.

The current canonical v10 owner does not yet retain same-observation artifact byte/SHA witnesses in
its Surgery records, and descriptor shadow v3 does not yet consume the temporal-binding contract.
This fixture prevents supporting policy existence from being reported as owner integration.

SOURCE ONLY. Expected to remain RED until one deliberate existing-owner composition is reviewed.
"""

import ast
from pathlib import Path


OWNER_PATH = Path("tools/try_forever_owner_surgery_custody_probe.py")
SHADOW_PATH = Path("tools/try_forever_owner_surgery_descriptor_shadow_audit.py")


def dataclass_fields(tree: ast.AST, class_name: str) -> set[str]:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return {
                item.target.id
                for item in node.body
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
            }
    raise AssertionError(f"missing class {class_name}")


def imported_names(tree: ast.AST, module: str) -> set[str]:
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == module:
            result.update(alias.asname or alias.name for alias in node.names)
    return result


def function_names(tree: ast.AST, function_name: str) -> set[str]:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            return {item.id for item in ast.walk(node) if isinstance(item, ast.Name)}
    raise AssertionError(f"missing function {function_name}")


def main() -> int:
    owner_tree = ast.parse(OWNER_PATH.read_text(encoding="utf-8"))
    shadow_tree = ast.parse(SHADOW_PATH.read_text(encoding="utf-8"))

    fields = dataclass_fields(owner_tree, "Surgery")
    assert "artifact_byte_count" in fields, (
        "RED: canonical v10 Surgery must retain byte count from the exact bounded observation that "
        "produced the admitted surgery record"
    )
    assert "artifact_sha256" in fields, (
        "RED: canonical v10 Surgery must retain SHA-256 from the exact bounded observation that "
        "produced the admitted surgery record"
    )

    temporal_imports = imported_names(
        shadow_tree,
        "try_forever_owner_surgery_shadow_temporal_binding",
    )
    assert "evaluate_temporal_content_binding" in temporal_imports, (
        "RED: descriptor shadow must consume the temporal binding contract before it can report a "
        "positive exact-content result"
    )
    audit_names = function_names(shadow_tree, "audit_descriptor_shadow")
    assert "evaluate_temporal_content_binding" in audit_names, (
        "RED: importing temporal policy is not enough; the shadow owner path must use it"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
