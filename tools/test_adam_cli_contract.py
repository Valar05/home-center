#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
router = (ROOT / "tools/adam.py").read_text(encoding="utf-8")
worker = (ROOT / "tools/adam_codex_phone.py").read_text(encoding="utf-8")
installer = (ROOT / "tools/install_adam_cli.sh").read_text(encoding="utf-8")

for token in [
    'ONE_SHOT_MODES = ("terminal", "chat", "continue", "vlad")',
    'def run_terminal(',
    'def run_worker(',
    'def worker_commission(',
]:
    assert token in router, f"Adam router missing {token}"

for token in [
    'CORE LOOP',
    'Inspect real workspace state.',
    'Choose ONE typed tool action.',
    'write_file',
    'run_command',
    'phone_intent',
    'respond',
    'finish',
    'def active_jars(',
    'def run_task(',
    'FORMAT_ERROR',
]:
    assert token in worker, f"Adam Codex worker missing {token}"

# Bare Adam and natural-language argv must enter the Codex worker. Only the
# explicit overlay/body mode names enter the transport router.
assert 'exec "$PYTHON_BIN" "$WORKER" "$@"' in installer
assert 'terminal|chat|continue|vlad)' in installer
assert '|shell)' not in installer

# Old interactive persona/executive machinery must not survive in the router.
for forbidden in ['def run_shell(', 'local_exec_plan', 'execute_plan', 'Adam online. Chat naturally', 'ollama_generate']:
    assert forbidden not in router, f"retired Adam machinery survived: {forbidden}"

# Raw prose from the local model cannot be emitted as a response/action.
assert 'action = parse_action(raw)' in worker
assert 'Output was not one valid JSON object' in worker
assert 'print(raw)' not in worker

print("Adam Codex-shaped CLI contract: PASS")
