#!/usr/bin/env python3
"""Deterministic contract for the Terminal DMC touch SPA surface."""
from __future__ import annotations

import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import terminal_dmc_anticipation as theorem
import terminal_dmc_web as web


def request_json(url: str, method: str = "GET", body: dict[str, object] | None = None) -> dict[str, object]:
    payload = None
    headers: dict[str, str] = {}
    if body is not None:
        payload = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=payload, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=3) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    lab = web.TouchLab("normal")
    state = lab.state()
    assert state["schema"] == "terminal-dmc.touch-state.v1"
    assert state["condition"]["name"] == "normal"
    assert state["enemy"]["name"] == "IRON MOUTH"
    assert state["controls"]["actions"] == ["strike", "launch", "heavy", "dodge", "brace"]
    assert state["controls"]["lanes"] == ["left", "center", "right"]

    # Normal condition exposes attack identity during anticipation. A touch in
    # that window must survive through resolution and return as replay evidence.
    enemy = lab.game.enemies[0]
    lab.game._start_attack(enemy, theorem.ATTACK_BY_NAME["FALLING_EDGE"])
    lab.enqueue("dodge")
    for _ in range(60):
        lab.tick()
        if lab.last_replay:
            break
    replay = lab.last_replay
    assert replay is not None
    assert replay["attack"] == "FALLING_EDGE"
    assert replay["phase"] == "ANTICIPATION"
    assert replay["correct"] is True
    assert replay["latency_ms"] is not None

    lab.set_condition("collapse")
    collapsed = lab.state()
    assert collapsed["condition"]["channel_bits"]["I_X_A"] == 0.0

    lab.set_condition("perfect")
    perfect = lab.state()
    bits = perfect["condition"]["channel_bits"]
    assert bits["I_X_A"] == bits["I_X_R"]

    html = web.WEB_ROOT.joinpath("index.html").read_text(encoding="utf-8")
    for required in (
        "Read the attack.",
        "DODGE",
        "BRACE",
        "HIDE EARLY CUE",
        "MAKE LATE CUE OBVIOUS",
        "ANTICIPATION",
        "/api/action",
    ):
        assert required in html, required

    # Exercise the real localhost HTTP contract, not only Python methods.
    server = ThreadingHTTPServer(("127.0.0.1", 0), web.handler_factory(lab))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_address[1]}"
        health = request_json(base + "/api/health")
        assert health["ok"] is True
        state2 = request_json(base + "/api/state")
        assert state2["schema"] == "terminal-dmc.touch-state.v1"
        moved = request_json(base + "/api/action", "POST", {"action": "left"})
        assert moved["controls"]["lanes"] == ["left", "center", "right"]
        normal = request_json(base + "/api/condition", "POST", {"condition": "normal"})
        assert normal["condition"]["name"] == "normal"
        with urllib.request.urlopen(base + "/", timeout=3) as response:
            page = response.read().decode("utf-8")
            assert "TOUCH COMBAT LAB" in page
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    print(json.dumps({
        "schema": "terminal-dmc.touch-test.v1",
        "ok": True,
        "proves": [
            "touch lab uses the Python anticipation/combat state as authority",
            "one-enemy five-verb touch surface is present",
            "anticipation response becomes replay evidence",
            "collapse-A and perfect-R conditions reach the touch state",
            "localhost SPA and JSON action/state endpoints answer",
        ],
        "does_not_prove": [
            "the browser presentation is obvious to Drew",
            "touch feel is good on Drew's actual phone",
        ],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
