#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
guard = (ROOT / "tools/fortress_queue_guardian.sh").read_text(encoding="utf-8")
supervisor = (ROOT / "tools/fortress_swarm_supervisor.py").read_text(encoding="utf-8")
governor = (ROOT / "tools/fortress_scheduler_governor.py").read_text(encoding="utf-8")

for token in [
    'MAX_TASK_SECONDS="${FORTRESS_QUEUE_MAX_TASK_SECONDS:-120}"',
    'POLL_SECONDS="${FORTRESS_QUEUE_GUARD_POLL_SECONDS:-10}"',
    'queue_daemon_pid()',
    'kill_task_tree()',
    '[ "${ppid:-}" = "$daemon" ] || continue',
    '*"timeout 1800 bash"*',
    'queue.task.stuck_detected',
    'queue.task.timeout',
    'queue.daemon.recovered',
]:
    assert token in guard, f"queue guardian missing bounded recovery contract: {token}"

for forbidden in [
    'reboot',
    'killall',
    'pkill -9',
    'am force-stop com.termux',
    'tmux kill-server',
]:
    assert forbidden not in guard, f"queue guardian may touch unrelated phone/session state: {forbidden}"

for token in [
    'queue_guardian = tools / "fortress_queue_guardian.sh"',
    '["bash", str(queue_guardian), "run"]',
    '"queueGuardianPid"',
    'fortress.swarm-supervisor.v2',
]:
    assert token in supervisor, f"swarm supervisor does not own queue guardian lifecycle: {token}"

for token in [
    'scheduler-wake-request.json',
    'lastAcceptedDigest',
    'actuator_unavailable',
    'nextRetryEpoch',
    'HC_CHATGPT_SCHEDULER_ACTUATOR_CMD',
]:
    assert token in governor, f"scheduler governor missing event-driven fail-closed contract: {token}"

assert 'hourly' not in governor.lower(), "local scheduler governor regressed to hourly polling"
print("Fortress queue guardian + event-driven scheduler contract: PASS")
