#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
router = (ROOT / "tools/adam.py").read_text(encoding="utf-8")
core = (ROOT / "tools/adam_codex_phone.py").read_text(encoding="utf-8")
reviewed = (ROOT / "tools/adam_venice_reviewed.py").read_text(encoding="utf-8")
installer = (ROOT / "tools/install_adam_cli.sh").read_text(encoding="utf-8")

for token in [
    'ONE_SHOT_MODES = ("terminal", "chat", "continue", "vlad")',
    'def run_terminal(',
    'def run_worker(',
    'def worker_commission(',
    'WORKER = ROOT / "tools" / "adam_venice_reviewed.py"',
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
    'def execute_tool(',
    'internal core; use bare `adam`',
]:
    assert token in core, f"Adam deterministic core missing {token}"

# The low-level core is no longer an alternate agent with its own stop loop.
for forbidden in ['def run_task(', 'def run_interactive(', 'def main(argv', 'FORMAT_ERROR']:
    assert forbidden not in core, f"unreviewed alternate Adam survived in core: {forbidden}"

for token in [
    'def run_task(',
    'while True:',
    'canonical_venice_review(',
    'CODEX LOCAL STEERING DOCUMENTS (binding)',
    'stop_after_steps',
]:
    assert token in reviewed, f"reviewed Adam entrypoint missing {token}"

assert 'exec "$PYTHON_BIN" "$WORKER" "$@"' in installer
assert 'terminal|chat|continue|vlad)' in installer
assert '|shell)' not in installer

for forbidden in ['def run_shell(', 'local_exec_plan', 'execute_plan', 'Adam online. Chat naturally', 'ollama_generate']:
    assert forbidden not in router, f"retired Adam machinery survived: {forbidden}"

print("Adam single reviewed Codex entrypoint contract: PASS")
