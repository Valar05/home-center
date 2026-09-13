#!/usr/bin/env python3
"""Overclock Frontier: deterministic speed × durable-value model.

Input is JSON on stdin or via --input PATH.
Output is one JSON document. Standard library only.

This is a productivity/decision instrument, not a medical diagnostic.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

DIMENSIONS = ("utility", "quality", "durability", "leverage", "novelty")
EVIDENCE_MULTIPLIER = {
    "verified": 1.0,
    "provisional": 0.75,
    "failed": 0.0,
}
VALUE_DISPOSITIONS = {"accepted", "pending"}
ALL_DISPOSITIONS = VALUE_DISPOSITIONS | {"discarded", "superseded"}
DEFAULT_WEIGHTS = {name: 1.0 for name in DIMENSIONS}
DEFAULT_TOLERANCE = 0.05


class ModelError(ValueError):
    pass


def _finite_number(value: Any, name: str, *, minimum: Optional[float] = None,
                   maximum: Optional[float] = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ModelError(f"{name} must be a number")
    value = float(value)
    if not math.isfinite(value):
        raise ModelError(f"{name} must be finite")
    if minimum is not None and value < minimum:
        raise ModelError(f"{name} must be >= {minimum}")
    if maximum is not None and value > maximum:
        raise ModelError(f"{name} must be <= {maximum}")
    return value


def _parse_iso8601(value: str, name: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ModelError(f"{name} must be a non-empty ISO-8601 timestamp")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ModelError(f"{name} must be ISO-8601") from exc


def normalized_weights(raw: Optional[Dict[str, Any]]) -> Dict[str, float]:
    source = DEFAULT_WEIGHTS if raw is None else raw
    missing = [d for d in DIMENSIONS if d not in source]
    extra = [d for d in source if d not in DIMENSIONS]
    if missing or extra:
        raise ModelError(f"weights must contain exactly {DIMENSIONS}; missing={missing}, extra={extra}")
    weights = {d: _finite_number(source[d], f"weights.{d}", minimum=0.0) for d in DIMENSIONS}
    total = sum(weights.values())
    if total <= 0:
        raise ModelError("at least one weight must be > 0")
    return {d: weights[d] / total for d in DIMENSIONS}


def beta_survival_prior(windows: Sequence[Dict[str, Any]]) -> Dict[str, float]:
    successes = 0
    failures = 0
    for wi, window in enumerate(windows):
        for oi, outcome in enumerate(window.get("outcomes", [])):
            retained = outcome.get("retained_72h")
            if retained is True:
                successes += 1
            elif retained is False:
                failures += 1
            elif retained is not None:
                raise ModelError(
                    f"windows[{wi}].outcomes[{oi}].retained_72h must be true, false, or null"
                )
    # Laplace/Beta(1,1) smoothing prevents a tiny history from asserting certainty.
    posterior_mean = (successes + 1.0) / (successes + failures + 2.0)
    return {
        "successes": successes,
        "failures": failures,
        "posterior_mean": posterior_mean,
    }


def outcome_base_value(outcome: Dict[str, Any], weights: Dict[str, float], path: str) -> float:
    dims = outcome.get("dimensions")
    if not isinstance(dims, dict):
        raise ModelError(f"{path}.dimensions must be an object")
    missing = [d for d in DIMENSIONS if d not in dims]
    extra = [d for d in dims if d not in DIMENSIONS]
    if missing or extra:
        raise ModelError(f"{path}.dimensions must contain exactly {DIMENSIONS}; missing={missing}, extra={extra}")
    score = 0.0
    for d in DIMENSIONS:
        score += weights[d] * _finite_number(dims[d], f"{path}.dimensions.{d}", minimum=0.0, maximum=1.0)
    evidence = outcome.get("evidence_status", "provisional")
    if evidence not in EVIDENCE_MULTIPLIER:
        raise ModelError(
            f"{path}.evidence_status must be one of {tuple(EVIDENCE_MULTIPLIER)}"
        )
    return score * EVIDENCE_MULTIPLIER[evidence]


def breadth_from_domains(domain_counts: Dict[str, int]) -> float:
    total = sum(domain_counts.values())
    if total <= 0:
        return 0.0
    entropy = 0.0
    for count in domain_counts.values():
        p = count / total
        entropy -= p * math.log(p)
    return math.exp(entropy)


def analyze_window(
    window: Dict[str, Any],
    weights: Dict[str, float],
    survival_prior: float,
    index: int,
) -> Dict[str, Any]:
    wid = str(window.get("id", f"window-{index+1}"))
    hours = _finite_number(window.get("duration_hours"), f"windows[{index}].duration_hours", minimum=1e-9)
    event_count = int(_finite_number(window.get("event_count", 0), f"windows[{index}].event_count", minimum=0))
    if event_count != window.get("event_count", 0):
        # Reject accidental fractions such as 1.5 commits.
        raise ModelError(f"windows[{index}].event_count must be an integer")

    outcomes = window.get("outcomes", [])
    if not isinstance(outcomes, list):
        raise ModelError(f"windows[{index}].outcomes must be an array")

    domain_counts: Dict[str, int] = {}
    value_bearing_lineages = set()
    matured_value = 0.0
    expected_value = 0.0
    immediate_value = 0.0
    pending_value = 0.0
    total_effort = 0.0
    wasted_effort = 0.0
    retained_known = 0
    retained_total = 0
    per_outcome: List[Dict[str, Any]] = []

    for oi, outcome in enumerate(outcomes):
        if not isinstance(outcome, dict):
            raise ModelError(f"windows[{index}].outcomes[{oi}] must be an object")
        path = f"windows[{index}].outcomes[{oi}]"
        oid = str(outcome.get("id", f"{wid}-outcome-{oi+1}"))
        lineage = str(outcome.get("lineage_id", oid))
        disposition = outcome.get("disposition", "pending")
        if disposition not in ALL_DISPOSITIONS:
            raise ModelError(f"{path}.disposition must be one of {tuple(sorted(ALL_DISPOSITIONS))}")
        effort = _finite_number(outcome.get("effort_units", 1.0), f"{path}.effort_units", minimum=0.0)
        total_effort += effort

        base = outcome_base_value(outcome, weights, path)
        retained = outcome.get("retained_72h")
        if retained not in (True, False, None):
            raise ModelError(f"{path}.retained_72h must be true, false, or null")

        if disposition == "discarded":
            wasted_effort += effort
            survival_factor = 0.0
        elif disposition == "superseded":
            inherits = outcome.get("inherits_prior")
            if not isinstance(inherits, bool):
                raise ModelError(f"{path}.inherits_prior must be boolean for superseded outcomes")
            # Inherited supersession is refinement, not waste. It is also not a second outcome.
            if not inherits:
                wasted_effort += effort
            survival_factor = 0.0
        else:
            value_bearing_lineages.add(lineage)
            domain = str(outcome.get("domain", "unknown")).strip() or "unknown"
            domain_counts[domain] = domain_counts.get(domain, 0) + 1

            immediate_value += base
            if retained is True:
                survival_factor = 1.0
                matured_value += base
                retained_known += 1
                retained_total += 1
            elif retained is False:
                survival_factor = 0.0
                retained_known += 1
                retained_total += 1
            else:
                survival_factor = survival_prior
                pending_value += base * survival_factor

            expected_value += base * survival_factor

        per_outcome.append(
            {
                "id": oid,
                "lineage_id": lineage,
                "disposition": disposition,
                "base_value": round(base, 6),
                "survival_factor": round(survival_factor, 6),
                "expected_durable_value": round(base * survival_factor, 6),
            }
        )

    outcome_count = len(value_bearing_lineages)
    event_speed = event_count / hours
    outcome_speed = outcome_count / hours
    value_power = expected_value / hours
    immediate_value_power = immediate_value / hours
    matured_value_power = matured_value / hours
    value_per_outcome = expected_value / outcome_count if outcome_count else 0.0
    value_per_event = expected_value / event_count if event_count else 0.0
    waste_rate = wasted_effort / total_effort if total_effort else 0.0
    breadth = breadth_from_domains(domain_counts)

    end_time = None
    if "end_time" in window and window["end_time"] is not None:
        end_time = _parse_iso8601(window["end_time"], f"windows[{index}].end_time")

    all_value_outcomes_mature = all(
        o.get("retained_72h") is not None
        for o in outcomes
        if o.get("disposition", "pending") in VALUE_DISPOSITIONS
    )

    return {
        "id": wid,
        "duration_hours": hours,
        "end_time": end_time,
        "event_count": event_count,
        "outcome_count": outcome_count,
        "event_speed_per_hour": event_speed,
        "outcome_speed_per_hour": outcome_speed,
        "immediate_value_power_per_hour": immediate_value_power,
        "durable_value_power_per_hour": value_power,
        "matured_value_power_per_hour": matured_value_power,
        "expected_durable_value_sum": expected_value,
        "pending_expected_value_sum": pending_value,
        "value_per_outcome": value_per_outcome,
        "value_per_event": value_per_event,
        "waste_rate": waste_rate,
        "breadth_effective_domains": breadth,
        "matured": all_value_outcomes_mature,
        "retained_known": retained_known,
        "retained_total": retained_total,
        "outcomes": per_outcome,
    }


def _solve_3x3(matrix: Sequence[Sequence[float]], vector: Sequence[float]) -> Optional[Tuple[float, float, float]]:
    # Gaussian elimination with partial pivoting; tiny systems do not justify a dependency.
    a = [list(map(float, row)) + [float(vector[i])] for i, row in enumerate(matrix)]
    for col in range(3):
        pivot = max(range(col, 3), key=lambda r: abs(a[r][col]))
        if abs(a[pivot][col]) < 1e-12:
            return None
        a[col], a[pivot] = a[pivot], a[col]
        p = a[col][col]
        for c in range(col, 4):
            a[col][c] /= p
        for r in range(3):
            if r == col:
                continue
            factor = a[r][col]
            for c in range(col, 4):
                a[r][c] -= factor * a[col][c]
    return (a[0][3], a[1][3], a[2][3])


def fit_quadratic_frontier(windows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    points = [
        (w["outcome_speed_per_hour"], w["durable_value_power_per_hour"])
        for w in windows
        if w["matured"] and w["outcome_count"] > 0
    ]
    unique_speeds = {round(x, 12) for x, _ in points}
    if len(points) < 3 or len(unique_speeds) < 3:
        return {
            "status": "unidentified",
            "reason": "need at least 3 matured windows with 3 distinct outcome speeds",
            "sample_count": len(points),
        }

    n = float(len(points))
    sx = sum(x for x, _ in points)
    sx2 = sum(x*x for x, _ in points)
    sx3 = sum(x*x*x for x, _ in points)
    sx4 = sum(x*x*x*x for x, _ in points)
    sy = sum(y for _, y in points)
    sxy = sum(x*y for x, y in points)
    sx2y = sum(x*x*y for x, y in points)

    # y = a*x^2 + b*x + c
    solved = _solve_3x3(
        ((sx4, sx3, sx2), (sx3, sx2, sx), (sx2, sx, n)),
        (sx2y, sxy, sy),
    )
    if solved is None:
        return {"status": "unidentified", "reason": "quadratic fit is singular", "sample_count": len(points)}
    a, b, c = solved

    if a >= -1e-12:
        return {
            "status": "open",
            "reason": "matured data does not yet show a concave value frontier",
            "sample_count": len(points),
            "quadratic": {"a": a, "b": b, "c": c},
        }

    frontier_speed = -b / (2.0 * a)
    min_speed = min(x for x, _ in points)
    max_speed = max(x for x, _ in points)
    predicted_value = a*frontier_speed*frontier_speed + b*frontier_speed + c
    return {
        "status": "estimated",
        "sample_count": len(points),
        "quadratic": {"a": a, "b": b, "c": c},
        "frontier_outcome_speed_per_hour": frontier_speed,
        "frontier_value_power_per_hour": predicted_value,
        "frontier_inside_observed_speed_range": min_speed <= frontier_speed <= max_speed,
        "observed_speed_range": [min_speed, max_speed],
    }


def classify_state(previous: Optional[Dict[str, Any]], current: Dict[str, Any],
                   tolerance: float) -> Dict[str, Any]:
    if previous is None:
        return {"state": "baseline", "reason": "no previous window"}
    ps = previous["outcome_speed_per_hour"]
    cs = current["outcome_speed_per_hour"]
    pv = previous["durable_value_power_per_hour"]
    cv = current["durable_value_power_per_hour"]

    def change(new: float, old: float) -> int:
        scale = max(abs(old), 1e-9)
        delta = (new - old) / scale
        if delta > tolerance:
            return 1
        if delta < -tolerance:
            return -1
        return 0

    sd = change(cs, ps)
    vd = change(cv, pv)
    if sd > 0 and vd > 0:
        state = "productive_overclock"
    elif sd <= 0 and vd > 0:
        state = "compression"
    elif sd > 0 and vd <= 0:
        state = "empty_acceleration"
    elif sd < 0 and vd < 0:
        state = "loss_of_productive_power"
    else:
        state = "mixed_or_flat"

    return {
        "state": state,
        "speed_delta_fraction": (cs - ps) / max(abs(ps), 1e-9),
        "value_power_delta_fraction": (cv - pv) / max(abs(pv), 1e-9),
    }


def estimate_time_to_frontier(
    windows: Sequence[Dict[str, Any]], frontier: Dict[str, Any]
) -> Dict[str, Any]:
    if frontier.get("status") != "estimated":
        return {"status": "unidentified", "reason": "value frontier is not estimated"}
    current = windows[-1]
    target = frontier["frontier_outcome_speed_per_hour"]
    current_speed = current["outcome_speed_per_hour"]
    if current_speed >= target:
        return {"status": "at_or_beyond_frontier", "hours": 0.0}

    timed = [w for w in windows if w["end_time"] is not None]
    if len(timed) < 2:
        return {"status": "unidentified", "reason": "need end_time on at least 2 windows"}
    prev, curr = timed[-2], timed[-1]
    dt_hours = (curr["end_time"] - prev["end_time"]).total_seconds() / 3600.0
    if dt_hours <= 0:
        return {"status": "unidentified", "reason": "window end_time values must increase"}
    speed_slope = (curr["outcome_speed_per_hour"] - prev["outcome_speed_per_hour"]) / dt_hours
    if speed_slope <= 0:
        return {"status": "not_approaching", "reason": "current outcome speed is not increasing", "speed_slope_per_hour": speed_slope}
    hours = (target - current_speed) / speed_slope
    return {"status": "estimated", "hours": hours, "speed_slope_per_hour": speed_slope}


def analyze(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ModelError("input must be a JSON object")
    windows_raw = payload.get("windows")
    if not isinstance(windows_raw, list) or not windows_raw:
        raise ModelError("windows must be a non-empty array")

    weights = normalized_weights(payload.get("weights"))
    tolerance = _finite_number(
        payload.get("state_tolerance", DEFAULT_TOLERANCE),
        "state_tolerance",
        minimum=0.0,
        maximum=1.0,
    )
    prior = beta_survival_prior(windows_raw)
    windows = [
        analyze_window(window, weights, prior["posterior_mean"], i)
        for i, window in enumerate(windows_raw)
    ]

    state = classify_state(windows[-2] if len(windows) >= 2 else None, windows[-1], tolerance)
    frontier = fit_quadratic_frontier(windows)
    eta = estimate_time_to_frontier(windows, frontier)

    current = windows[-1]
    derivative = None
    if frontier.get("status") == "estimated":
        q = frontier["quadratic"]
        derivative = 2.0*q["a"]*current["outcome_speed_per_hour"] + q["b"]

    def public_window(w: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(w)
        if out["end_time"] is not None:
            out["end_time"] = out["end_time"].isoformat()
        for key, value in list(out.items()):
            if isinstance(value, float):
                out[key] = round(value, 6)
        return out

    return {
        "schema_version": "overclock-frontier.v1",
        "model": {
            "dimensions": list(DIMENSIONS),
            "weights": {k: round(v, 6) for k, v in weights.items()},
            "evidence_multiplier": EVIDENCE_MULTIPLIER,
            "pending_survival_model": "Beta(1,1) posterior mean over known 72h retention",
            "state_tolerance": tolerance,
        },
        "survival_prior": prior,
        "windows": [public_window(w) for w in windows],
        "current": {
            "window_id": current["id"],
            "state": state,
            "marginal_value_power_per_added_outcome_speed": None if derivative is None else round(derivative, 6),
            "frontier": frontier,
            "time_to_frontier": eta,
        },
        "laws": {
            "event_speed_is_not_outcome_speed": True,
            "refinement_is_not_waste_when_inherited": True,
            "young_value_is_expected_not_observed": True,
            "frontier_requires_matured_value": True,
        },
    }


def self_test() -> None:
    # Synthetic concave law: P = -(S-3)^2 + 9 = -S^2 + 6S.
    # Because each accepted outcome has max value 1, use windows whose hours make
    # outcome speed and value power land on the curve exactly.
    payload = {
        "windows": [
            {
                "id": "slow",
                "duration_hours": 1.0,
                "event_count": 5,
                "end_time": "2026-01-01T10:00:00+00:00",
                "outcomes": [
                    {"id": "a", "lineage_id": "a", "domain": "x", "disposition": "accepted",
                     "evidence_status": "verified", "retained_72h": True,
                     "dimensions": {d: 1.0 for d in DIMENSIONS}},
                ],
            },
            {
                "id": "middle",
                "duration_hours": 2/3,
                "event_count": 8,
                "end_time": "2026-01-01T11:00:00+00:00",
                "outcomes": [
                    {"id": f"b{i}", "lineage_id": f"b{i}", "domain": "x", "disposition": "accepted",
                     "evidence_status": "verified", "retained_72h": True,
                     "dimensions": {d: 1.0 for d in DIMENSIONS}}
                    for i in range(2)
                ],
            },
            {
                "id": "fast",
                "duration_hours": 0.75,
                "event_count": 12,
                "end_time": "2026-01-01T12:00:00+00:00",
                "outcomes": [
                    {"id": f"c{i}", "lineage_id": f"c{i}", "domain": "x", "disposition": "accepted",
                     "evidence_status": "verified", "retained_72h": True,
                     "dimensions": {d: 0.75 for d in DIMENSIONS}}
                    for i in range(3)
                ],
            },
        ]
    }
    result = analyze(payload)
    assert result["schema_version"] == "overclock-frontier.v1"
    assert result["windows"][0]["event_speed_per_hour"] == 5.0
    # Inherited supersession must not be penalized as waste.
    payload2 = {
        "windows": [{
            "duration_hours": 1,
            "event_count": 10,
            "outcomes": [
                {"id": "old", "lineage_id": "L", "domain": "code", "disposition": "superseded",
                 "inherits_prior": True, "evidence_status": "verified", "retained_72h": True,
                 "effort_units": 8, "dimensions": {d: 1 for d in DIMENSIONS}},
                {"id": "new", "lineage_id": "L", "domain": "code", "disposition": "accepted",
                 "evidence_status": "verified", "retained_72h": True,
                 "effort_units": 2, "dimensions": {d: 1 for d in DIMENSIONS}},
            ],
        }]
    }
    r2 = analyze(payload2)
    assert r2["windows"][0]["outcome_count"] == 1
    assert r2["windows"][0]["waste_rate"] == 0.0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", help="JSON input path; defaults to stdin")
    parser.add_argument("--self-test", action="store_true", help="run deterministic built-in tests")
    args = parser.parse_args(argv)

    if args.self_test:
        self_test()
        print(json.dumps({"ok": True, "self_test": "passed"}, sort_keys=True))
        return 0

    try:
        if args.input:
            with open(args.input, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
        else:
            payload = json.load(sys.stdin)
        print(json.dumps(analyze(payload), indent=2, sort_keys=True))
        return 0
    except (OSError, json.JSONDecodeError, ModelError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
