#!/usr/bin/env python3
"""Deterministically classify Punch-Card Aphorism specs.

Usage:
  python3 tools/punch_card_judge.py spec.json
  cat spec.json | python3 tools/punch_card_judge.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def load_spec() -> dict:
    if len(sys.argv) > 2:
        raise SystemExit("usage: punch_card_judge.py [spec.json]")
    if len(sys.argv) == 2:
        return json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    return json.load(sys.stdin)


def present(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict, set)):
        return bool(value)
    return True


def judge(spec: dict) -> dict:
    phrase = spec.get("phrase")
    gates = {
        "retrieval": present(spec.get("retrieval")),
        "reconstruction": present(spec.get("reconstruction")),
        "execution": present(spec.get("execution")),
        "transfer": present(spec.get("transfer")),
        "correction": present(spec.get("correction")),
    }

    gameplay = spec.get("gameplay") or {}
    gameplay_requested = bool(spec.get("gameplay_required")) or bool(gameplay)
    gameplay_fields = {
        "state": present(gameplay.get("state")),
        "input": present(gameplay.get("input")),
        "rule": present(gameplay.get("rule")),
        "next_state": present(gameplay.get("next_state")),
        "observable": present(gameplay.get("observable")),
        "correction": present(gameplay.get("correction") or spec.get("correction")),
    }

    randomness = gameplay.get("randomness") or {}
    randomness_used = bool(randomness.get("used"))
    randomness_explicit = present(randomness.get("seed_or_input")) if randomness_used else True

    if not present(phrase):
        verdict = "INVALID"
    elif gameplay_requested and not all(gameplay_fields.values()):
        verdict = "GAMEPLAY_LOGIC_INCOMPLETE"
    elif gameplay_requested and not randomness_explicit:
        verdict = "NONDETERMINISTIC_RANDOMNESS"
    elif gameplay_requested and all(gameplay_fields.values()) and all(gates.values()):
        verdict = "EXECUTABLE_GAMEPLAY_CARD"
    elif all(gates.values()):
        verdict = "PUNCH_CARD_READY"
    elif gates["retrieval"] and gates["reconstruction"] and not gates["execution"]:
        verdict = "MNEMONIC_ONLY"
    elif gates["execution"] and not gates["correction"]:
        verdict = "DOGMA_RISK"
    else:
        verdict = "SLOGAN_ONLY"

    return {
        "verdict": verdict,
        "phrase": phrase,
        "gates": gates,
        "gameplay_requested": gameplay_requested,
        "gameplay_fields": gameplay_fields if gameplay_requested else None,
        "randomness_explicit": randomness_explicit if gameplay_requested else None,
    }


def main() -> None:
    result = judge(load_spec())
    json.dump(result, sys.stdout, sort_keys=True, separators=(",", ":"))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
