#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
router = (ROOT / "tools/adam.py").read_text(encoding="utf-8")
core = (ROOT / "tools/adam_codex_phone.py").read_text(encoding="utf-8")
planned = (ROOT / "tools/adam_planned_venice.py").read_text(encoding="utf-8")
reviewed = (ROOT / "tools/adam_venice_reviewed.py").read_text(encoding="utf-8")
installer = (ROOT / "tools/install_adam_cli.sh").read_text(encoding="utf-8")

for token in [
    'ONE_SHOT_MODES = ("terminal", "chat", "continue", "vlad")',
    'def run_terminal(',
    'def run_worker(',
    'def worker_commission(',
    'WORKER = ROOT / "tools" / "adam_planned_venice.py"',
    'preExecutionPlanReview=True',
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

for forbidden in ['def run_task(', 'def run_interactive(', 'def main(argv', 'FORMAT_ERROR']:
    assert forbidden not in core, f"unreviewed alternate Adam survived in core: {forbidden}"

for token in [
    'PLANNING_TOOLS = {"read_file", "list_dir", "search_files", "run_command", "submit_plan"}',
    'def preflight(',
    'selectedJars',
    'jarRationale',
    'antagonism',
    'PLAN_ALLOWED',
    'REPLAN_REQUIRED',
    'review_plan_phone(',
    'return execution.run_task(',
]:
    assert token in planned, f"planned Adam entrypoint missing {token}"

for forbidden in ['"write_file"', '"phone_intent"', '"finish"', '"respond"']:
    planning_line = next(line for line in planned.splitlines() if line.startswith('PLANNING_TOOLS'))
    assert forbidden not in planning_line, f"planning phase allows mutation/terminal tool {forbidden}"

for token in [
    'def run_task(',
    'while True:',
    'canonical_venice_review(',
    'CODEX LOCAL STEERING DOCUMENTS (binding)',
    'stop_after_steps',
]:
    assert token in reviewed, f"reviewed execution entrypoint missing {token}"

assert 'exec "$PYTHON_BIN" "$WORKER" "$@"' in installer
assert 'WORKER="$ROOT/tools/adam_planned_venice.py"' in installer
assert 'venicePlanReviewReceiptVerified' in installer
assert 'veniceStopReviewReceiptVerified' in installer
assert 'terminal|chat|continue|vlad)' in installer
assert '|shell)' not in installer

for forbidden in ['def run_shell(', 'local_exec_plan', 'execute_plan', 'Adam online. Chat naturally', 'ollama_generate']:
    assert forbidden not in router, f"retired Adam machinery survived: {forbidden}"

print("Adam planned + Venice-reviewed Codex entrypoint contract: PASS")
