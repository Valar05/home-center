#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
adam = (ROOT / "tools/adam.py").read_text(encoding="utf-8")

required = [
    'ONE_SHOT_MODES = ("terminal", "chat", "continue", "vlad")',
    'ONE_SHOT_MODES + ("shell",)',
    'def run_shell(',
    'def run_mode(',
    'def shell_help(',
    'def resolve_cwd(',
    ':mode terminal|chat|continue|vlad',
    'No auto-routing.',
    'interactive_tty_required',
    'shell_does_not_accept_text',
]
for token in required:
    assert token in adam, f"Adam CLI missing {token}"

# Shell requests must flow through the same explicit one-shot router the overlay uses.
assert 'run_mode(lane, text, current_cwd, timeout)' in adam
# The shell may change lanes only from explicit :mode input; it must not inspect text to pick one.
assert 'if stripped.startswith(":mode")' in adam
for forbidden in [
    'classify_intent(',
    'choose_mode(',
    'auto_route(',
    'cloudFallback=True',
]:
    assert forbidden not in adam, f"Adam CLI contains forbidden auto-routing token {forbidden}"

print("Adam deterministic interactive CLI contract: PASS")
