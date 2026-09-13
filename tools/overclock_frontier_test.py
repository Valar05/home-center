#!/usr/bin/env python3
"""Regression contract for tools/overclock_frontier.py."""

from overclock_frontier import DIMENSIONS, analyze


def dims(v):
    return {d: v for d in DIMENSIONS}


def outcome(
    oid,
    *,
    lineage=None,
    domain="code",
    disposition="accepted",
    retained=True,
    evidence="verified",
    effort=1.0,
    value=1.0,
    inherits_prior=None,
):
    item = {
        "id": oid,
        "lineage_id": lineage or oid,
        "domain": domain,
        "disposition": disposition,
        "retained_72h": retained,
        "evidence_status": evidence,
        "effort_units": effort,
        "dimensions": dims(value),
    }
    if inherits_prior is not None:
        item["inherits_prior"] = inherits_prior
    return item


def test_commit_burst_does_not_multiply_outcomes():
    result = analyze({
        "windows": [{
            "id": "burst",
            "duration_hours": 0.2,
            "event_count": 11,
            "outcomes": [outcome("artifact", lineage="A")],
        }]
    })
    w = result["windows"][0]
    assert w["event_speed_per_hour"] == 55.0
    assert w["outcome_speed_per_hour"] == 5.0
    assert w["outcome_count"] == 1


def test_inherited_refinement_is_not_waste():
    result = analyze({
        "windows": [{
            "duration_hours": 1,
            "event_count": 10,
            "outcomes": [
                outcome("v1", lineage="A", disposition="superseded", effort=8, inherits_prior=True),
                outcome("v2", lineage="A", disposition="accepted", effort=2),
            ],
        }]
    })
    w = result["windows"][0]
    assert w["outcome_count"] == 1
    assert w["waste_rate"] == 0.0


def test_abandoned_branch_is_waste():
    result = analyze({
        "windows": [{
            "duration_hours": 1,
            "event_count": 2,
            "outcomes": [
                outcome("dead", disposition="discarded", effort=3),
                outcome("live", effort=1),
            ],
        }]
    })
    w = result["windows"][0]
    assert w["waste_rate"] == 0.75


def test_pending_value_uses_delayed_survival_history():
    result = analyze({
        "windows": [
            {
                "duration_hours": 1,
                "event_count": 2,
                "outcomes": [
                    outcome("keep", retained=True),
                    outcome("drop", retained=False),
                ],
            },
            {
                "duration_hours": 1,
                "event_count": 1,
                "outcomes": [
                    outcome("young", retained=None),
                ],
            },
        ]
    })
    # Beta(1,1) + one success + one failure => 0.5 posterior mean.
    assert result["survival_prior"]["posterior_mean"] == 0.5
    young = result["windows"][1]["outcomes"][0]
    assert young["expected_durable_value"] == 0.5


def test_state_uses_value_not_speed_alone():
    result = analyze({
        "windows": [
            {
                "duration_hours": 1,
                "event_count": 4,
                "outcomes": [
                    outcome("a", value=1.0),
                    outcome("b", value=1.0),
                ],
            },
            {
                "duration_hours": 1,
                "event_count": 8,
                "outcomes": [
                    outcome("c", value=0.2),
                    outcome("d", value=0.2),
                    outcome("e", value=0.2),
                ],
            },
        ]
    })
    assert result["current"]["state"]["state"] == "empty_acceleration"


def test_quadratic_frontier_is_recovered():
    # Three matured windows with speeds 1, 2, 3 outcomes/hour and
    # value powers 1.0, 1.6, 1.5. A concave quadratic exists between them.
    result = analyze({
        "windows": [
            {
                "id": "s1",
                "duration_hours": 1,
                "event_count": 2,
                "end_time": "2026-01-01T10:00:00+00:00",
                "outcomes": [outcome("a", value=1.0)],
            },
            {
                "id": "s2",
                "duration_hours": 1,
                "event_count": 4,
                "end_time": "2026-01-01T11:00:00+00:00",
                "outcomes": [
                    outcome("b1", value=0.8),
                    outcome("b2", value=0.8),
                ],
            },
            {
                "id": "s3",
                "duration_hours": 1,
                "event_count": 8,
                "end_time": "2026-01-01T12:00:00+00:00",
                "outcomes": [
                    outcome("c1", value=0.5),
                    outcome("c2", value=0.5),
                    outcome("c3", value=0.5),
                ],
            },
        ]
    })
    frontier = result["current"]["frontier"]
    assert frontier["status"] == "estimated"
    assert 2.0 < frontier["frontier_outcome_speed_per_hour"] < 3.0


def main():
    tests = [
        test_commit_burst_does_not_multiply_outcomes,
        test_inherited_refinement_is_not_waste,
        test_abandoned_branch_is_waste,
        test_pending_value_uses_delayed_survival_history,
        test_state_uses_value_not_speed_alone,
        test_quadratic_frontier_is_recovered,
    ]
    for test in tests:
        test()
    print(f"PASS overclock_frontier_test ({len(tests)} tests)")


if __name__ == "__main__":
    main()
