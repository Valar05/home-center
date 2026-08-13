#!/usr/bin/env python3
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
config = json.loads((ROOT / "config/judgment-jars.v1.json").read_text(encoding="utf-8"))
receipts = config["receipts"]
assert receipts["commandCenterExists"] is False
assert set(receipts["surfaces"]) == {"jar", "home_center", "vlad"}
assert "context_packet" in receipts["outputKinds"]
assert "review_verdict" in receipts["outputKinds"]
assert "execution_result" in receipts["outputKinds"]
assert receipts["homeCenterReadbackRequired"] is True
assert receipts["contextAccessAndCreatedOutputAreDistinctReceipts"] is True

strict_module = ROOT / "tools/judgment_jar_receipt_truth.py"
quarantine_test = ROOT / "tools/test_judgment_jar_receipt_quarantine_truth.py"
assert strict_module.is_file()
assert quarantine_test.is_file()

vlad_cli = (ROOT / "tools/judgment_jars.py").read_text(encoding="utf-8")
receipt_cli = (ROOT / "tools/jar_receipt.py").read_text(encoding="utf-8")
offline_continue = (ROOT / "tools/cn-offline.ps1").read_text(encoding="utf-8")
assert "from judgment_jar_receipt_truth import" in vlad_cli
assert "from judgment_jar_receipt_truth import" in receipt_cli
assert "apply_import_truth" in vlad_cli
assert "IMPORT_QUARANTINED" in vlad_cli
assert "judgment_jars.py" in offline_continue
assert "jar_receipt.py" in offline_continue
assert "'execution_result'" in offline_continue
assert "Get-ChildItem -Path $rulesPath -Filter '*judgement-jar*.md'" not in offline_continue
assert "judgment-jar-receipts\\artifacts" in offline_continue

print("judgment_jar_receipt_contract: PASS")
