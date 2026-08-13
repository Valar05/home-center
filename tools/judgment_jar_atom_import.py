#!/usr/bin/env python3
"""Import Atom's append-only Jar capture log into the shared receipt outbox."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from judgment_jar_common import write_atomic
from judgment_jar_receipts import ReceiptError, capture, fingerprint


def _source(config: dict[str, Any]) -> Path:
    receipts = config.get("receipts") or {}
    env_name = str(receipts.get("atomStateDirEnv") or "HC_ATOM_STATE_DIR")
    state_dir = Path(os.environ.get(env_name, str(receipts.get("atomStateDir") or "~/.local/state/atom"))).expanduser()
    return state_dir / "judgment-jar-usage.jsonl"


def _receipt_root(config: dict[str, Any]) -> Path:
    receipts = config.get("receipts") or {}
    env_name = str(receipts.get("stateDirEnv") or "HC_JUDGMENT_JAR_RECEIPT_STATE_DIR")
    return Path(os.environ.get(env_name, str(receipts.get("stateDir") or "~/.local/state/home-center/vlad-swarm/judgment-jar-receipts"))).expanduser()


def _append(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def import_atom_receipts(config: dict[str, Any]) -> dict[str, Any]:
    root = _receipt_root(config)
    source = _source(config)
    cursor_path = root / "atom-import-cursor.json"
    quarantine_path = root / "atom-import-quarantine.jsonl"
    if not source.is_file():
        return {
            "ok": True,
            "state": "NO_ATOM_LOG",
            "source": str(source),
            "cursor": str(cursor_path),
            "quarantine": str(quarantine_path),
            "imported": 0,
            "duplicates": 0,
            "rejected": 0,
        }
    cursor = {"line": 0}
    if cursor_path.is_file():
        try:
            cursor = json.loads(cursor_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            cursor = {"line": 0}
    lines = source.read_text(encoding="utf-8", errors="replace").splitlines()
    start = max(0, int(cursor.get("line") or 0))
    cursor_reset = ""
    if start > len(lines):
        start = 0
        cursor_reset = "SOURCE_TRUNCATED_OR_REPLACED"
    imported = duplicates = rejected = 0
    errors: list[dict[str, Any]] = []
    consumed = start
    for index, line in enumerate(lines[start:], start=start):
        if not line.strip():
            consumed = index + 1
            continue
        try:
            receipt = json.loads(line)
            if not isinstance(receipt, dict):
                raise ReceiptError("Atom receipt is not an object")
            receipt.setdefault("surface", "jar")
            receipt.setdefault("actor", "Vlad")
            receipt.setdefault("intent", "retrieve bounded Judgment Jar context")
            receipt.setdefault("decisionAction", "returned cached Jar body and provenance through Atom fast access")
            receipt["captureState"] = "CAPTURED"
            receipt["receiptDeliveryState"] = "PENDING_HOME_CENTER"
            receipt["homeCenterDeliveryState"] = "PENDING"
            receipt["dedupFingerprint"] = fingerprint(receipt)
            result = capture(receipt, config)
            duplicates += int(bool(result.get("duplicate")))
            imported += int(not result.get("duplicate"))
        except Exception as exc:
            rejected += 1
            error = {"line": index + 1, "error": f"{type(exc).__name__}: {exc}"}
            errors.append(error)
            _append(quarantine_path, {
                "schema": "home-center.judgment-jar-atom-import-quarantine.v1",
                "source": str(source),
                "line": index + 1,
                "raw": line,
                **error,
            })
        consumed = index + 1
    write_atomic(cursor_path, {
        "schema": "home-center.judgment-jar-atom-import-cursor.v1",
        "source": str(source),
        "line": consumed,
        "sourceLineCount": len(lines),
        "cursorReset": cursor_reset,
        "quarantine": str(quarantine_path),
        "lastErrors": errors[-10:],
    })
    return {
        "ok": rejected == 0,
        "state": "IMPORTED" if imported else "NO_CHANGE",
        "source": str(source),
        "cursor": str(cursor_path),
        "quarantine": str(quarantine_path),
        "cursorReset": cursor_reset,
        "imported": imported,
        "duplicates": duplicates,
        "rejected": rejected,
        "errors": errors[-10:],
    }
