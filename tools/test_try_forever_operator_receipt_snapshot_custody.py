#!/usr/bin/env python3
"""SOURCE / UNEXECUTED regression for one-observation receipt snapshot custody."""

from unittest.mock import patch

from try_forever_operator_receipt_snapshot_custody import (
    OperatorReceiptSnapshotCustodyError,
    snapshot_json_mapping,
    snapshot_verification_inputs,
)


class FalseGetDict(dict):
    """Underlying capability is true while semantic ``get`` tries to present false."""

    def get(self, key, default=None):
        if key == "tested":
            return False
        return super().get(key, default)


def expect_reject(call, fragment: str) -> None:
    try:
        call()
    except OperatorReceiptSnapshotCustodyError as exc:
        assert fragment in str(exc)
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

    # Non-finite, non-JSON, and over-nested encoder failures stay inside the typed custody boundary.
    expect_reject(
        lambda: snapshot_json_mapping({"value": float("nan")}, field="operator receipt"),
        "finite JSON-shaped",
    )
    expect_reject(
        lambda: snapshot_json_mapping({"value": object()}, field="operator receipt"),
        "finite JSON-shaped",
    )
    with patch(
        "try_forever_operator_receipt_snapshot_custody.json.dumps",
        side_effect=RecursionError("hostile nesting"),
    ):
        expect_reject(
            lambda: snapshot_json_mapping({"value": []}, field="operator receipt"),
            "finite JSON-shaped",
        )

    assert captured["oneObservationSnapshot"] is True
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
