#!/usr/bin/env python3
"""Exercise Jar Runner receipt truth against the real production receipt modules."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from judgment_jar_common import CONFIG_PATH, read_config
from judgment_jar_receipts import build, fingerprint, validate
import judgment_jar_runner as runner


config = read_config(CONFIG_PATH)
registry = {
    "schema": "home-center.judgment-jars.registry.v2",
    "registryDigest": "production-contract-registry",
    "sourceCommit": "fixture",
}
jar = {
    "id": "venice-the-organism-keeps-the-camera",
    "origin": "home-center-cabinet",
    "title": "Venice — The Organism Keeps the Camera",
    "sourceFileId": "fixture-venice-file",
}
artifact_core = {"reviewer": "Venice", "verdict": "CONTINUE", "case": "fixture"}
canonical = json.dumps(artifact_core, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
receipt = build(
    registry, jar, output_kind="review_verdict", output_text=canonical,
    summary="Production receipt validation fixture", actor="Venice",
    intent="verify runner compatibility with production receipt validation", surface="vlad",
    decision_action="CONTINUE", input_text="fixture", request_id="fixture-review",
    group_id="fixture-group", source=runner.TRUSTED_GATE_SOURCES["venice"],
    metadata={"authorityRoute": runner.TRUSTED_AUTHORITY_ROUTES["venice"]},
)
validate(receipt, config)

with tempfile.TemporaryDirectory() as temp:
    delivered = Path(temp) / "delivered"
    delivered.mkdir()
    verified = {
        **receipt,
        "receiptDeliveryState": "DELIVERED",
        "homeCenterDeliveryState": "DELIVERED",
        "homeCenter": {"readbackVerified": True},
    }
    (delivered / "verified.json").write_text(json.dumps(verified), encoding="utf-8")
    found = runner._delivered_receipts(config, lambda _config: {"delivered": delivered})
    assert [value["receiptId"] for value in found] == [receipt["receiptId"]]

    forged = dict(verified)
    forged["dedupFingerprint"] = "0" * 64
    assert forged["dedupFingerprint"] != fingerprint(forged)
    (delivered / "forged.json").write_text(json.dumps(forged), encoding="utf-8")
    found = runner._delivered_receipts(config, lambda _config: {"delivered": delivered})
    assert [value["receiptId"] for value in found] == [receipt["receiptId"]]

print(json.dumps({"ok": True, "schema": "judgment-jar-runner-production-contract.v1"}, sort_keys=True))
