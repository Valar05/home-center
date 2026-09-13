#!/usr/bin/env python3
"""Playable Anticipation Theorem layer for Terminal DMC.

The theorem is a falsifiable game experiment, not a success label. Enemy attacks
are split into anticipation, commitment/reaction, and impact information. Human
responses are logged separately from physical survival, and counterfactual
switches deliberately break the proposed information ordering.

Normal design assumption:
    I(X;A) > I(X;R) > I(X;I) = 0

X is attack identity, A is the anticipation cue, R is the compressed reaction
cue, and I is the impact cue. No Devil May Cry assets or source data are used.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import terminal_dmc as base


@dataclass(frozen=True)
class AttackProfile:
    name: str
    anticipation_cue: str
    reaction_cue: str
    required_response: str
    anticipation_frames: int
    commit_frames: int
    reaction_frames: int


ATTACKS = (
    AttackProfile("FALLING_EDGE", "^", "ARC", "DODGE", 14, 2, 3),
    AttackProfile("LINE_THRUST", ">", "LINE", "STRAFE", 10, 2, 2),
    AttackProfile("LOW_SWEEP", "_", "ARC", "BRACE", 12, 3, 2),
)
ATTACK_BY_NAME = {attack.name: attack for attack in ATTACKS}

COLLAPSE_ANTICIPATION = False
PERFECT_REACTION = False
TRIAL_LOG: Path | None = None


def anticipation_observation(attack: AttackProfile) -> str:
    return "?" if COLLAPSE_ANTICIPATION else attack.anticipation_cue


def reaction_observation(attack: AttackProfile) -> str:
    return attack.name if PERFECT_REACTION else attack.reaction_cue


def impact_observation(_attack: AttackProfile) -> str:
    # Impact occurs after the action-selection window and carries no attack
    # identity information in the theorem condition.
    return "X"


def mutual_information(pairs: list[tuple[str, str]]) -> float:
    if not pairs:
        return 0.0
    n = len(pairs)
    xs = Counter(x for x, _ in pairs)
    ys = Counter(y for _, y in pairs)
    joint = Counter(pairs)
    result = 0.0
    for (x, y), count in joint.items():
        pxy = count / n
        result += pxy * math.log2(pxy / ((xs[x] / n) * (ys[y] / n)))
    return result


def channel_information() -> dict[str, object]:
    # Equal attack frequency describes channel structure rather than a sample
    # distribution. This is a mechanical contract, not human evidence.
    samples = [attack for attack in ATTACKS for _ in range(120)]
    ia = mutual_information([(x.name, anticipation_observation(x)) for x in samples])
    ir = mutual_information([(x.name, reaction_observation(x)) for x in samples])
    ii = mutual_information([(x.name, impact_observation(x)) for x in samples])
    return {
        "schema": "terminal-dmc.anticipation-channel.v1",
        "condition": {
            "collapse_anticipation": COLLAPSE_ANTICIPATION,
            "perfect_reaction": PERFECT_REACTION,
        },
        "bits": {
            "I_X_A": round(ia, 6),
            "I_X_R": round(ir, 6),
            "I_X_I": round(ii, 6),
        },
        "strict_order_holds": ia > ir > ii and abs(ii) < 1e-12,
        "equation": "I(X;A) > I(X;R) > I(X;I)=0",
        "boundary": "channel structure only; not evidence of human performance",
    }


def response_from_keys(keys: Iterable[str]) -> str | None:
    pressed = set(keys)
    if " " in pressed:
        return "DODGE"
    if "f" in pressed:
        return "BRACE"
    if "a" in pressed or "d" in pressed:
        return "STRAFE"
    return None


def write_trial(trial: dict[str, object]) -> None:
    if TRIAL_LOG is None:
        return
    TRIAL_LOG.parent.mkdir(parents=True, exist_ok=True)
    with TRIAL_LOG.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(trial, sort_keys=True) + "\n")


def load_trials(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    rows: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("schema") == "terminal-dmc.anticipation-trial.v1":
            rows.append(value)
    return rows


def behavioral_report(path: Path) -> dict[str, object]:
    rows = load_trials(path)
    by_phase: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_phase[str(row.get("first_response_phase") or "NONE")].append(row)

    phases: dict[str, object] = {}
    for phase, phase_rows in sorted(by_phase.items()):
        responded = [row for row in phase_rows if row.get("first_response")]
        correct = [row for row in responded if row.get("response_correct") is True]
        latencies = [
            int(row["response_latency_ticks"])
            for row in responded
            if isinstance(row.get("response_latency_ticks"), int)
        ]
        phases[phase] = {
            "trials": len(phase_rows),
            "responses": len(responded),
            "correct": len(correct),
            "correct_rate": round(len(correct) / len(responded), 4) if responded else None,
            "mean_latency_ticks": round(sum(latencies) / len(latencies), 3) if latencies else None,
        }

    return {
        "schema": "terminal-dmc.anticipation-behavior-report.v1",
        "trial_log": str(path),
        "trial_count": len(rows),
        "by_first_response_phase": phases,
        "channel": channel_information(),
        "falsification_note": (
            "The channel inequality is a design condition. Human response accuracy/latency must change "
            "when that condition is manipulated before the theorem earns behavioral support."
        ),
    }


class AnticipationGame(base.Game):
    def __init__(self) -> None:
        super().__init__()
        self.theorem_attack_counter = 0
        self.theorem_trials: list[dict[str, object]] = []
        for enemy in self.enemies:
            self._reset_attack_state(enemy)

    def _reset_attack_state(self, enemy: base.Enemy) -> None:
        enemy.theorem_phase = "IDLE"
        enemy.theorem_phase_ticks = 0
        enemy.theorem_attack = None
        enemy.theorem_started_tick = None
        enemy.theorem_first_response = None
        enemy.theorem_first_response_phase = None
        enemy.theorem_response_tick = None
        # The theorem phase owns the enemy's attack-warning surface. Once a
        # trial ends or is interrupted, no stale base-game telegraph may survive
        # and imply a counterfactual window that no longer exists.
        enemy.telegraph = 0

    def _active_enemy(self) -> base.Enemy | None:
        return next(
            (
                enemy
                for enemy in self.alive_enemies()
                if getattr(enemy, "theorem_phase", "IDLE") != "IDLE"
            ),
            None,
        )

    def _start_attack(self, enemy: base.Enemy, attack: AttackProfile | None = None) -> None:
        attack = attack or ATTACKS[self.theorem_attack_counter % len(ATTACKS)]
        self.theorem_attack_counter += 1
        enemy.theorem_phase = "ANTICIPATION"
        enemy.theorem_phase_ticks = attack.anticipation_frames
        enemy.theorem_attack = attack.name
        enemy.theorem_started_tick = self.tick
        enemy.theorem_first_response = None
        enemy.theorem_first_response_phase = None
        enemy.theorem_response_tick = None
        enemy.telegraph = (
            attack.anticipation_frames + attack.commit_frames + attack.reaction_frames
        )
        self.log(
            f"{enemy.name} // A:{anticipation_observation(attack)} "
            f"({attack.anticipation_frames}f)"
        )

    def _attack_profile(self, enemy: base.Enemy) -> AttackProfile | None:
        return ATTACK_BY_NAME.get(getattr(enemy, "theorem_attack", None))

    def _record_response(self, keys: Iterable[str]) -> None:
        response = response_from_keys(keys)
        if response is None:
            return
        enemy = self._active_enemy()
        if enemy is None or getattr(enemy, "theorem_first_response", None) is not None:
            return
        phase = getattr(enemy, "theorem_phase", "IDLE")
        if phase not in {"ANTICIPATION", "COMMIT", "REACTION"}:
            return
        enemy.theorem_first_response = response
        enemy.theorem_first_response_phase = phase
        enemy.theorem_response_tick = self.tick
        attack = self._attack_profile(enemy)
        if attack:
            verdict = "RIGHT" if response == attack.required_response else "WRONG"
            self.log(f"READ {phase[0]} // {response} // {verdict}")

    def step(self, keys: Iterable[str] = ()) -> None:
        pressed = list(keys)
        self._record_response(pressed)
        super().step(pressed)
        if "r" in pressed:
            self.theorem_attack_counter = 0
            self.theorem_trials = []
            for enemy in self.enemies:
                self._reset_attack_state(enemy)

    def _finish_trial(self, enemy: base.Enemy, outcome: str) -> None:
        attack = self._attack_profile(enemy)
        if attack is None:
            self._reset_attack_state(enemy)
            return
        response = getattr(enemy, "theorem_first_response", None)
        response_phase = getattr(enemy, "theorem_first_response_phase", None)
        response_tick = getattr(enemy, "theorem_response_tick", None)
        started_tick = getattr(enemy, "theorem_started_tick", None)
        trial = {
            "schema": "terminal-dmc.anticipation-trial.v1",
            "at_epoch": int(time.time()),
            "tick": self.tick,
            "enemy": enemy.name,
            "attack": attack.name,
            "anticipation_observation": anticipation_observation(attack),
            "reaction_observation": reaction_observation(attack),
            "impact_observation": impact_observation(attack),
            "required_response": attack.required_response,
            "first_response": response,
            "first_response_phase": response_phase,
            "response_correct": (response == attack.required_response) if response else None,
            "response_latency_ticks": (
                int(response_tick - started_tick)
                if isinstance(response_tick, int) and isinstance(started_tick, int)
                else None
            ),
            "outcome": outcome,
            "condition": {
                "collapse_anticipation": COLLAPSE_ANTICIPATION,
                "perfect_reaction": PERFECT_REACTION,
            },
        }
        self.theorem_trials.append(trial)
        self.theorem_trials[:] = self.theorem_trials[-50:]
        write_trial(trial)
        self._reset_attack_state(enemy)

    def _cancel_trial(self, enemy: base.Enemy, reason: str) -> None:
        if getattr(enemy, "theorem_phase", "IDLE") != "IDLE":
            self._finish_trial(enemy, reason)

    def _tick_enemies(self) -> None:
        active = self._active_enemy()
        for enemy in self.alive_enemies():
            enemy.landed_this_tick = False

            if enemy.airborne:
                enemy.height += enemy.vy
                enemy.vy -= 0.075
                if enemy.height <= 0.0:
                    enemy.height = 0.0
                    enemy.vy = 0.0
                    enemy.landed_this_tick = True
                    enemy.stagger = max(enemy.stagger, 7)
                    self.log(f"{enemy.name} // LANDING DEBT")

            if enemy.stagger > 0:
                # Offensive initiative can erase the opponent's remaining
                # counterfactual window. Interruption is evidence, not impact.
                if getattr(enemy, "theorem_phase", "IDLE") != "IDLE":
                    self._cancel_trial(enemy, "INTERRUPTED_BY_OFFENSE")
                    active = None
                enemy.stagger -= 1
                continue

            phase = getattr(enemy, "theorem_phase", "IDLE")
            if phase != "IDLE":
                attack = self._attack_profile(enemy)
                if attack is None:
                    self._reset_attack_state(enemy)
                    continue
                enemy.theorem_phase_ticks -= 1
                enemy.telegraph = max(0, enemy.telegraph - 1)
                if enemy.theorem_phase_ticks > 0:
                    continue
                if phase == "ANTICIPATION":
                    enemy.theorem_phase = "COMMIT"
                    enemy.theorem_phase_ticks = attack.commit_frames
                    self.log(f"{enemy.name} // COMMIT")
                    continue
                if phase == "COMMIT":
                    enemy.theorem_phase = "REACTION"
                    enemy.theorem_phase_ticks = attack.reaction_frames
                    self.log(f"{enemy.name} // R:{reaction_observation(attack)}")
                    continue
                if phase == "REACTION":
                    self._theorem_impact(enemy, attack)
                    active = None
                    continue

            if enemy.attack_cooldown > 0:
                enemy.attack_cooldown -= 1
            if enemy.airborne:
                continue
            if enemy.distance > 1.75 and self.tick % 5 == 0:
                enemy.distance = max(1.2, enemy.distance - 0.12)
                continue
            if (
                enemy.distance <= 2.0
                and enemy.attack_cooldown <= 0
                and active is None
            ):
                enemy.attack_cooldown = 42
                self._start_attack(enemy)
                active = enemy

    def _theorem_impact(self, enemy: base.Enemy, attack: AttackProfile) -> None:
        response = getattr(enemy, "theorem_first_response", None)
        correct = response == attack.required_response
        same_lane = enemy.lane == self.player_lane
        survived = not same_lane or self.dodge_frames > 0 or self.guard_frames > 0

        if correct:
            self._award_flat_style(45, f"READ {attack.name}")

        # Inference correctness and physical survival are deliberately separate.
        before_hp = self.player_hp
        before_stagger = enemy.stagger
        super()._enemy_strike(enemy)
        if self.player_hp < before_hp:
            outcome = "HIT"
        elif enemy.stagger > before_stagger:
            outcome = "PARRIED"
        elif survived or enemy.lane != self.player_lane:
            outcome = "EVADED"
        else:
            outcome = "MISSED"
        self.log(f"I:{impact_observation(attack)} // {outcome}")
        self._finish_trial(enemy, outcome)

    def summary(self) -> dict[str, object]:
        result = super().summary()
        active = self._active_enemy()
        result["anticipation_theorem"] = {
            "equation": "I(X;A) > I(X;R) > I(X;I)=0",
            "channel": channel_information(),
            "active": (
                {
                    "enemy": active.name,
                    "phase": getattr(active, "theorem_phase", "IDLE"),
                    "attack": getattr(active, "theorem_attack", None),
                }
                if active
                else None
            ),
            "trials": len(self.theorem_trials),
            "recent_trials": list(self.theorem_trials[-5:]),
        }
        return result


_ORIGINAL_ENEMY_SPRITE = base.enemy_sprite
_ORIGINAL_RENDER = base.render


def theorem_enemy_sprite(enemy: base.Enemy) -> list[str]:
    sprite = list(_ORIGINAL_ENEMY_SPRITE(enemy))
    phase = getattr(enemy, "theorem_phase", "IDLE")
    attack = ATTACK_BY_NAME.get(getattr(enemy, "theorem_attack", None))
    if phase == "ANTICIPATION" and attack:
        marker = f"A:{anticipation_observation(attack)}"
    elif phase in {"COMMIT", "REACTION"} and attack:
        marker = "C:!!" if phase == "COMMIT" else f"R:{reaction_observation(attack)}"
    else:
        return sprite
    width = max(len(line) for line in sprite)
    return [marker.center(width)] + sprite


def theorem_render(game: base.Game, width: int = base.WIDTH, height: int = base.HEIGHT) -> str:
    frame = _ORIGINAL_RENDER(game, width, height)
    lines = frame.splitlines()
    if not lines:
        return frame
    lines[0] = ("ANTICIPATION THEOREM // " + lines[0])[: max(64, width)]
    target = game.nearest_target()
    if target is not None and len(lines) > 2:
        phase = getattr(target, "theorem_phase", "IDLE")
        attack = ATTACK_BY_NAME.get(getattr(target, "theorem_attack", None))
        if phase == "ANTICIPATION" and attack:
            cue = anticipation_observation(attack)
        elif phase in {"COMMIT", "REACTION"} and attack:
            cue = "!!" if phase == "COMMIT" else reaction_observation(attack)
        else:
            cue = "-"
        lines[2] = (lines[2] + f"  PHASE={phase} CUE={cue}")[: max(64, width)]
    return "\n".join(lines)


def install_hooks() -> None:
    base.Game = AnticipationGame
    base.enemy_sprite = theorem_enemy_sprite
    base.render = theorem_render


def parse_wrapper(argv: list[str]) -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--collapse-anticipation", action="store_true")
    parser.add_argument("--perfect-reaction", action="store_true")
    parser.add_argument("--theorem-channel-report", action="store_true")
    parser.add_argument("--theorem-behavior-report", action="store_true")
    parser.add_argument("--theorem-log")
    parser.add_argument("--no-theorem-log", action="store_true")
    return parser.parse_known_args(argv)


def configure(args: argparse.Namespace) -> None:
    global COLLAPSE_ANTICIPATION, PERFECT_REACTION, TRIAL_LOG
    COLLAPSE_ANTICIPATION = bool(args.collapse_anticipation)
    PERFECT_REACTION = bool(args.perfect_reaction)
    if args.no_theorem_log:
        TRIAL_LOG = None
    elif args.theorem_log:
        TRIAL_LOG = Path(args.theorem_log).expanduser()
    else:
        state = Path(
            os.environ.get("HC_STATE_DIR", "~/.local/state/home-center")
        ).expanduser()
        condition = (
            "collapse-a"
            if COLLAPSE_ANTICIPATION
            else "perfect-r"
            if PERFECT_REACTION
            else "normal"
        )
        TRIAL_LOG = (
            state
            / "terminal-dmc-campaign"
            / f"anticipation-trials-{condition}.jsonl"
        )


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    wrapper, remaining = parse_wrapper(raw)
    configure(wrapper)

    if wrapper.theorem_channel_report:
        print(json.dumps(channel_information(), indent=2, sort_keys=True))
        return 0
    if wrapper.theorem_behavior_report:
        if TRIAL_LOG is None:
            print(json.dumps({"error": "theorem log disabled"}, sort_keys=True))
            return 2
        print(json.dumps(behavioral_report(TRIAL_LOG), indent=2, sort_keys=True))
        return 0

    install_hooks()
    return base.main(remaining)


if __name__ == "__main__":
    raise SystemExit(main())
