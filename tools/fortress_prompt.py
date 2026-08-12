#!/usr/bin/env python3
"""Fortress deterministic prompt compiler.

Stable runtime, mutable behavior. The engine loads a shipped base config plus an
optional user override from ~/.config/home-center/fortress-prompt.json. Nearly all
new vocabulary and command behavior should be configuration-only.
"""
from __future__ import annotations

import difflib
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

HOME = Path.home()
REPO = Path(os.environ.get("FORTRESS_HOME_CENTER", "/storage/emulated/0/Documents/GodotProjects/home-center"))
BASE_CONFIG = REPO / "config/fortress-prompt.json"
USER_CONFIG = HOME / ".config/home-center/fortress-prompt.json"


def deep_merge(base: Any, override: Any) -> Any:
    if isinstance(base, dict) and isinstance(override, dict):
        out = dict(base)
        for key, value in override.items():
            out[key] = deep_merge(out[key], value) if key in out else value
        return out
    # lists intentionally replace, so config authors can fully control grammar
    return override


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_config() -> dict[str, Any]:
    if not BASE_CONFIG.exists():
        raise SystemExit(f"BLOCKED: missing base config: {BASE_CONFIG}")
    cfg = load_json(BASE_CONFIG)
    if USER_CONFIG.exists():
        cfg = deep_merge(cfg, load_json(USER_CONFIG))
    return cfg


def normalize(text: str) -> str:
    return " ".join(text.lower().strip().split())


def expand(token: str, cfg: dict[str, Any]) -> str:
    places = {
        "home": str(HOME),
        "repo": str(REPO),
        **{k: os.path.expandvars(os.path.expanduser(v)) for k, v in cfg.get("places", {}).items()},
    }
    for key, value in places.items():
        token = token.replace("{" + key + "}", value)
    return token


def phrases(cfg: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    out: list[tuple[str, dict[str, Any]]] = []
    for intent in cfg.get("intents", []):
        if not intent.get("enabled", True):
            continue
        for phrase in intent.get("phrases", []):
            out.append((normalize(phrase), intent))
    return out


def resolve(text: str, cfg: dict[str, Any]) -> dict[str, Any] | None:
    needle = normalize(text)
    for phrase, intent in phrases(cfg):
        if needle == phrase:
            return intent
    return None


def suggest(text: str, cfg: dict[str, Any]) -> list[str]:
    needle = normalize(text)
    known = [p for p, _ in phrases(cfg)]
    return difflib.get_close_matches(needle, known, n=5, cutoff=0.35)


def render_argv(intent: dict[str, Any], cfg: dict[str, Any]) -> list[str]:
    return [expand(str(x), cfg) for x in intent.get("argv", [])]


def self_status(cfg: dict[str, Any]) -> int:
    print(json.dumps({
        "engine": str(Path(__file__).resolve()),
        "base_config": str(BASE_CONFIG),
        "user_config": str(USER_CONFIG),
        "user_override_present": USER_CONFIG.exists(),
        "intent_count": len(cfg.get("intents", [])),
        "phrase_count": len(phrases(cfg)),
    }, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    cfg = load_config()
    if argv == ["--self-status"]:
        return self_status(cfg)
    if argv and argv[0] == "--list":
        for phrase, intent in phrases(cfg):
            print(f"{phrase}\t{intent.get('name','unnamed')}")
        return 0
    if not argv:
        print("usage: fortress <human-ish command>")
        return 2

    text = " ".join(argv)
    intent = resolve(text, cfg)
    if not intent:
        print(f"UNKNOWN: {text}")
        nearby = suggest(text, cfg)
        if nearby:
            print("Nearby legal forms:")
            for item in nearby:
                print(f"  {item}")
        return 2

    cmd = render_argv(intent, cfg)
    if not cmd:
        print(f"BLOCKED: intent {intent.get('name')} has no argv")
        return 2
    print("→ " + shlex.join(cmd))
    if intent.get("dry_run", False):
        return 0
    try:
        return subprocess.run(cmd, check=False).returncode
    except FileNotFoundError:
        print(f"BLOCKED: executable not found: {cmd[0]}")
        return 127


if __name__ == "__main__":
    raise SystemExit(main())
