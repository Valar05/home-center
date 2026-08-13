#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
installer = (ROOT / "tools/install_atom_phone.sh").read_text(encoding="utf-8")
server = (ROOT / "atom/server.mjs").read_text(encoding="utf-8")
receipts = (ROOT / "atom/judgment-jar-receipts.mjs").read_text(encoding="utf-8")

required = {
    "installer validates config": '[ -f "$ROOT/config/judgment-jars.v1.json" ]' in installer,
    "installer copies config": 'cp "$ROOT/config/judgment-jars.v1.json" "$DEST.new/config/"' in installer,
    "atom wrapper binds installed config": 'HC_JUDGMENT_JARS_CONFIG' in installer and '$HOME/.local/share/atom/config/judgment-jars.v1.json' in installer,
    "installer activates existing daemon": 'bash "$ROOT/tools/setup_vlad_swarm_daemon.sh" ensure' in installer,
    "server resolves config path": 'judgmentJarConfigPath' in server and 'HC_JUDGMENT_JARS_CONFIG' in server,
    "receipt service accepts explicit config": 'createJudgmentJarReceiptService({ configPath' in receipts and 'readFile(configPath' in receipts,
}
failed = [name for name, ok in required.items() if not ok]
if failed:
    raise SystemExit("FAIL: " + "; ".join(failed))
print({"ok": True, "schema": "atom-vlad-judgment-jar-install-contract-v1", **required})
