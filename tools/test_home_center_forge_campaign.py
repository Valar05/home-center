#!/usr/bin/env python3
from pathlib import Path
import ast

ROOT=Path(__file__).resolve().parents[1]
forge=(ROOT/'tools/home_center_forge_campaign.py').read_text(encoding='utf-8')
bootstrap=(ROOT/'tools/bootstrap_free_cloud_forge.sh').read_text(encoding='utf-8')
skill=(ROOT/'skills/home-center-forge-campaign/SKILL.md').read_text(encoding='utf-8')
portable=(ROOT/'.gitea/workflows/home-center-ci.yml').read_text(encoding='utf-8')
android=(ROOT/'.gitea/workflows/build-android.yml').read_text(encoding='utf-8')
canary=(ROOT/'.gitea/workflows/forge-canary.yml').read_text(encoding='utf-8')

ast.parse(forge)

for token in [
    'Judgment Jars','PLAN_ALLOWED','bootstrap_free_cloud_forge.sh',
    'FORGE_TAILSCALE_IP','systemctl is-active --quiet gitea',
    'systemctl is-active --quiet gitea-runner',
    'forge-linux-free','phone-android','cauldron-windows',
    'Never substitute cloud proof for platform-specific truth',
]:
    assert token.lower() in forge.lower(), token

for token in [
    'GITEA_VERSION="${HC_GITEA_VERSION:-1.27.3}"',
    'RUNNER_VERSION="${HC_GITEA_RUNNER_VERSION:-3.4.1}"',
    'home-center-forge-bootstrap-ssh',
    'tailscale',
    'HTTP_ADDR = $TS_IP',
    'SSH_LISTEN_HOST = $TS_IP',
    'ENABLED = true',
    'gitea-runner',
    "--labels '$CLOUD_RUNNER_LABEL:host'",
    '--labels "$PHONE_RUNNER_LABEL:host"',
    'firewall-rules delete "$BOOTSTRAP_FW"',
    'PRIVATE_FORGE_PROVEN',
    'repos/migrate',
    'mirror": False',
    'return_run_details=true',
    'workflow_run_id',
    'Gitea Actions canary succeeded',
]:
    assert token in bootstrap, token

assert "Tailscale\' not in forge" not in (ROOT/'tools/test_home_center_forge_campaign.py').read_text(encoding='utf-8')
assert 'public_ipv6=$public6' not in bootstrap
assert 'tcp:3000' not in bootstrap
assert 'tcp:2222' not in bootstrap

for token in ['runs-on: forge-linux-free','sh tools/home_center_ci_validate.sh']:
    assert token in portable, token
for token in ['runs-on: forge-linux-free','bash -n tools/bootstrap_free_cloud_forge.sh','python3 tools/test_home_center_forge_campaign.py']:
    assert token in canary, token
for token in ['runs-on: phone-android','gradle :app:assembleDebug']:
    assert token in android, token

for token in [
    'private Tailscale lane','Gitea','forge-linux-free','phone-android','cauldron-windows',
    'one canonical phone bootstrap','GitHub-hosted Actions'
]:
    assert token.lower() in skill.lower(), token

print('Home Center private forge + CI routing contract: PASS')
