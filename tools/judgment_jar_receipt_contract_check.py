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
assert receipts["homeCenterReadbackRequired"] is True
assert receipts["contextAccessAndCreatedOutputAreDistinctReceipts"] is True
print("judgment_jar_receipt_contract: PASS")
