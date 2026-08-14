#!/usr/bin/env python3
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("venice_garden", HERE / "venice_garden.py")
vg = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(vg)


def test_conserve_on_ram_pressure():
    assert vg.choose_mode(90, True, vg.RESERVE_MB - 1, "BLOOM") == "CONSERVE"


def test_conserve_battery_hysteresis():
    assert vg.choose_mode(34, False, vg.RESERVE_MB * 3, "NORMAL") == "CONSERVE"
    assert vg.choose_mode(44, False, vg.RESERVE_MB * 3, "CONSERVE") == "CONSERVE"
    assert vg.choose_mode(45, False, vg.RESERVE_MB * 3, "CONSERVE") == "NORMAL"


def test_bloom_hysteresis():
    assert vg.choose_mode(75, True, vg.RESERVE_MB * 3, "NORMAL") == "BLOOM"
    assert vg.choose_mode(66, True, vg.RESERVE_MB * 3, "BLOOM") == "BLOOM"
    assert vg.choose_mode(64, True, vg.RESERVE_MB * 3, "BLOOM") == "NORMAL"


def test_worker_budget():
    base = dict(battery_percent=80, charging=True, ram_total_mb=32000, ram_available_mb=16000)
    assert vg.worker_budget(vg.Resources(mode="CONSERVE", **base)) == 0
    assert vg.worker_budget(vg.Resources(mode="NORMAL", **base)) == min(1, vg.MAX_WORKERS)
    assert vg.worker_budget(vg.Resources(mode="BLOOM", **base)) == vg.MAX_WORKERS


if __name__ == "__main__":
    for fn in [test_conserve_on_ram_pressure, test_conserve_battery_hysteresis, test_bloom_hysteresis, test_worker_budget]:
        fn()
    print("venice-garden contracts: PASS")
