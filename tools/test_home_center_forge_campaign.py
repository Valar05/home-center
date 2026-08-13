#!/usr/bin/env python3
from pathlib import Path
import ast

ROOT=Path(__file__).resolve().parents[1]
forge=(ROOT/'tools/home_center_forge_campaign.py').read_text(encoding='utf-8')
setup=(ROOT/'tools/setup_home_center_forge_campaign.sh').read_text(encoding='utf-8')
skill=(ROOT/'skills/home-center-forge-campaign/SKILL.md').read_text(encoding='utf-8')
menu=(ROOT/'tools/home_center_status_menu.sh').read_text(encoding='utf-8')

ast.parse(forge)
for token in [
 'judgment_jars','adam_planned_venice','PLAN_ALLOWED','provision_gcp_free_forge_vm.sh','bootstrap_free_cloud_forge.sh',
 'BatchMode=yes','FORTRESS_SSH_CONTROL_OK','receipts.jsonl','run.lock','systemctl is-active gitea','time.sleep(min(60,2**min(round_no,5)))'
]: assert token in forge, token
for token in ['home-center-forge','runit','Termux:Boot','supervisor.pid']: assert token in setup or token in skill, token
for token in ['Forge repair','Home Center forge','forge_summary','home-center-forge resume']: assert token in menu, token
assert 'Tailscale' not in forge
print('Home Center forge campaign contract: PASS')
