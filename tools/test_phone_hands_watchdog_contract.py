#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
watchdog = (ROOT / "tools/phone_hands_watchdog.sh").read_text(encoding="utf-8")
installer = (ROOT / "tools/install_phone_hands_watchdog.sh").read_text(encoding="utf-8")

for token in [
    "home_center_phone_relay_recover.sh",
    "phone-relay-heartbeat.json",
    "PHONE_HANDS_WATCHDOG_HEALTHY_AGE_SECONDS",
    "PHONE_HANDS_WATCHDOG_BUSY_GRACE_SECONDS",
    "BUSY_PROTECTED",
    "relay_absent",
    "idle_heartbeat_stale",
    "source_hash_mismatch",
    "heartbeat_pid_mismatch",
    "phone-hands-watchdog.run.lock",
    "-u PHONE_HANDS_WATCHDOG_INTERVAL",
    "-u PHONE_HANDS_REPO_ROOT",
]:
    assert token in watchdog, f"watchdog missing safety/recovery contract: {token}"

for forbidden in [
    "termux-wake-lock",
    "termux-notification",
    "am start",
    "monkey",
    "SYSTEM_ALERT_WINDOW",
    "operator_overlay",
]:
    assert forbidden not in watchdog, f"watchdog must not resurrect UI/power side effects: {forbidden}"

for token in [
    "PHONE_HANDS_WATCHDOG_ACTIVE",
    "20-phone-hands-watchdog",
    "termux-job-scheduler",
    "--job-id",
    "900000",
    "nohup",
    "loop",
    "canonical_recovery=1",
    "no_wakelock=1",
    "no_notification=1",
    "export PHONE_HANDS_WATCHDOG_INTERVAL=60",
]:
    assert token in installer, f"installer missing durable watchdog contract: {token}"

for forbidden in [
    "HC_ENABLE_LEGACY_PHONE_HANDS_WATCHDOG",
    "LEGACY_PHONE_HANDS_WATCHDOG_RETIRED",
    'exec "$DECOMMISSION"',
    "termux-wake-lock",
    "termux-notification",
]:
    assert forbidden not in installer, f"installer regressed to retired/side-effect path: {forbidden}"

assert 'PHONE_HANDS_REPO_ROOT="$REPO_ROOT" "$BIN" once' in installer
assert 'PHONE_HANDS_REPO_ROOT="$REPO_ROOT" nohup "$BIN" loop' in installer
print("Phone Hands working relay watchdog contract: PASS")
