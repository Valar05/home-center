#!/usr/bin/env python3
"""Deterministic daily PI Zodiac calculator.

The configured epoch maps to the first digit of pi, including the integer part:
3, 1, 4, 1, 5, 9, ...

Examples:
  python3 tools/pi_zodiac.py
  python3 tools/pi_zodiac.py --date 2026-09-21 --pretty
  python3 tools/pi_zodiac.py --date 2026-09-21 --config config/pi_zodiac.v1.json
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from decimal import Decimal, getcontext
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config/pi_zodiac.v1.json"


def load_config(path: Path = DEFAULT_CONFIG) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "pi-zodiac.v1":
        raise ValueError(f"unsupported config schema: {data.get('schema')!r}")
    signs = data.get("signs", {})
    if set(signs) != set("0123456789"):
        raise ValueError("config must define exactly signs 0..9")
    return data


def pi_digits(count: int) -> str:
    """Return count digits of pi with the integer digit first and no decimal point."""
    if count <= 0:
        return ""
    getcontext().prec = count + 20
    C = 426880 * Decimal(10005).sqrt()
    M = 1
    L = 13591409
    X = 1
    K = 6
    S = Decimal(L)
    terms = count // 14 + 2
    for i in range(1, terms):
        M = (M * (K**3 - 16 * K)) // (i**3)
        L += 545140134
        X *= -262537412640768000
        S += Decimal(M * L) / Decimal(X)
        K += 12
    value = C / S
    rendered = format(+value, "f").replace(".", "")
    if len(rendered) < count:
        raise RuntimeError("pi precision underflow")
    return rendered[:count]


def local_today(timezone_name: str) -> date:
    return datetime.now(ZoneInfo(timezone_name)).date()


def zodiac_for_date(target: date, config: dict) -> dict:
    epoch = date.fromisoformat(config["epoch_date"])
    offset = (target - epoch).days
    if offset < 0:
        raise ValueError(
            f"date {target.isoformat()} precedes configured PI Zodiac epoch "
            f"{epoch.isoformat()}"
        )
    digits = pi_digits(offset + 1)
    digit = digits[offset]
    sign = config["signs"][digit]
    return {
        "schema": "pi-zodiac.result.v1",
        "date": target.isoformat(),
        "timezone": config["epoch_timezone"],
        "epoch_date": epoch.isoformat(),
        "index": offset,
        "human_position": offset + 1,
        "digit": int(digit),
        "sign": sign["name"],
        "question": sign["question"],
        "hook": sign["hook"],
        "display": f"π[{offset}] = {digit} · {sign['name']}",
        "ceremonial": True,
        "predictive": False,
        "meaning": "symbolic daily routing context; not evidence, fate, probability, or guidance",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="local YYYY-MM-DD; defaults to today in config timezone")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(Path(args.config))
    target = (
        date.fromisoformat(args.date)
        if args.date
        else local_today(config["epoch_timezone"])
    )
    result = zodiac_for_date(target, config)
    if args.pretty:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
