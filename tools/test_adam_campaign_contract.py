#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
agents = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')
skill = (ROOT / 'skills/operator-campaign/SKILL.md').read_text(encoding='utf-8')
campaign = (ROOT / 'tools/adam_phone_campaign.sh').read_text(encoding='utf-8')
menu = (ROOT / 'tools/home_center_status_menu.sh').read_text(encoding='utf-8')
bootstrap = (ROOT / 'tools/install_adam_phone_campaign.sh').read_text(encoding='utf-8')

for token in [
    'Operator campaigns — continuing value required',
    'A script that succeeds once and becomes dead weight fails this contract.',
    'persistent Home Center notification is a control menu',
]:
    assert token in agents, token

for token in [
    'Stable entrypoint', 'Durable state', 'Self-heal', 'Daemon patience',
    'Continuing operations', 'Control surface', 'Do not hand Drew a command. Leave him a machine that keeps helping.'
]:
    assert token in skill, token

for token in [
    'adam-campaign', 'history.jsonl', 'preserve_workspace', 'restore_workspace',
    'original-ref', 'symbolic-ref --short -q HEAD',
    'repair_with_adam', 'persist_repairs', 'write_acceptance', 'while true', 'backoff',
    'install_service', 'run|resume', 'status)', 'receipts)', 'overlay)', 'phone-hands)',
    'PLAN_ALLOWED', 'STOP_ALLOWED', 'Self-heal Adam phone campaign',
    'git rebase --abort', 'home_center_status_menu.sh" probe',
    "'notificationMenu':menu_ok", "adam-phone-campaign-receipt-v2",
    "'workspacePreservation':True", 'verify-failed repairing',
    'repair_with_adam "$STATE_ROOT/verify.log"',
    'accepted locally but canonical persistence failed; adam-campaign resume will retry',
]:
    assert token in campaign, token

assert 'max-rounds' not in campaign
assert 'for round in' not in campaign
assert 'git stash push -u' in campaign
assert 'git stash pop --index' in campaign
assert 'git push origin HEAD:main' in campaign
assert 'return "$verify_rc"' not in campaign

for token in [
    "--ongoing true", "Resume Adam", "Status", "Recovery", "Overlay on", "Phone Hands", "Receipts", "Back",
    'recover_adam_overlay_phone.sh', 'phone_hands_watchdog.sh', 'adam-campaign run',
    'case "$MODE" in', 'recovery)', 'status)', 'receipts)', 'MODE="${1:-main}"',
    '[ "$MODE" = "probe" ]', 'command -v termux-notification',
]:
    assert token in menu, token

assert 'install-service' in bootstrap
assert 'adam-campaign" run' in bootstrap
print('Adam continuing-value campaign + proven nested notification menu contract: PASS')
