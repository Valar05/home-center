#!/usr/bin/env python3
"""Deterministic contract checks for Terminal DMC Anticipation Theorem mode.

These checks prove the experiment is wired correctly. They do not prove the
human-facing theorem. Human play under counterfactual conditions remains the
acceptance surface for behavioral claims.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import terminal_dmc_anticipation as theorem


def set_normal() -> None:
    theorem.COLLAPSE_ANTICIPATION = False
    theorem.PERFECT_REACTION = False
    theorem.TRIAL_LOG = None


def isolated_game() -> tuple[theorem.AnticipationGame, object]:
    game = theorem.AnticipationGame()
    target = game.enemies[1]
    target.distance = 1.45
    target.attack_cooldown = 999
    for enemy in game.enemies:
        if enemy is not target:
            enemy.distance = 5.8
            enemy.attack_cooldown = 999
    return game, target


def resolve(game: theorem.AnticipationGame, limit: int = 80) -> None:
    for _ in range(limit):
        if game.theorem_trials:
            return
        game.step([])
    raise AssertionError("theorem attack did not resolve")


def main() -> int:
    set_normal()

    info = theorem.channel_information()
    bits = info["bits"]
    assert info["strict_order_holds"] is True
    assert bits["I_X_A"] > bits["I_X_R"] > bits["I_X_I"]
    assert bits["I_X_I"] == 0.0

    theorem.COLLAPSE_ANTICIPATION = True
    collapsed = theorem.channel_information()
    assert collapsed["strict_order_holds"] is False
    assert collapsed["bits"]["I_X_A"] == 0.0

    theorem.COLLAPSE_ANTICIPATION = False
    theorem.PERFECT_REACTION = True
    perfect_r = theorem.channel_information()
    assert perfect_r["strict_order_holds"] is False
    assert perfect_r["bits"]["I_X_A"] == perfect_r["bits"]["I_X_R"]

    set_normal()

    # A correct read can occur in anticipation even if the defensive animation
    # later expires. The trial separates inference quality from physical outcome.
    game, target = isolated_game()
    game._start_attack(target, theorem.ATTACK_BY_NAME["FALLING_EDGE"])
    assert target.theorem_phase == "ANTICIPATION"
    game.step([" "])
    resolve(game)
    trial = game.theorem_trials[-1]
    assert trial["first_response"] == "DODGE"
    assert trial["first_response_phase"] == "ANTICIPATION"
    assert trial["response_correct"] is True
    assert trial["anticipation_observation"] == "^"
    assert trial["reaction_observation"] == "ARC"
    assert trial["impact_observation"] == "X"

    # Wait until the compressed reaction channel before answering.
    game2, target2 = isolated_game()
    attack2 = theorem.ATTACK_BY_NAME["LOW_SWEEP"]
    game2._start_attack(target2, attack2)
    for _ in range(attack2.anticipation_frames + attack2.commit_frames):
        game2.step([])
    assert target2.theorem_phase == "REACTION"
    game2.step(["f"])
    resolve(game2)
    trial2 = game2.theorem_trials[-1]
    assert trial2["first_response"] == "BRACE"
    assert trial2["first_response_phase"] == "REACTION"
    assert trial2["response_correct"] is True

    # Offensive initiative closes the remaining counterfactual window instead
    # of pretending the interrupted attack reached impact. Its visual telegraph
    # must retire at the same boundary so the renderer cannot claim the old
    # action window still exists.
    game3, target3 = isolated_game()
    game3._start_attack(target3, theorem.ATTACK_BY_NAME["LINE_THRUST"])
    assert target3.telegraph > 0
    target3.stagger = 2
    game3.step([])
    assert game3.theorem_trials[-1]["outcome"] == "INTERRUPTED_BY_OFFENSE"
    assert target3.theorem_phase == "IDLE"
    assert target3.telegraph == 0

    # The theorem is visible on the playable surface, not hidden in metadata.
    game4, target4 = isolated_game()
    game4._start_attack(target4, theorem.ATTACK_BY_NAME["FALLING_EDGE"])
    frame = theorem.theorem_render(game4, 90, 30)
    assert "ANTICIPATION THEOREM" in frame
    assert "PHASE=ANTICIPATION" in frame
    assert "CUE=^" in frame

    # Behavioral reports preserve phase-specific response evidence without
    # upgrading it into a theorem verdict.
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "trials.jsonl"
        path.write_text(
            "\n".join(json.dumps(row, sort_keys=True) for row in (trial, trial2))
            + "\n",
            encoding="utf-8",
        )
        report = theorem.behavioral_report(path)
        assert report["trial_count"] == 2
        assert report["by_first_response_phase"]["ANTICIPATION"]["correct_rate"] == 1.0
        assert report["by_first_response_phase"]["REACTION"]["correct_rate"] == 1.0
        assert "behavioral support" in report["falsification_note"]

    print(
        json.dumps(
            {
                "schema": "terminal-dmc.anticipation-test.v1",
                "ok": True,
                "proves": [
                    "normal channel encodes I(X;A) > I(X;R) > I(X;I)=0",
                    "collapse-A counterfactual breaks the ordering",
                    "perfect-R counterfactual breaks strict A>R",
                    "responses retain A/R phase and correctness separately from survival",
                    "offensive interruption closes the remaining attack and visual telegraph window",
                    "playable render exposes theorem phase/cue",
                    "behavior report preserves phase-specific human evidence",
                ],
                "does_not_prove": [
                    "the theorem is true for human players",
                    "Drew prefers the resulting combat feel",
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
