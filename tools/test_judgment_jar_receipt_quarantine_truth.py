#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from judgment_jar_receipt_truth import status


with tempfile.TemporaryDirectory(prefix="jar-quarantine-") as temp:
    root = Path(temp)
    os.environ["HC_TEST_JAR_QUARANTINE_DIR"] = str(root)
    pending = root / "pending"
    pending.mkdir(parents=True)
    (pending / "quarantine-bad.json").write_text("{}\n", encoding="utf-8")
    config = {
        "receipts": {
            "schema": "home-center.judgment-jar-usage-receipt.v1",
            "surfaces": ["jar", "home_center", "vlad"],
            "outputKinds": ["context_packet"],
            "stateDirEnv": "HC_TEST_JAR_QUARANTINE_DIR",
            "stateDir": str(root),
        }
    }
    value = status(config)
    assert value["ok"] is False
    assert value["state"] == "QUARANTINED"
    assert value["quarantined"] == 1
    assert value["blocked"]["state"] == "QUARANTINED"

print(json.dumps({
    "ok": True,
    "schema": "judgment-jar-receipt-quarantine-truth-test.v1",
    "quarantineFailsClosed": True,
}, sort_keys=True))
