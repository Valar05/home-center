#!/usr/bin/env python3
"""Wizard DNS: tiny evidence-first debugging framework.

Stdlib-only. The framework is deliberately small:
- model a debugging case as hypotheses + probes
- choose the cheapest probe that best separates surviving hypotheses
- run probes through registered handlers
- emit receipts
- keep operator-facing output in plain speech

Extend by registering more probe handlers; do not fork the planner.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class Hypothesis:
    name: str
    predicts: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Probe:
    name: str
    kind: str
    args: dict[str, Any] = field(default_factory=dict)
    cost: float = 1.0
    plain: str = ""


@dataclass
class Case:
    name: str
    hypotheses: list[Hypothesis]
    probes: list[Probe]
    observations: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Receipt:
    probe: str
    ok: bool
    value: Any
    elapsed_ms: int
    ts: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "probe": self.probe,
            "ok": self.ok,
            "value": self.value,
            "elapsed_ms": self.elapsed_ms,
            "ts": self.ts,
        }


ProbeHandler = Callable[[dict[str, Any]], Any]
_HANDLERS: dict[str, ProbeHandler] = {}


def register(kind: str) -> Callable[[ProbeHandler], ProbeHandler]:
    """Register a probe kind. This is the framework's extension seam."""
    def deco(fn: ProbeHandler) -> ProbeHandler:
        _HANDLERS[kind] = fn
        return fn
    return deco


@register("shell")
def _shell(args: dict[str, Any]) -> Any:
    cmd = args.get("cmd")
    if not isinstance(cmd, list) or not cmd:
        raise ValueError("shell probe requires args.cmd as a non-empty argv list")
    timeout = float(args.get("timeout", 10))
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    return {
        "returncode": p.returncode,
        "stdout": p.stdout.strip(),
        "stderr": p.stderr.strip(),
    }


@register("file_exists")
def _file_exists(args: dict[str, Any]) -> Any:
    return Path(str(args["path"])).exists()


@register("literal")
def _literal(args: dict[str, Any]) -> Any:
    """Useful for simulation/canaries and externally supplied observations."""
    return args.get("value")


def run_probe(probe: Probe) -> Receipt:
    if probe.kind not in _HANDLERS:
        raise KeyError(f"unknown probe kind: {probe.kind}")
    started = time.perf_counter()
    try:
        value = _HANDLERS[probe.kind](probe.args)
        ok = True
    except Exception as exc:  # receipts include failures; planner keeps moving
        value = {"error": type(exc).__name__, "message": str(exc)}
        ok = False
    return Receipt(
        probe=probe.name,
        ok=ok,
        value=value,
        elapsed_ms=round((time.perf_counter() - started) * 1000),
        ts=time.time(),
    )


def survivors(case: Case) -> list[Hypothesis]:
    """Keep hypotheses not contradicted by current observations.

    Predictions only constrain keys they explicitly mention. This makes the
    framework useful before every probe has a prediction table.
    """
    live: list[Hypothesis] = []
    for h in case.hypotheses:
        contradicted = any(
            key in case.observations and case.observations[key] != expected
            for key, expected in h.predicts.items()
        )
        if not contradicted:
            live.append(h)
    return live


def _separation_score(probe: Probe, hypotheses: list[Hypothesis]) -> float:
    predicted = [h.predicts[probe.name] for h in hypotheses if probe.name in h.predicts]
    if len(predicted) < 2:
        return 0.0
    distinct = len({json.dumps(v, sort_keys=True, default=str) for v in predicted})
    if distinct < 2:
        return 0.0
    coverage = len(predicted) / max(1, len(hypotheses))
    return (distinct * coverage) / max(probe.cost, 0.001)


def choose_probe(case: Case, *, require_separation: bool = False) -> Probe | None:
    """Choose the best remaining probe.

    Normal one-step use remains permissive so partially modeled cases can still
    gather evidence. Stable-loop use is stricter: once no remaining probe can
    separate the surviving hypotheses, return ``None`` instead of burning every
    leftover probe merely because it exists.
    """
    live = survivors(case)
    candidates = [p for p in case.probes if p.name not in case.observations]
    if not candidates:
        return None
    ranked = sorted(
        candidates,
        key=lambda p: (_separation_score(p, live), -p.cost, p.name),
        reverse=True,
    )
    best = ranked[0]
    if require_separation and _separation_score(best, live) <= 0.0:
        return None
    return best


def step(case: Case, *, require_separation: bool = False) -> tuple[Probe | None, Receipt | None]:
    probe = choose_probe(case, require_separation=require_separation)
    if probe is None:
        return None, None
    receipt = run_probe(probe)
    case.observations[probe.name] = receipt.value
    return probe, receipt


def plain_status(case: Case, probe: Probe | None = None, receipt: Receipt | None = None) -> str:
    live = survivors(case)
    if receipt is not None and probe is not None:
        action = probe.plain or f"Checked {probe.name}."
        result = "worked" if receipt.ok else "failed"
        return f"{action} The check {result}. {len(live)} explanation(s) still fit the evidence."
    if len(live) == 1:
        return f"The evidence currently points to: {live[0].name}."
    if not live:
        return "The current evidence contradicts every listed explanation; add or revise a hypothesis."
    return f"{len(live)} explanations still fit the evidence."


def load_case(data: dict[str, Any]) -> Case:
    return Case(
        name=str(data.get("name", "unnamed")),
        hypotheses=[Hypothesis(str(h["name"]), dict(h.get("predicts", {}))) for h in data.get("hypotheses", [])],
        probes=[Probe(str(p["name"]), str(p["kind"]), dict(p.get("args", {})), float(p.get("cost", 1)), str(p.get("plain", ""))) for p in data.get("probes", [])],
        observations=dict(data.get("observations", {})),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Wizard DNS evidence-first debugger")
    ap.add_argument("case", help="JSON case file")
    ap.add_argument("--until-stable", action="store_true", help="keep probing until no useful probe remains")
    ap.add_argument("--receipts", help="append JSONL receipts here")
    ns = ap.parse_args()

    case = load_case(json.loads(Path(ns.case).read_text()))
    while True:
        probe, receipt = step(case, require_separation=ns.until_stable)
        print(plain_status(case, probe, receipt))
        if receipt and ns.receipts:
            with Path(ns.receipts).open("a", encoding="utf-8") as f:
                f.write(json.dumps(receipt.as_dict(), sort_keys=True) + "\n")
        if not ns.until_stable or probe is None:
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
