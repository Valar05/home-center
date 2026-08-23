#!/usr/bin/env python3
"""Source-wiring regression for canonical-result ↔ artifact-content temporal binding.

Canonical v10 must retain and emit same-observation artifact byte/SHA witnesses, and descriptor
shadow v3 must consume the temporal-binding contract before reporting positive exact-content
staging. This remains source evidence only; execution, runtime, and delivery are separate states.
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


def function_string_constants(tree: ast.AST, function_name: str) -> set[str]:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            return {
                item.value
                for item in ast.walk(node)
                if isinstance(item, ast.Constant) and isinstance(item.value, str)
            }
    raise AssertionError(f"missing function {function_name}")


def main() -> int:
    owner_tree = ast.parse(OWNER_PATH.read_text(encoding="utf-8"))
    shadow_tree = ast.parse(SHADOW_PATH.read_text(encoding="utf-8"))

    fields = dataclass_fields(owner_tree, "Surgery")
    assert "artifact_byte_count" in fields, (
        "canonical v10 Surgery must retain byte count from the exact bounded observation that "
        "produced the admitted surgery record"
    )
    assert "artifact_sha256" in fields, (
        "canonical v10 Surgery must retain SHA-256 from the exact bounded observation that "
        "produced the admitted surgery record"
    )

    classify_names = function_names(owner_tree, "classify")
    classify_strings = function_string_constants(owner_tree, "classify")
    assert (
        "artifactContentWitnesses" in classify_strings
        or "WITNESS_FIELD" in classify_names
    ), (
        "canonical classify result must emit a dedicated same-observation artifactContentWitnesses "
        "surface rather than leaving retained content identity trapped inside internal records"
    )

    temporal_imports = imported_names(
        shadow_tree,
        "try_forever_owner_surgery_shadow_temporal_binding",
    )
    assert "evaluate_temporal_content_binding" in temporal_imports, (
        "descriptor shadow must import the temporal binding contract before it can report a "
        "positive exact-content result"
    )
    audit_names = function_names(shadow_tree, "audit_descriptor_shadow")
    audit_strings = function_string_constants(shadow_tree, "audit_descriptor_shadow")
    assert "evaluate_temporal_content_binding" in audit_names, (
        "importing temporal policy is not enough; the shadow owner path must use it"
    )
    assert "temporalContentBinding" in audit_strings
    assert "temporalBindingProven" in audit_strings

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
