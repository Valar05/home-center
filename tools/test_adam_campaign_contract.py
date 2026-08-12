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
    'adam-campaign', 'history.jsonl', 'preserve_local', 'restore_local',
    'repair_with_adam', 'persist_repairs', 'while true', 'backoff',
    'install_service', 'run|resume', 'status)', 'receipts)', 'overlay)', 'phone-hands)',
    'PLAN_ALLOWED', 'STOP_ALLOWED', 'Self-heal Adam phone campaign',
]:
    assert token in campaign, token

assert 'max-rounds' not in campaign
assert 'for round in' not in campaign
assert 'git stash push -u' in campaign
assert 'git stash pop --index' in campaign
assert 'git push origin HEAD:main' in campaign

for token in [
    "--ongoing true", "Resume Adam", "Overlay on", "Repair Phone Hands",
    'recover_adam_overlay_phone.sh', 'phone_hands_watchdog.sh', 'adam-campaign run'
]:
    assert token in menu, token

assert 'install-service' in bootstrap
assert 'adam-campaign" run' in bootstrap
print('Adam continuing-value campaign + notification menu contract: PASS')
