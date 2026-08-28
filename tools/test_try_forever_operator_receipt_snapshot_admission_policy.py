#!/usr/bin/env python3
"""SOURCE / UNEXECUTED regression for bounded snapshot admission policy."""

from collections.abc import Mapping

from try_forever_operator_receipt_snapshot_admission_policy import (
    MAX_DIAGNOSTIC_CONTEXT_CODEPOINTS,
    SCHEMA,
    SnapshotAdmissionPolicyError,
    admit_diagnostic_context,
    is_exact_json_object,
    source_capabilities,
)


class ExplosiveItemsDict(dict):
    """A dict subclass whose observation executes caller-owned Python code."""

    def items(self):
        raise AssertionError("arbitrary Mapping callback executed")


class MappingOnly(Mapping):
    def __getitem__(self, key):
        raise KeyError(key)

    def __iter__(self):
        return iter(())

    def __len__(self):
        return 0


def expect_context_reject(value: object, fragment: str) -> None:
    try:
        admit_diagnostic_context(value)
    except SnapshotAdmissionPolicyError as exc:
        assert fragment in str(exc), str(exc)
        return
    raise AssertionError("hostile diagnostic context was admitted")


def main() -> int:
    # Exact built-in dict is the JSON-object container. Subclasses/custom Mapping objects are rejected
    # by type identity alone, so admission itself does not execute their observation callbacks.
    assert is_exact_json_object({"schema": "receipt"}) is True
    hostile = ExplosiveItemsDict({"schema": "receipt"})
    assert is_exact_json_object(hostile) is False
    assert is_exact_json_object(MappingOnly()) is False

    # Diagnostic context is bounded before later escaping/projection and remains exact when admitted.
    exact = "root\n\u202e\ud800"
    assert admit_diagnostic_context(exact) == exact
    at_limit = "x" * MAX_DIAGNOSTIC_CONTEXT_CODEPOINTS
    assert admit_diagnostic_context(at_limit) == at_limit
    expect_context_reject(
        "x" * (MAX_DIAGNOSTIC_CONTEXT_CODEPOINTS + 1),
        "diagnostic context exceeds source ceiling",
    )
    expect_context_reject("", "non-empty exact string")
    expect_context_reject(17, "non-empty exact string")

    capabilities = source_capabilities()
    assert capabilities["schema"] == SCHEMA
    assert capabilities["exactBuiltinObjectAdmission"] is True
    assert capabilities["boundedDiagnosticContextAdmission"] is True
    assert capabilities["ownerWired"] is True
    for field in (
        "regressionExecuted",
        "tested",
        "runtimeUi",
        "runtimeTalkBack",
        "deployed",
        "callable",
        "executed",
        "delivered",
        "accepted",
        "phoneP0MutationAuthority",
    ):
        assert capabilities[field] is False
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
