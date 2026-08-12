#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
adam = (ROOT / "tools/adam.py").read_text(encoding="utf-8")

required = [
    'ONE_SHOT_MODES = ("terminal", "chat", "continue", "vlad")',
    'EXEC_KINDS = ("say", "terminal", "continue", "phone", "vlad")',
    'ONE_SHOT_MODES + ("shell",)',
    'def run_shell(',
    'def run_mode(',
    'def local_exec_plan(',
    'def execute_plan(',
    'def explicit_command(',
    'Adam online. Chat naturally; :help for exact controls.',
    ':sh COMMAND',
    ':continue PROMPT',
    ':phone INTENT',
    ':vlad QUESTION',
    ':chat TEXT',
    'response_format',
    'DANGEROUS_SHELL',
    'interactive_tty_required',
]
for token in required:
    assert token in adam, f"Adam CLI missing {token}"

# Overlay one-shot modes remain explicit and unchanged.
for mode in ('terminal', 'chat', 'continue', 'vlad'):
    assert f'if mode == "{mode}"' in adam or mode == 'vlad'

# Bare conversational turns must be planned into a typed action, not sent to Bash.
assert 'plan = local_exec_plan(history, text, current_cwd, timeout)' in adam
assert 'execute_plan(plan, current_cwd, timeout)' in adam
assert 'run_mode("terminal", text' not in adam

# Exact controls bypass model interpretation.
assert 'handled, _ = explicit_command(text, current_cwd, timeout)' in adam
assert '(":sh", "terminal")' in adam
assert '(":continue", "continue")' in adam

# Runtime blocks known high-risk model-generated shell patterns and has no cloud fallback.
for forbidden in ['cloudFallback=True', 'rm -rf "$HOME"']:
    assert forbidden not in adam, f"Adam CLI contains forbidden token {forbidden}"

print("Adam conversational executive CLI contract: PASS")
