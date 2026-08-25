#!/usr/bin/env python3
"""SOURCE / UNEXECUTED regression for bounded one-observation receipt snapshot custody."""

from collections.abc import Mapping

from try_forever_operator_receipt_snapshot_admission_policy import (
    MAX_DIAGNOSTIC_CONTEXT_CODEPOINTS,
)
from try_forever_operator_receipt_snapshot_custody import (
    MAX_DIAGNOSTIC_PATH_CHARS,
    MAX_SNAPSHOT_INTEGER_BITS,
    MAX_SNAPSHOT_NODES,
    MAX_SNAPSHOT_STRING_CODEPOINTS,
    OperatorReceiptSnapshotCustodyError,
    SCHEMA,
    snapshot_json_mapping,
    snapshot_verification_inputs,
)


class FalseGetDict(dict):
    """Dict subclass whose semantic methods disagree with stored evidence."""

    def get(self, key, default=None):
        if key == "tested":
            return False
        return super().get(key, default)

    def items(self):
        raise AssertionError("dict-subclass items() callback executed")


class MappingOnly(Mapping):
    """Custom Mapping whose traversal must never be invoked by exact-object admission."""

    def __getitem__(self, key):
        raise AssertionError("custom Mapping __getitem__ executed")

    def __iter__(self):
        raise AssertionError("custom Mapping __iter__ executed")

    def __len__(self):
        raise AssertionError("custom Mapping __len__ executed")


def rejection_message(call) -> str:
    try:
        call()
    except OperatorReceiptSnapshotCustodyError as exc:
        return str(exc)
    raise AssertionError("hostile snapshot input was admitted")


def expect_reject(call, fragment: str) -> None:
    message = rejection_message(call)
    assert fragment in message, message


def assert_safe_diagnostic(message: str) -> None:
    assert "\n" not in message, repr(message)
    assert "\u202e" not in message, repr(message)
    assert "\ud800" not in message, repr(message)
    assert len(message) <= MAX_DIAGNOSTIC_PATH_CHARS + 192, len(message)


def main() -> int:
    # Caller-owned Mapping behavior is rejected before traversal. A dict subclass can no longer show
    # semantic checks one view and later expose a different payload to the snapshot.
    hostile = FalseGetDict({"schema": "receipt", "tested": True, "summary": "stable"})
    assert hostile.get("tested") is False
    expect_reject(
        lambda: snapshot_json_mapping(hostile, field="operator receipt"),
        "exact built-in dict",
    )
    expect_reject(
        lambda: snapshot_json_mapping(MappingOnly(), field="operator receipt"),
        "exact built-in dict",
    )

    # Plain dict/list source remains detached as one snapshot observation.
    nested = {"status": "before", "items": [{"value": 1}]}
    raw = {"schema": "raw", "nested": nested}
    captured = snapshot_verification_inputs({"schema": "receipt"}, raw)
    nested["status"] = "after"
    nested["items"][0]["value"] = 99
    assert captured["rawMachineEvidence"]["nested"] == {
        "status": "before",
        "items": [{"value": 1}],
    }

    # Hostile Unicode remains exact evidence rather than becoming an encoding crash during custody.
    surrogate = snapshot_json_mapping(
        {"schema": "receipt", "summary": "x\ud800y"},
        field="operator receipt",
    )
    assert surrogate["summary"] == "x\ud800y"

    # Evidence keys remain exact too, but diagnostic paths must reveal hostile layout/direction text
    # safely rather than injecting it literally into an exception/log surface.
    hostile_key = "line\n\u202e\ud800"
    exact_key_snapshot = snapshot_json_mapping(
        {hostile_key: "exact evidence"},
        field="operator receipt",
    )
    assert list(exact_key_snapshot) == [hostile_key]
    diagnostic = rejection_message(
        lambda: snapshot_json_mapping(
            {hostile_key: float("nan")},
            field="operator receipt",
        )
    )
    assert_safe_diagnostic(diagnostic)
    assert "\\n" in diagnostic
    assert "\\u202e" in diagnostic
    assert "\\ud800" in diagnostic.lower()

    # Very long/deep key paths are diagnostic evidence, not a second unbounded resource channel.
    deep_hostile: object = object()
    for index in range(48):
        deep_hostile = {f"segment-{index}-" + ("x" * 72): deep_hostile}
    deep_message = rejection_message(
        lambda: snapshot_json_mapping(deep_hostile, field="operator receipt")
    )
    assert "<path>...#" in deep_message, deep_message
    assert_safe_diagnostic(deep_message)

    # Caller-supplied diagnostic context is bounded before escaping/projection and is never authority.
    hostile_field = "root\n\u202e\ud800" + ("z" * 512)
    root_message = rejection_message(
        lambda: snapshot_json_mapping({"value": object()}, field=hostile_field)
    )
    assert "<text>...#" in root_message, root_message
    assert_safe_diagnostic(root_message)
    expect_reject(
        lambda: snapshot_json_mapping(
            {"schema": "receipt"},
            field="x" * (MAX_DIAGNOSTIC_CONTEXT_CODEPOINTS + 1),
        ),
        "diagnostic context rejected by bounded source admission",
    )

    # A single oversized source key should collapse as a whole diagnostic identity rather than emit an
    # arbitrary partial prefix, while a legal value still keeps the full exact key in the snapshot.
    long_key = ("very-long-key-" * 48) + "\n"
    long_snapshot = snapshot_json_mapping({long_key: "kept"}, field="operator receipt")
    assert list(long_snapshot) == [long_key]
    long_message = rejection_message(
        lambda: snapshot_json_mapping({long_key: float("inf")}, field="operator receipt")
    )
    assert "<text>...#" in long_message, long_message
    assert "very-long-key-very-long-key" not in long_message
    assert_safe_diagnostic(long_message)

    # Exact JSON shape is enforced at every nesting level. Python JSON conveniences must not rewrite
    # evidence identity by stringifying keys or converting tuples into arrays.
    expect_reject(
        lambda: snapshot_json_mapping(
            {"nested": {1: "integer key"}},
            field="operator receipt",
        ),
        "field names must be non-empty strings",
    )
    expect_reject(
        lambda: snapshot_json_mapping(
            {"nested": {"": "empty key"}},
            field="operator receipt",
        ),
        "field names must be non-empty strings",
    )
    expect_reject(
        lambda: snapshot_json_mapping(
            {"items": ("tuple", "is not JSON")},
            field="operator receipt",
        ),
        "exact JSON",
    )
    expect_reject(
        lambda: snapshot_json_mapping(
            {"nested": FalseGetDict({"schema": "counterfeit"})},
            field="operator receipt",
        ),
        "exact JSON",
    )

    # Resource pressure must fail before later semantic/hash/linkage work. These fixtures are large
    # enough to cross the declared budgets but remain bounded enough to run as ordinary regressions.
    expect_reject(
        lambda: snapshot_json_mapping(
            {"text": "x" * (MAX_SNAPSHOT_STRING_CODEPOINTS + 1)},
            field="operator receipt",
        ),
        "snapshot text budget",
    )
    expect_reject(
        lambda: snapshot_json_mapping(
            {"items": list(range(MAX_SNAPSHOT_NODES + 1))},
            field="operator receipt",
        ),
        "snapshot node budget",
    )

    # Large integer conversion is a resource boundary too. A moderate large integer remains ordinary
    # JSON evidence; max+1 bit magnitude must reject before decimal serialization. Do not require the
    # source ceiling itself to serialize successfully because Python can impose a stricter process-wide
    # integer-to-string policy, which is an independent fail-closed boundary.
    ordinary_large_int = (1 << 2_048) - 1
    assert snapshot_json_mapping(
        {"value": ordinary_large_int}, field="operator receipt"
    )["value"] == ordinary_large_int
    expect_reject(
        lambda: snapshot_json_mapping(
            {"value": 1 << MAX_SNAPSHOT_INTEGER_BITS},
            field="operator receipt",
        ),
        "snapshot integer-magnitude budget",
    )

    # Non-finite and non-JSON values stay inside the typed custody boundary.
    expect_reject(
        lambda: snapshot_json_mapping({"value": float("nan")}, field="operator receipt"),
        "finite JSON numbers",
    )
    expect_reject(
        lambda: snapshot_json_mapping({"value": object()}, field="operator receipt"),
        "exact JSON",
    )

    assert captured["schema"] == SCHEMA
    assert captured["oneObservationSnapshot"] is True
    assert captured["boundedSnapshot"] is True
    assert captured["exactJsonShape"] is True
    for field in (
        "authorityAdmitted",
        "ownerMutation",
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
        assert captured[field] is False
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
