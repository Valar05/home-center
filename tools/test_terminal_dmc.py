#!/usr/bin/env python3
"""Deterministic regression contract for the terminal DMC vertical slice."""
from __future__ import annotations

import json

import terminal_dmc as game


def main() -> int:
    launched = game.run_script("w" * 12 + "k")
    target = launched.enemies[1]
    assert target.airborne, target
    assert target.hp == target.max_hp - game.LAUNCHER.damage
    assert launched.last_move == "UPROOT"
    assert launched.combo == 1

    script = "w" * 12 + "j" + "." * 6 + "j" + "." * 7 + "k" + "." * 4 + "j" + "." * 5 + "l"
    combo = game.run_script(script)
    target = combo.enemies[1]
    assert target.hp < target.max_hp - 40
    assert combo.combo >= 5
    assert combo.style >= 200
    assert combo.rank() in {"C", "B", "A", "S", "SS", "SSS"}
    assert combo.last_move == "BURIAL"
    assert target.vy < 0, "airborne heavy must become a downward spike"

    repeat = game.Game()
    repeat._award_style(game.HEAVY)
    first = repeat.style
    repeat._award_style(game.HEAVY)
    second_gain = repeat.style - first
    varied = game.Game()
    varied._award_style(game.HEAVY)
    varied_first = varied.style
    varied._award_style(game.LAUNCHER)
    varied_second_gain = varied.style - varied_first
    assert second_gain < varied_second_gain

    dodge = game.Game()
    for enemy in dodge.enemies[1:]:
        enemy.dead = True
    enemy = dodge.enemies[0]
    enemy.lane = 0
    enemy.distance = 1.4
    enemy.telegraph = 1
    hp = dodge.player_hp
    dodge.step([" "])
    assert dodge.player_hp == hp
    assert any("MISSED" in line for line in dodge.events)

    parry = game.Game()
    for foe in parry.enemies[1:]:
        foe.dead = True
    foe = parry.enemies[0]
    foe.lane = 0
    foe.distance = 1.4
    foe.telegraph = 1
    hp = parry.player_hp
    parry.step(["f"])
    assert parry.player_hp == hp
    assert foe.stagger >= 18
    assert parry.style >= 65
    assert any("PARRIED" in line for line in parry.events)

    gated = game.Game()
    gated.step(["f"])
    first_guard = gated.guard_frames
    gated.step(["f"])
    assert gated.guard_frames < first_guard, "guard spam must not refresh during recovery"
    dodge_gate = game.Game()
    dodge_gate.step([" "])
    first_dodge = dodge_gate.dodge_frames
    dodge_gate.step([" "])
    assert dodge_gate.dodge_frames < first_dodge, "dodge spam must not refresh during recovery"

    frame = game.render(game.Game(), 80, 27)
    assert "DMC TERMINAL // SHOVEL PROOF" in frame
    assert "STYLE" in frame
    assert "TARGET" in frame
    assert "____/__/" in frame or "/___/" in frame

    assert game.lane_screen_x(0, 0, 80) == 40
    assert game.lane_screen_x(0, 1, 80) < 40
    assert game.lane_screen_x(1, 1, 80) == 40

    a = game.run_script(script, settle=8).summary()
    b = game.run_script(script, settle=8).summary()
    assert a == b

    assert game.Game().summary()["schema"] == "terminal-dmc-state.v1"

    print(json.dumps({
        "schema": "terminal-dmc-regression.v1",
        "ok": True,
        "proves": [
            "launcher creates airborne state",
            "ground-launch-juggle-spike grammar executes",
            "style rewards move variety",
            "dodge beats telegraphed strike when timed",
            "shovel brace parries into enemy recovery debt",
            "defensive spam cannot refresh invulnerability windows",
            "renderer exposes target/style/first-person shovel",
            "strafing shifts world lanes in first-person screen space",
            "scripted combat core is deterministic",
        ],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
