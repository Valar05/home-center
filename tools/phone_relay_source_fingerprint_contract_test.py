#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RELAY = (ROOT / "tools/android_phone_home_center_relay.py").read_text(encoding="utf-8")
RECOVER = (ROOT / "tools/home_center_phone_relay_recover.sh").read_text(encoding="utf-8")


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise AssertionError(f"missing {label}: {needle}")


require(RELAY, "hashlib.sha256(Path(__file__).read_bytes()).hexdigest()", "loaded relay source fingerprint")
require(RELAY, "'sourceSha256':RELAY_SOURCE_SHA256", "heartbeat source fingerprint")
require(RECOVER, 'DESIRED_SOURCE_SHA256="$(desired_source_sha256)"', "current on-disk source fingerprint")
require(RECOVER, "if data.get('sourceSha256')!=wanted_sha:", "fingerprint mismatch rejection")
require(RECOVER, 'heartbeat_ok "$existing_pid" "$DESIRED_SOURCE_SHA256"', "healthy-path source match")
require(RECOVER, 'wait_for_heartbeat "$pid" "$STARTUP_WAIT_SECONDS" "$DESIRED_SOURCE_SHA256"', "restart source match")
require(RECOVER, "'desiredSourceSha256':desired_sha or None", "desired fingerprint recovery receipt")
require(RECOVER, "'sourceSha256':raw.get('sourceSha256')", "observed fingerprint recovery receipt")
require(RECOVER, 'RECOVERY_REASON="stale_source_or_unproven_existing_relay"', "bounded stale-source recovery reason")

print("phone relay source fingerprint contract: ok")
