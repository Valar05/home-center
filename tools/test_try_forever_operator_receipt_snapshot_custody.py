#!/usr/bin/env python3
"""SOURCE / UNEXECUTED regression for bounded one-observation receipt snapshot custody."""

from try_forever_operator_receipt_snapshot_custody import (
    MAX_SNAPSHOT_NODES,
    MAX_SNAPSHOT_STRING_CODEPOINTS,
    OperatorReceiptSnapshotCustodyError,
    SCHEMA,
    snapshot_json_mapping,
    snapshot_verification_inputs,
)


class FalseGetDict(dict):
    """Underlying capability is true while semantic ``get`` tries to present false."""

    def get(self, key, default=None):
        if key == "tested":
            return False
        return super().get(key, default)


class DuplicateItemsMapping(dict):
    """Hostile Mapping whose items() stream repeats one field despite dict-shaped storage."""

    def items(self):
        yield "schema", "receipt"
        yield "schema", "counterfeit"


def expect_reject(call, fragment: str) -> None:
    try:
        call()
    except OperatorReceiptSnapshotCustodyError as exc:
        assert fragment in str(exc), str(exc)
    else:
        raise AssertionError("hostile snapshot input was admitted")


def main() -> int:
    # A verifier that repeatedly consults the caller-owned Mapping can validate ``tested=false`` and
    # later sign the underlying ``tested=true`` payload. Snapshot custody must capture one view.
    hostile = FalseGetDict({"schema": "receipt", "tested": True, "summary": "stable"})
    assert hostile.get("tested") is False
    snapshot = snapshot_json_mapping(hostile, field="operator receipt")
    assert type(snapshot) is dict
    assert snapshot["tested"] is True

    # Nested caller-owned structure must be detached as part of the same snapshot.
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
        lambda: snapshot_json_mapping(DuplicateItemsMapping(), field="operator receipt"),
        "duplicate mapping field",
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
