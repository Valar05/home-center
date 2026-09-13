#!/usr/bin/env python3
"""DMC-shaped terminal action vertical slice.

Original ASCII presentation and combat implementation. No Devil May Cry assets,
audio, dialogue, or character art are included. The reference is gameplay
grammar: aggressive cancels, launch/juggle, dodge, hit-stop, style variety,
and consequence-heavy recovery.
"""
from __future__ import annotations

import argparse
import json
import os
import select
import sys
import termios
import time
import tty
from dataclasses import dataclass, field
from typing import Iterable

TICK_HZ = 20
DT = 1.0 / TICK_HZ
WIDTH = 80
HEIGHT = 27

STYLE_RANKS = [
    (0, "D"),
    (120, "C"),
    (280, "B"),
    (520, "A"),
    (850, "S"),
    (1250, "SS"),
    (1750, "SSS"),
]


@dataclass(frozen=True)
class Move:
    key: str
    name: str
    damage: int
    style: int
    recovery: int
    cancel: int
    hitstop: int
    reach: float = 2.35
    launch: float = 0.0
    lift: float = 0.0
    slam: bool = False
    knockback: float = 0.0


GROUND_CHAIN = (
    Move("j", "EDGE", 10, 28, 5, 3, 1, knockback=0.10),
    Move("j", "BACKHOE", 12, 36, 6, 3, 1, knockback=0.12),
    Move("j", "GRAVE DRIVER", 20, 62, 10, 4, 3, knockback=0.28),
)
AIR_CLEAVE = Move("j", "AIR CLEAVE", 9, 38, 4, 3, 1, reach=2.6, lift=0.22)
LAUNCHER = Move("k", "UPROOT", 14, 55, 9, 4, 2, reach=2.1, launch=0.68)
HEAVY = Move("l", "HEADSTONE", 24, 70, 12, 3, 3, reach=2.45, knockback=0.45)
SPIKE = Move("l", "BURIAL", 22, 82, 10, 3, 3, reach=2.6, slam=True)


@dataclass
class Enemy:
    name: str
    lane: int
    distance: float
    hp: int = 70
    max_hp: int = 70
    height: float = 0.0
    vy: float = 0.0
    stagger: int = 0
    telegraph: int = 0
    attack_cooldown: int = 24
    dead: bool = False
    landed_this_tick: bool = False

    @property
    def airborne(self) -> bool:
        return self.height > 0.05 or self.vy > 0.02


@dataclass
class Game:
    tick: int = 0
    player_hp: int = 100
    player_lane: int = 0
    dodge_frames: int = 0
    dodge_cooldown: int = 0
    guard_frames: int = 0
    guard_cooldown: int = 0
    last_strafe: int = 1
    recovery: int = 0
    cancel_window: int = 0
    hitstop: int = 0
    chain_index: int = 0
    chain_timer: int = 0
    combo: int = 0
    combo_timer: int = 0
    style: float = 0.0
    style_idle: int = 0
    last_style_move: str = ""
    repeat_count: int = 0
    last_move: str = ""
    pose: str = "IDLE"
    pose_ticks: int = 0
    quit_requested: bool = False
    events: list[str] = field(default_factory=list)
    enemies: list[Enemy] = field(default_factory=lambda: [
        Enemy("CINDER WRETCH", -1, 3.8),
        Enemy("IRON MOUTH", 0, 4.6, hp=90, max_hp=90, attack_cooldown=36),
        Enemy("RAG KNIGHT", 1, 4.1, hp=80, max_hp=80, attack_cooldown=30),
    ])

    def log(self, text: str) -> None:
        self.events.append(text)
        self.events[:] = self.events[-4:]

    def alive_enemies(self) -> list[Enemy]:
        return [enemy for enemy in self.enemies if not enemy.dead]

    def nearest_target(self) -> Enemy | None:
        alive = self.alive_enemies()
        if not alive:
            return None
        same = [e for e in alive if e.lane == self.player_lane]
        pool = same or alive
        return min(pool, key=lambda e: (e.distance, abs(e.lane - self.player_lane)))

    def rank(self) -> str:
        rank = "D"
        for threshold, label in STYLE_RANKS:
            if self.style >= threshold:
                rank = label
        return rank

    def can_act(self) -> bool:
        return self.recovery <= 0 or self.cancel_window > 0

    def step(self, keys: Iterable[str] = ()) -> None:
        pressed = list(keys)
        self.tick += 1

        if "q" in pressed:
            self.quit_requested = True
            return
        if "r" in pressed:
            self.__dict__.update(Game().__dict__)
            self.log("ROOM RESET")
            return

        if self.player_hp <= 0:
            self._tick_timers()
            self._tick_style()
            return

        if self.hitstop > 0:
            self.hitstop -= 1
            self._decay_ui_only()
            return

        self._tick_timers()

        # Movement remains available during most recovery, which keeps the
        # terminal prototype responsive instead of becoming menu combat.
        if "a" in pressed:
            self.player_lane = max(-1, self.player_lane - 1)
            self.last_strafe = -1
        if "d" in pressed:
            self.player_lane = min(1, self.player_lane + 1)
            self.last_strafe = 1
        if "w" in pressed:
            for enemy in self.alive_enemies():
                enemy.distance = max(1.0, enemy.distance - 0.22)
        if "s" in pressed:
            for enemy in self.alive_enemies():
                enemy.distance = min(6.0, enemy.distance + 0.22)

        if " " in pressed and self.can_act() and self.dodge_cooldown <= 0:
            self._dodge()
        if "f" in pressed and self.can_act() and self.guard_cooldown <= 0:
            self._guard()

        for key in pressed:
            if key in ("j", "k", "l") and self.can_act():
                self._attack(key)
                break

        self._tick_enemies()
        self._tick_style()

    def _tick_timers(self) -> None:
        if self.recovery > 0:
            self.recovery -= 1
        if self.cancel_window > 0:
            self.cancel_window -= 1
        if self.dodge_frames > 0:
            self.dodge_frames -= 1
        if self.dodge_cooldown > 0:
            self.dodge_cooldown -= 1
        if self.guard_frames > 0:
            self.guard_frames -= 1
        if self.guard_cooldown > 0:
            self.guard_cooldown -= 1
        if self.chain_timer > 0:
            self.chain_timer -= 1
        else:
            self.chain_index = 0
        if self.combo_timer > 0:
            self.combo_timer -= 1
        elif self.combo:
            self.combo = 0
        if self.pose_ticks > 0:
            self.pose_ticks -= 1
        else:
            self.pose = "IDLE"

    def _decay_ui_only(self) -> None:
        if self.pose_ticks > 0:
            self.pose_ticks -= 1

    def _guard(self) -> None:
        self.guard_frames = 3
        self.guard_cooldown = 10
        self.recovery = max(self.recovery, 8)
        self.pose = "KICKSTAND"
        self.pose_ticks = 6
        self.log("SHOVEL BRACE // support bought with tool")

    def _dodge(self) -> None:
        self.dodge_frames = 4
        self.dodge_cooldown = 8
        self.player_lane = max(-1, min(1, self.player_lane + self.last_strafe))
        self.recovery = max(self.recovery, 6)
        self.pose = "DODGE"
        self.pose_ticks = 5
        self.log("DODGE // lane break")

    def _choose_move(self, key: str, target: Enemy | None) -> Move:
        airborne = bool(target and target.airborne)
        if key == "j":
            if airborne:
                return AIR_CLEAVE
            move = GROUND_CHAIN[self.chain_index % len(GROUND_CHAIN)]
            self.chain_index = (self.chain_index + 1) % len(GROUND_CHAIN)
            self.chain_timer = 14
            return move
        if key == "k":
            return LAUNCHER
        if key == "l":
            return SPIKE if airborne else HEAVY
        raise ValueError(key)

    def _attack(self, key: str) -> None:
        target = self.nearest_target()
        move = self._choose_move(key, target)
        self.pose = move.name
        self.pose_ticks = max(4, move.recovery)
        self.recovery = move.recovery
        self.last_move = move.name

        if not target:
            self.log(f"{move.name} // room already dead")
            return

        in_lane = target.lane == self.player_lane
        in_range = target.distance <= move.reach
        if not (in_lane and in_range):
            self.cancel_window = 0
            self.style_idle += 6
            self.log(f"{move.name} // WHIFF")
            return

        target.hp -= move.damage
        target.stagger = max(target.stagger, move.recovery + 2)
        if move.launch and not target.airborne:
            target.height = max(target.height, 0.18)
            target.vy = move.launch
        elif move.lift and target.airborne:
            target.vy = max(target.vy, move.lift)
            target.height += 0.08
        if move.slam and target.airborne:
            target.vy = -0.92
        if move.knockback:
            target.distance = min(6.0, target.distance + move.knockback)

        self.cancel_window = move.cancel
        self.hitstop = move.hitstop
        self.combo += 1
        self.combo_timer = 34
        self._award_style(move)

        state = "AIR" if target.airborne else "GROUND"
        self.log(f"{move.name}  {move.damage}dmg  [{state}]  x{self.combo}")

        if target.hp <= 0:
            target.hp = 0
            target.dead = True
            self._award_flat_style(120, "EXECUTION")
            self.log(f"{target.name} // DOWN")

    def _award_flat_style(self, amount: float, source: str) -> None:
        self.style += amount
        self.style_idle = 0
        self.log(f"+{int(amount)} STYLE // {source}")

    def _award_style(self, move: Move) -> None:
        if move.name == self.last_style_move:
            self.repeat_count += 1
        else:
            self.repeat_count = 0
        multiplier = max(0.18, 1.0 - 0.26 * self.repeat_count)
        airborne_bonus = 1.22 if "AIR" in move.name or move.slam else 1.0
        gained = move.style * multiplier * airborne_bonus
        self.style += gained
        self.style_idle = 0
        self.last_style_move = move.name

    def _tick_style(self) -> None:
        self.style_idle += 1
        if self.style_idle > 40 and self.style > 0:
            self.style = max(0.0, self.style - 2.4)

    def _tick_enemies(self) -> None:
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
                enemy.stagger -= 1
                continue

            if enemy.telegraph > 0:
                enemy.telegraph -= 1
                if enemy.telegraph == 0:
                    self._enemy_strike(enemy)
                continue

            if enemy.attack_cooldown > 0:
                enemy.attack_cooldown -= 1

            if enemy.airborne:
                continue

            # Enemies spend time earning range rather than teleporting into it.
            if enemy.distance > 1.75 and self.tick % 5 == 0:
                enemy.distance = max(1.2, enemy.distance - 0.12)
                continue

            if enemy.distance <= 2.0 and enemy.attack_cooldown <= 0:
                enemy.telegraph = 11
                enemy.attack_cooldown = 42
                self.log(f"{enemy.name} // WINDUP !")

    def _enemy_strike(self, enemy: Enemy) -> None:
        if enemy.lane == self.player_lane and self.guard_frames > 0:
            enemy.stagger = max(enemy.stagger, 18)
            enemy.distance = min(6.0, enemy.distance + 0.35)
            self.hitstop = max(self.hitstop, 2)
            self.pose = "KICKSTAND"
            self.pose_ticks = 7
            self._award_flat_style(65, "SHOVEL PARRY")
            self.log(f"{enemy.name} // PARRIED INTO DEBT")
            return
        if enemy.lane != self.player_lane or self.dodge_frames > 0:
            self.log(f"{enemy.name} // MISSED")
            return
        self.player_hp = max(0, self.player_hp - 13)
        self.combo = 0
        self.combo_timer = 0
        self.style *= 0.55
        self.recovery = max(self.recovery, 7)
        self.pose = "HURT"
        self.pose_ticks = 7
        self.log(f"{enemy.name} // HIT YOU -13")

    def summary(self) -> dict[str, object]:
        return {
            "schema": "terminal-dmc-state.v1",
            "tick": self.tick,
            "player_hp": self.player_hp,
            "player_lane": self.player_lane,
            "style": round(self.style, 3),
            "rank": self.rank(),
            "combo": self.combo,
            "alive_enemies": sum(not e.dead for e in self.enemies),
            "enemies": [
                {
                    "name": e.name,
                    "hp": e.hp,
                    "lane": e.lane,
                    "distance": round(e.distance, 3),
                    "height": round(e.height, 3),
                    "airborne": e.airborne,
                    "dead": e.dead,
                }
                for e in self.enemies
            ],
            "last_move": self.last_move,
            "events": list(self.events),
        }


def put(canvas: list[list[str]], x: int, y: int, text: str) -> None:
    if y < 0 or y >= len(canvas):
        return
    for i, ch in enumerate(text):
        px = x + i
        if 0 <= px < len(canvas[y]):
            canvas[y][px] = ch


def centered(canvas: list[list[str]], y: int, text: str) -> None:
    put(canvas, max(0, (len(canvas[0]) - len(text)) // 2), y, text)


def enemy_sprite(enemy: Enemy) -> list[str]:
    if enemy.distance > 4.2:
        return [" o ", "/|\\", "/ \\"]
    if enemy.distance > 2.6:
        return ["  O  ", " /#\\ ", "<###>", " / \\ "]
    return [
        "   ___   ",
        "  /O O\\  ",
        " /|###|\\ ",
        "< |###| >",
        "  /| |\\  ",
        " _/   \\_ ",
    ]


def weapon_sprite(pose: str) -> list[str]:
    if pose in {"EDGE", "BACKHOE"}:
        return [
            "                                __",
            "                         _____/ /",
            "                  ______/ ____ / ",
            "             ____/______/ /      ",
            "            /___________/         ",
        ]
    if pose == "GRAVE DRIVER":
        return [
            "       =============================[____]",
            "                    IMPACT  >>>>>>>>>>>   ",
            "                                \\\\        ",
            "                                 \\\\       ",
        ]
    if pose == "UPROOT":
        return [
            "                                /|",
            "                           ____/ |",
            "                      ____/ ___  |",
            "                 ____/_____/  \\__|",
            "                /_____/           ",
        ]
    if pose in {"AIR CLEAVE", "BURIAL"}:
        return [
            "                                  |\\",
            "                                  | \\",
            "                             _____|  \\___",
            "                        ____/___________/",
            "                       /____/            ",
        ]
    if pose == "HEADSTONE":
        return [
            "                            ____________",
            "                      _____/  _________/",
            "                _____/______/           ",
            "               /_____/                  ",
        ]
    if pose == "KICKSTAND":
        return [
            "                                      /|",
            "                                 ____/ |",
            "                            ____/     |",
            "                       ____/          |",
            "______________________/_______________|_",
        ]
    if pose == "DODGE":
        return [
            "                                             __",
            "                                  __________/ /",
            "                        _________/___________/ ",
        ]
    if pose == "HURT":
        return ["                                      //", "                              ____  //", "                         ____/___\\//"]
    return [
        "                                           ___",
        "                                      ____/__/ ",
        "                                 ____/___/     ",
        "                            ____/___/          ",
        "                           /___/               ",
    ]


def lane_screen_x(world_lane: int, player_lane: int, width: int) -> int:
    """Project world lanes into first-person screen space around the player's lane."""
    relative = max(-2, min(2, world_lane - player_lane))
    return {
        -2: 5,
        -1: width // 4,
        0: width // 2,
        1: 3 * width // 4,
        2: width - 6,
    }[relative]


def render(game: Game, width: int = WIDTH, height: int = HEIGHT) -> str:
    width = max(64, width)
    height = max(23, height)
    canvas = [[" "] * width for _ in range(height)]

    rank = game.rank()
    alive = game.alive_enemies()
    title = "DMC TERMINAL // SHOVEL PROOF"
    put(canvas, 1, 0, title)
    put(canvas, 1, 1, f"HP {game.player_hp:3d}   COMBO x{game.combo:<2d}   LANE {game.player_lane:+d}")
    style_bar = "#" * min(20, int(game.style / 90))
    put(canvas, max(1, width - 34), 1, f"STYLE {rank:>3} [{style_bar:<20}]")

    target = game.nearest_target()
    if target:
        put(
            canvas,
            1,
            2,
            f"TARGET {target.name:<14} HP {target.hp:>3}/{target.max_hp:<3}  z={target.distance:0.1f}"
            + (f"  AIR={target.height:0.1f}" if target.airborne else ""),
        )
    else:
        put(canvas, 1, 2, "TARGET -- ROOM CLEARED --")

    horizon = 7
    put(canvas, 0, horizon, "." * width)
    centered(canvas, horizon - 1, "V")
    floor_bottom = height - 7
    for y in range(horizon + 1, floor_bottom):
        spread = max(2, int((y - horizon) * 1.7))
        cx = width // 2
        for x in (cx - spread, cx, cx + spread):
            if 0 <= x < width:
                canvas[y][x] = "|" if x == cx else ("/" if x < cx else "\\")
    for y in (horizon + 3, horizon + 7, floor_bottom - 1):
        if y < floor_bottom:
            inset = max(0, int((floor_bottom - y) * 1.5))
            put(canvas, inset, y, "-" * max(0, width - inset * 2))

    for enemy in alive:
        sprite = enemy_sprite(enemy)
        sx = lane_screen_x(enemy.lane, game.player_lane, width)
        x = sx - len(sprite[0]) // 2
        base_y = floor_bottom - max(1, int((6.2 - min(6.0, enemy.distance)) * 1.2))
        base_y -= int(enemy.height * 3.0)
        top = base_y - len(sprite) + 1
        if enemy.telegraph:
            put(canvas, sx - 1, top - 1, "!!!")
        for i, line in enumerate(sprite):
            put(canvas, x, top + i, line)
        hp_width = 9
        filled = max(0, min(hp_width, int(hp_width * enemy.hp / enemy.max_hp)))
        put(canvas, sx - 5, base_y + 1, "[" + "#" * filled + "." * (hp_width - filled) + "]")

    if game.hitstop > 0:
        centered(canvas, horizon + 2, "*** HIT-STOP ***")

    weapon = weapon_sprite(game.pose)
    wy = height - len(weapon) - 2
    for i, line in enumerate(weapon):
        put(canvas, max(0, width - len(line) - 1), wy + i, line)

    help_text = "A/D strafe  W/S range  J combo  K launcher  L heavy/spike  F brace  SPACE dodge  R reset  Q quit"
    put(canvas, 1, height - 2, help_text[: width - 2])
    event = " | ".join(game.events[-2:]) if game.events else "Move. Earn range. Make the hit mean something."
    put(canvas, 1, height - 1, event[: width - 2])

    if game.player_hp <= 0:
        centered(canvas, height // 2, "YOU ARE FLOOR GEOMETRY.  [R] RESET")
    elif not alive:
        centered(canvas, height // 2, f"ROOM CLEARED // STYLE {rank} // [R] AGAIN")

    return "\n".join("".join(row).rstrip() for row in canvas)


class RawTerminal:
    def __init__(self) -> None:
        self.fd = sys.stdin.fileno()
        self.old: list[object] | None = None

    def __enter__(self) -> "RawTerminal":
        self.old = termios.tcgetattr(self.fd)
        tty.setcbreak(self.fd)
        sys.stdout.write("\x1b[?1049h\x1b[?25l\x1b[2J\x1b[H")
        sys.stdout.flush()
        return self

    def read(self) -> list[str]:
        keys: list[str] = []
        while True:
            ready, _, _ = select.select([self.fd], [], [], 0)
            if not ready:
                break
            data = os.read(self.fd, 32)
            if not data:
                break
            text = data.decode("utf-8", errors="ignore")
            # Arrow keys are optional aliases for WASD.
            text = text.replace("\x1b[D", "a").replace("\x1b[C", "d")
            text = text.replace("\x1b[A", "w").replace("\x1b[B", "s")
            keys.extend(ch.lower() for ch in text if ch.lower() in "adwsjklfrq ")
        return keys

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.old is not None:
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old)
        sys.stdout.write("\x1b[?25h\x1b[?1049l")
        sys.stdout.flush()


def play_interactive() -> int:
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        print("Interactive mode requires a TTY. Use --turn or --script.", file=sys.stderr)
        return 2

    game = Game()
    with RawTerminal() as term:
        next_tick = time.monotonic()
        while not game.quit_requested:
            now = time.monotonic()
            if now < next_tick:
                time.sleep(min(0.004, next_tick - now))
                continue
            keys = term.read()
            game.step(keys)
            size = os.get_terminal_size(sys.stdout.fileno())
            frame = render(game, min(120, size.columns), min(40, size.lines))
            sys.stdout.write("\x1b[H" + frame + "\x1b[J")
            sys.stdout.flush()
            next_tick += DT
            if now - next_tick > 0.25:
                next_tick = now
    return 0


def play_turn_mode() -> int:
    game = Game()
    while not game.quit_requested:
        print("\x1b[2J\x1b[H" + render(game))
        if game.player_hp <= 0 or not game.alive_enemies():
            prompt = "[r]eset or [q]uit > "
        else:
            prompt = "keys > "
        try:
            line = input(prompt)
        except EOFError:
            break
        keys = list(line.lower()) or ["."]
        for key in keys:
            game.step([] if key == "." else [key])
            if game.quit_requested:
                break
    return 0


def run_script(script: str, settle: int = 0) -> Game:
    game = Game()
    for ch in script:
        game.step([] if ch == "." else [ch])
        if game.quit_requested:
            break
    for _ in range(max(0, settle)):
        game.step([])
    return game


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--turn", action="store_true", help="line-input fallback instead of raw real-time input")
    p.add_argument("--script", help="headless deterministic input: one character per simulation tick; '.' means idle")
    p.add_argument("--settle", type=int, default=0, help="idle ticks after --script")
    p.add_argument("--render-final", action="store_true", help="with --script, print final frame before JSON")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.script is not None:
        game = run_script(args.script, args.settle)
        if args.render_final:
            print(render(game))
        print(json.dumps(game.summary(), sort_keys=True))
        return 0
    if args.turn:
        return play_turn_mode()
    return play_interactive()


if __name__ == "__main__":
    raise SystemExit(main())
