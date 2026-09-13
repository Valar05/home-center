#!/usr/bin/env python3
"""Touch-first localhost SPA for the Terminal DMC anticipation experiment.

The Python combat/theorem simulation remains authoritative. The browser is a
presentation and input surface: it makes anticipation, commitment, reaction,
impact, touch timing, and immediate replay visible without requiring the player
to decode terminal glyphs or remember keyboard bindings.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import threading
import time
from collections import deque
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import terminal_dmc as base
import terminal_dmc_anticipation as theorem

ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "web" / "terminal-dmc"
TICK_SECONDS = 1.0 / base.TICK_HZ

CONDITIONS = {
    "normal": (False, False, "READ EARLY"),
    "collapse": (True, False, "EARLY CUE HIDDEN"),
    "perfect": (False, True, "LATE CUE OBVIOUS"),
}

ACTIONS = {
    "left": "a",
    "right": "d",
    "strike": "j",
    "launch": "k",
    "heavy": "l",
    "dodge": " ",
    "brace": "f",
}

ATTACK_NAMES = {
    "FALLING_EDGE": "OVERHEAD",
    "LINE_THRUST": "THRUST",
    "LOW_SWEEP": "SWEEP",
}

RESPONSE_NAMES = {
    "DODGE": "DODGE",
    "STRAFE": "LEAVE THE LANE",
    "BRACE": "BRACE",
}


class TouchLab:
    """Thread-safe single-enemy teaching surface over AnticipationGame."""

    def __init__(self, condition: str = "normal") -> None:
        self.lock = threading.RLock()
        self.pending: deque[str] = deque(maxlen=6)
        self.condition = "normal"
        self.histories: dict[str, list[dict[str, object]]] = {
            key: [] for key in CONDITIONS
        }
        self._seen_trials: set[str] = set()
        self.replay_id = 0
        self.last_replay: dict[str, object] | None = None
        self.game = theorem.AnticipationGame()
        self.set_condition(condition, reset_history=False)

    def _trial_log(self, condition: str) -> Path:
        state = Path(
            os.environ.get("HC_STATE_DIR", "~/.local/state/home-center")
        ).expanduser()
        return state / "terminal-dmc-campaign" / f"touch-trials-{condition}.jsonl"

    def _new_game(self) -> None:
        game = theorem.AnticipationGame()
        enemy = base.Enemy(
            "IRON MOUTH",
            lane=0,
            distance=1.72,
            hp=9999,
            max_hp=9999,
            attack_cooldown=10,
        )
        game.enemies = [enemy]
        game._reset_attack_state(enemy)
        game.events = ["Watch the body before you choose."]
        self.game = game
        self.pending.clear()
        self._seen_trials.clear()
        self.last_replay = None

    def set_condition(self, condition: str, reset_history: bool = False) -> None:
        if condition not in CONDITIONS:
            raise ValueError(f"unknown condition: {condition}")
        with self.lock:
            collapse, perfect, _ = CONDITIONS[condition]
            theorem.COLLAPSE_ANTICIPATION = collapse
            theorem.PERFECT_REACTION = perfect
            theorem.TRIAL_LOG = self._trial_log(condition)
            self.condition = condition
            if reset_history:
                self.histories[condition].clear()
            self._new_game()

    def reset(self) -> None:
        with self.lock:
            self._new_game()

    def enqueue(self, action: str) -> None:
        with self.lock:
            if action == "center":
                self.pending.append("@center")
                return
            key = ACTIONS.get(action)
            if key is None:
                raise ValueError(f"unknown action: {action}")
            self.pending.append(key)

    @staticmethod
    def _signature(trial: dict[str, object]) -> str:
        fields = (
            trial.get("tick"),
            trial.get("attack"),
            trial.get("outcome"),
            trial.get("first_response"),
            trial.get("first_response_phase"),
        )
        return json.dumps(fields, separators=(",", ":"))

    def _collect_trials(self) -> None:
        for trial in self.game.theorem_trials:
            signature = self._signature(trial)
            if signature in self._seen_trials:
                continue
            self._seen_trials.add(signature)
            copy = dict(trial)
            copy["condition_name"] = self.condition
            self.histories[self.condition].append(copy)
            self.histories[self.condition] = self.histories[self.condition][-200:]
            self.replay_id += 1
            self.last_replay = self._replay(copy)

            # The lab is deliberately brisk. After a completed exchange the
            # next one arrives quickly enough to support perceptual learning.
            enemy = self.game.enemies[0]
            enemy.attack_cooldown = min(enemy.attack_cooldown, 16)
            enemy.distance = min(enemy.distance, 1.9)

    def tick(self) -> None:
        with self.lock:
            keys: list[str] = []
            # Preserve touch intent through hit-stop instead of reproducing the
            # terminal prototype's known eaten-input problem.
            if self.game.hitstop <= 0 and self.pending:
                token = self.pending.popleft()
                if token == "@center":
                    self.game.player_lane = 0
                else:
                    keys.append(token)
            self.game.step(keys)
            self._collect_trials()

            # This is a training room, not a life counter. Keep the lesson alive
            # after failure without deleting the evidence from the trial log.
            if self.game.player_hp <= 0:
                self.game.player_hp = 100
                self.game.recovery = 0
                self.game.combo = 0
                self.game.events.append("RESET // keep reading")
                self.game.events[:] = self.game.events[-4:]

    def _stats(self) -> dict[str, object]:
        rows = self.histories[self.condition]
        responded = [row for row in rows if row.get("first_response")]
        correct = [row for row in responded if row.get("response_correct") is True]
        latencies = [
            int(row["response_latency_ticks"]) * 1000.0 / base.TICK_HZ
            for row in responded
            if isinstance(row.get("response_latency_ticks"), int)
        ]
        return {
            "trials": len(rows),
            "responses": len(responded),
            "correct": len(correct),
            "correct_rate": (
                round(len(correct) / len(responded), 3) if responded else None
            ),
            "mean_latency_ms": (
                round(sum(latencies) / len(latencies)) if latencies else None
            ),
        }

    def _replay(self, trial: dict[str, object]) -> dict[str, object]:
        phase = trial.get("first_response_phase")
        response = trial.get("first_response")
        correct = trial.get("response_correct")
        outcome = str(trial.get("outcome") or "")
        attack = str(trial.get("attack") or "")
        required = str(trial.get("required_response") or "")
        latency_ticks = trial.get("response_latency_ticks")
        latency_ms = (
            round(int(latency_ticks) * 1000.0 / base.TICK_HZ)
            if isinstance(latency_ticks, int)
            else None
        )

        if outcome == "INTERRUPTED_BY_OFFENSE":
            lesson = "You attacked before impact and erased the remaining question."
            tone = "initiative"
        elif response is None:
            lesson = "Impact arrived before you made a defensive choice."
            tone = "late"
        elif correct and phase == "ANTICIPATION":
            lesson = "You read the setup before commitment. That is the head start."
            tone = "early"
        elif correct and phase in {"COMMIT", "REACTION"}:
            lesson = "Correct answer, later information. Compare how much time it cost."
            tone = "late-correct"
        elif correct:
            lesson = "Correct response. Now move the same decision earlier."
            tone = "correct"
        else:
            lesson = f"First read was {response}. This attack asked for {required}."
            tone = "wrong"

        return {
            "id": self.replay_id,
            "attack": attack,
            "attack_label": ATTACK_NAMES.get(attack, attack),
            "response": response,
            "response_label": RESPONSE_NAMES.get(str(response), response),
            "required_response": required,
            "required_label": RESPONSE_NAMES.get(required, required),
            "phase": phase,
            "correct": correct,
            "outcome": outcome,
            "latency_ms": latency_ms,
            "lesson": lesson,
            "tone": tone,
        }

    def state(self) -> dict[str, object]:
        with self.lock:
            enemy = self.game.enemies[0]
            phase = str(getattr(enemy, "theorem_phase", "IDLE"))
            attack = self.game._attack_profile(enemy)
            attack_name = attack.name if attack else None
            remaining = int(getattr(enemy, "theorem_phase_ticks", 0) or 0)
            totals = {
                "ANTICIPATION": attack.anticipation_frames if attack else 1,
                "COMMIT": attack.commit_frames if attack else 1,
                "REACTION": attack.reaction_frames if attack else 1,
            }
            total = max(1, int(totals.get(phase, 1)))
            progress = 0.0 if phase == "IDLE" else max(0.0, min(1.0, 1 - remaining / total))
            collapse, perfect, condition_label = CONDITIONS[self.condition]
            channel = theorem.channel_information()
            stats = self._stats()
            tutorial_stage = (
                "SHOW_ANSWER" if stats["trials"] < 2
                else "SHOW_CUE" if stats["trials"] < 5
                else "BODY_ONLY"
            )

            cue = None
            reaction_cue = None
            required = None
            if attack:
                cue = theorem.anticipation_observation(attack)
                reaction_cue = theorem.reaction_observation(attack)
                required = attack.required_response

            return {
                "schema": "terminal-dmc.touch-state.v1",
                "tick": self.game.tick,
                "condition": {
                    "name": self.condition,
                    "label": condition_label,
                    "collapse_anticipation": collapse,
                    "perfect_reaction": perfect,
                    "channel_bits": channel["bits"],
                },
                "tutorial_stage": tutorial_stage,
                "player": {
                    "hp": self.game.player_hp,
                    "lane": self.game.player_lane,
                    "style": round(self.game.style, 1),
                    "rank": self.game.rank(),
                    "combo": self.game.combo,
                    "pose": self.game.pose,
                    "last_move": self.game.last_move,
                    "hitstop": self.game.hitstop,
                },
                "enemy": {
                    "name": enemy.name,
                    "lane": enemy.lane,
                    "distance": round(enemy.distance, 3),
                    "airborne": enemy.airborne,
                    "height": round(enemy.height, 3),
                    "stagger": enemy.stagger,
                    "phase": phase,
                    "phase_progress": round(progress, 3),
                    "phase_remaining_ticks": remaining,
                    "attack": attack_name,
                    "attack_label": ATTACK_NAMES.get(str(attack_name), attack_name),
                    "anticipation_cue": cue,
                    "reaction_cue": reaction_cue,
                    "required_response": required,
                    "required_label": RESPONSE_NAMES.get(str(required), required),
                },
                "stats": stats,
                "replay": self.last_replay,
                "events": list(self.game.events[-4:]),
                "controls": {
                    "lanes": ["left", "center", "right"],
                    "actions": ["strike", "launch", "heavy", "dodge", "brace"],
                },
            }


class LabRunner:
    def __init__(self, lab: TouchLab) -> None:
        self.lab = lab
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._loop, name="terminal-dmc-tick", daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        self.thread.join(timeout=2.0)

    def _loop(self) -> None:
        deadline = time.monotonic()
        while not self.stop_event.is_set():
            deadline += TICK_SECONDS
            self.lab.tick()
            delay = deadline - time.monotonic()
            if delay > 0:
                self.stop_event.wait(delay)
            else:
                deadline = time.monotonic()


def handler_factory(lab: TouchLab) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "TerminalDMCTouch/1"

        def log_message(self, _format: str, *_args: object) -> None:
            return

        def _json(self, value: object, status: int = 200) -> None:
            payload = json.dumps(value, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(payload)

        def _body(self) -> dict[str, Any]:
            try:
                length = min(4096, int(self.headers.get("Content-Length", "0") or "0"))
                raw = self.rfile.read(length) if length else b"{}"
                value = json.loads(raw.decode("utf-8"))
                return value if isinstance(value, dict) else {}
            except Exception:
                return {}

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/api/state":
                self._json(lab.state())
                return
            if self.path == "/api/health":
                self._json({"ok": True, "schema": "terminal-dmc.touch-health.v1"})
                return
            if self.path in {"/", "/index.html"}:
                path = WEB_ROOT / "index.html"
                if not path.is_file():
                    self.send_error(HTTPStatus.NOT_FOUND, "touch SPA missing")
                    return
                payload = path.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Content-Security-Policy", "default-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:")
                self.end_headers()
                self.wfile.write(payload)
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:  # noqa: N802
            body = self._body()
            try:
                if self.path == "/api/action":
                    lab.enqueue(str(body.get("action") or ""))
                    self._json(lab.state())
                    return
                if self.path == "/api/condition":
                    lab.set_condition(str(body.get("condition") or "normal"))
                    self._json(lab.state())
                    return
                if self.path == "/api/reset":
                    lab.reset()
                    self._json(lab.state())
                    return
            except ValueError as exc:
                self._json({"ok": False, "error": str(exc)}, status=400)
                return
            self.send_error(HTTPStatus.NOT_FOUND)

    return Handler


def bind_server(host: str, port: int, lab: TouchLab) -> ThreadingHTTPServer:
    candidates = [port] if port == 0 else list(range(port, port + 11))
    last_error: OSError | None = None
    for candidate in candidates:
        try:
            return ThreadingHTTPServer((host, candidate), handler_factory(lab))
        except OSError as exc:
            last_error = exc
    assert last_error is not None
    raise last_error


def open_url(url: str) -> bool:
    opener = shutil.which("termux-open-url")
    if not opener:
        return False
    try:
        subprocess.Popen(
            [opener, url],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return True
    except OSError:
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Terminal DMC touch combat lab")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8780)
    parser.add_argument("--condition", choices=sorted(CONDITIONS), default="normal")
    parser.add_argument("--open", action="store_true", dest="open_browser")
    args = parser.parse_args(argv)

    if not WEB_ROOT.joinpath("index.html").is_file():
        parser.error(f"touch SPA missing: {WEB_ROOT / 'index.html'}")

    lab = TouchLab(args.condition)
    runner = LabRunner(lab)
    server = bind_server(args.host, args.port, lab)
    port = int(server.server_address[1])
    url = f"http://{args.host}:{port}/"

    print(f"Terminal DMC Touch Lab: {url}", flush=True)
    print("The browser is the controller. Ctrl-C here stops the local server.", flush=True)
    if args.open_browser:
        if open_url(url):
            print("Opened browser.", flush=True)
        else:
            print(f"Open this URL on the phone: {url}", flush=True)

    runner.start()
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()
        runner.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
