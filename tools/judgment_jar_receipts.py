#!/usr/bin/env python3
"""Typed Judgment Jar usage receipts and verified Home Center delivery.

Callers capture locally. The existing ``vlad-jars sync`` heartbeat flushes the
oldest pending receipt first, so no second watcher or control plane is created.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from judgment_jar_common import normalize_key, write_atomic

SCHEMA = "home-center.judgment-jar-usage-receipt.v1"
SURFACES = {"jar", "home_center", "vlad"}
DEFAULT_STATE = "~/.local/state/home-center/vlad-swarm/judgment-jar-receipts"


class ReceiptError(RuntimeError):
    pass


def _sha(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _safe(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", str(value or "")).strip("-")[:180]


def settings(config: dict[str, Any]) -> dict[str, Any]:
    raw = dict(config.get("receipts") or {})
    state_env = str(raw.get("stateDirEnv") or "HC_JUDGMENT_JAR_RECEIPT_STATE_DIR")
    root = Path(os.environ.get(state_env, str(raw.get("stateDir") or DEFAULT_STATE))).expanduser()
    return {
        "root": root,
        "schema": str(raw.get("schema") or SCHEMA),
        "kinds": {str(value) for value in raw.get("outputKinds") or []},
        "surfaces": {str(value) for value in raw.get("surfaces") or sorted(SURFACES)},
        "title": str(raw.get("homeCenterLedgerTitle") or "Judgment Jar Usage Receipts — Vlad and Home Center"),
        "fileIdEnv": str(raw.get("homeCenterLedgerFileIdEnv") or "HC_JUDGMENT_JAR_RECEIPT_LEDGER_FILE_ID"),
        "batch": max(1, min(int(raw.get("flushBatchSize") or 12), 100)),
        "maxBackoff": max(30, int(raw.get("maximumBackoffSeconds") or 900)),
    }


def paths(config: dict[str, Any]) -> dict[str, Path]:
    root = settings(config)["root"]
    return {
        "root": root,
        "captured": root / "captured.jsonl",
        "pending": root / "pending",
        "delivered": root / "delivered",
        "deliveredLog": root / "delivered.jsonl",
        "lastCaptured": root / "last-captured.json",
        "lastDelivered": root / "last-delivered.json",
        "ledger": root / "home-center-ledger.json",
    }


def _pending_files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(
        path for path in directory.glob("*.json")
        if path.is_file() and not path.name.startswith("quarantine-")
    )


def _quarantine_files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(path for path in directory.glob("quarantine-*.json") if path.is_file())


def resolve_jar(registry: dict[str, Any], reference: str) -> dict[str, Any] | None:
    key = normalize_key(reference)
    jar_id = (registry.get("aliasIndex") or {}).get(key, key)
    return next((jar for jar in registry.get("jars") or [] if jar.get("id") == jar_id), None)


def jar_identity(registry: dict[str, Any], jar: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "id", "order", "title", "status", "origin", "sourceAuthority", "sourceCompleteness",
        "sourcePath", "sourceSha256", "sourceFileId", "sourceType", "sourceUrl",
        "registryFileId", "registrySection",
    )
    return {
        **{key: jar.get(key) for key in keys if jar.get(key) not in (None, "")},
        "registryDigest": str(registry.get("registryDigest") or ""),
        "registrySchema": str(registry.get("schema") or ""),
        "registrySourceCommit": str(registry.get("sourceCommit") or "unknown"),
    }


def fingerprint(receipt: dict[str, Any]) -> str:
    jar = receipt.get("jar") or {}
    invocation = receipt.get("invocation") or {}
    output = receipt.get("output") or {}
    basis = {
        "jar": [jar.get("id"), jar.get("sourceSha256"), jar.get("registryDigest")],
        "surface": receipt.get("surface"),
        "actor": receipt.get("actor"),
        "intent": receipt.get("intent"),
        "request": invocation.get("requestId"),
        "input": invocation.get("inputSha256"),
        "decision": receipt.get("decisionAction"),
        "output": [output.get("kind"), output.get("status"), output.get("sha256")],
    }
    return _sha(json.dumps(basis, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def build(
    registry: dict[str, Any],
    jar: dict[str, Any],
    *,
    output_kind: str,
    output_text: str,
    summary: str,
    actor: str,
    intent: str,
    surface: str,
    decision_action: str,
    input_text: str = "",
    output_status: str = "created",
    request_id: str = "",
    group_id: str = "",
    references: list[str] | None = None,
    source: str = "vlad-jars",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    receipt = {
        "schema": SCHEMA,
        "receiptId": str(uuid.uuid4()),
        "createdAt": _now(),
        "createdAtEpochMs": int(time.time() * 1000),
        "captureState": "CAPTURED",
        "receiptDeliveryState": "PENDING_HOME_CENTER",
        "homeCenterDeliveryState": "PENDING",
        "surface": str(surface).strip(),
        "actor": str(actor).strip(),
        "intent": str(intent).strip(),
        "decisionAction": str(decision_action).strip(),
        "jar": jar_identity(registry, jar),
        "invocation": {
            "source": str(source).strip() or "vlad-jars",
            "requestId": str(request_id).strip() or str(uuid.uuid4()),
            "groupId": str(group_id).strip() or str(uuid.uuid4()),
            "inputSha256": _sha(input_text),
            "inputBytes": len(str(input_text or "").encode("utf-8")),
        },
        "output": {
            "kind": str(output_kind).strip(),
            "status": str(output_status).strip() or "created",
            "summary": str(summary).strip(),
            "sha256": _sha(output_text),
            "bytes": len(str(output_text or "").encode("utf-8")),
            "references": [str(value) for value in references or [] if str(value).strip()],
        },
        "metadata": dict(metadata or {}),
    }
    receipt["dedupFingerprint"] = fingerprint(receipt)
    return receipt


def validate(receipt: dict[str, Any], config: dict[str, Any]) -> None:
    cfg = settings(config)
    if receipt.get("schema") != cfg["schema"] or not str(receipt.get("receiptId") or ""):
        raise ReceiptError("invalid receipt identity")
    if receipt.get("surface") not in cfg["surfaces"]:
        raise ReceiptError("surface must be jar, home_center, or vlad")
    for key in ("actor", "intent", "decisionAction"):
        if not str(receipt.get(key) or "").strip():
            raise ReceiptError(f"{key} is required")
    kind = str((receipt.get("output") or {}).get("kind") or "")
    if kind not in cfg["kinds"]:
        raise ReceiptError(f"unsupported output kind: {kind}")
    jar = receipt.get("jar") or {}
    if not all(str(jar.get(key) or "") for key in ("id", "origin", "registryDigest")):
        raise ReceiptError("Jar identity is incomplete")
    if receipt.get("dedupFingerprint") != fingerprint(receipt):
        raise ReceiptError("receipt fingerprint mismatch")


def _append(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def capture(receipt: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    validate(receipt, config)
    state = paths(config)
    state["pending"].mkdir(parents=True, exist_ok=True)
    state["delivered"].mkdir(parents=True, exist_ok=True)
    receipt_id = _safe(receipt["receiptId"])
    delivered = state["delivered"] / f"{receipt_id}.json"
    if delivered.is_file():
        return {
            "ok": True,
            "state": "DELIVERED",
            "duplicate": True,
            "receipt": json.loads(delivered.read_text(encoding="utf-8")),
        }
    existing = [path for path in _pending_files(state["pending"]) if path.name.endswith(f"-{receipt_id}.json")]
    if existing:
        return {
            "ok": True,
            "state": "PENDING_HOME_CENTER",
            "duplicate": True,
            "receipt": json.loads(existing[0].read_text(encoding="utf-8")),
        }
    captured = {**receipt, "capturedAt": _now(), "deliveryAttempts": 0, "nextAttemptEpochMs": 0}
    pending = state["pending"] / f"{int(captured['createdAtEpochMs']):016d}-{receipt_id}.json"
    _append(state["captured"], captured)
    write_atomic(state["lastCaptured"], captured)
    write_atomic(pending, captured)
    return {
        "ok": True,
        "state": "PENDING_HOME_CENTER",
        "duplicate": False,
        "receipt": captured,
        "path": str(pending),
    }


def record(registry: dict[str, Any], jar: dict[str, Any], config: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    return capture(build(registry, jar, **kwargs), config)


def _file(value: dict[str, Any]) -> dict[str, Any]:
    for item in (value.get("file"), value.get("document"), value.get("result")):
        if isinstance(item, dict):
            return item
    return value


def _file_id(value: dict[str, Any]) -> str:
    item = _file(value)
    return str(item.get("id") or item.get("fileId") or item.get("documentId") or value.get("documentId") or "")


def _ledger(client: Any, config: dict[str, Any]) -> dict[str, Any]:
    cfg = settings(config)
    state = paths(config)
    title = cfg["title"]
    cached = json.loads(state["ledger"].read_text(encoding="utf-8")) if state["ledger"].is_file() else {}
    for file_id in (os.environ.get(cfg["fileIdEnv"], ""), str(cached.get("fileId") or "")):
        if not file_id:
            continue
        try:
            if client.read_document(file_id, title).strip():
                value = {**cached, "fileId": file_id, "title": title, "verifiedAt": _now()}
                write_atomic(state["ledger"], value)
                return value
        except Exception:
            pass
    exact = next(
        (item for item in client.search_drive(title, 10) if str(item.get("name") or item.get("title") or "") == title),
        None,
    )
    if exact:
        value = {
            "fileId": str(exact.get("id") or exact.get("fileId")),
            "title": title,
            "webViewLink": exact.get("webViewLink", ""),
            "verifiedAt": _now(),
        }
        if value["fileId"] and client.read_document(value["fileId"], title).strip():
            write_atomic(state["ledger"], value)
            return value
    parent = ""
    registry_id = str((config.get("homeCenter") or {}).get("registryFileId") or "")
    if registry_id:
        try:
            parents = _file(client.drive_operation("drive.read_metadata", {"fileId": registry_id})).get("parents") or []
            parent = str(parents[0]) if parents else ""
        except Exception:
            parent = ""
    args: dict[str, Any] = {
        "title": title,
        "body": f"# {title}\n\nAppend-only typed Judgment Jar usage receipts. CAPTURED is not DELIVERED.\n",
    }
    if parent:
        args["folderId"] = parent
    created = client.drive_operation("docs.create", args)
    file_id = _file_id(created)
    if not file_id or title not in client.read_document(file_id, title):
        raise ReceiptError("Home Center receipt ledger creation failed readback")
    value = {
        "fileId": file_id,
        "title": title,
        "webViewLink": _file(created).get("webViewLink", ""),
        "parentId": parent,
        "verifiedAt": _now(),
    }
    write_atomic(state["ledger"], value)
    return value


def _block(receipt: dict[str, Any]) -> str:
    jar = receipt["jar"]
    output = receipt["output"]
    invocation = receipt["invocation"]
    canonical = json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return (
        f"\n\n## {receipt['createdAt']} — {jar.get('title') or jar['id']} → {output['kind']}\n\n"
        f"- receiptId: {receipt['receiptId']}\n"
        f"- judgmentJarReceiptFingerprint: {receipt['dedupFingerprint']}\n"
        f"- surface: {receipt['surface']}\n"
        f"- actor: {receipt['actor']}\n"
        f"- intent: {receipt['intent']}\n"
        f"- decision/action: {receipt['decisionAction']}\n"
        f"- requestId: {invocation['requestId']}\n"
        f"- Jar source: {jar.get('sourcePath') or jar.get('sourceFileId') or 'unknown'}\n"
        f"- output status: {output['status']}\n"
        f"- output summary: {output['summary']}\n"
        f"- output sha256: {output['sha256']}\n"
        f"RECEIPT_JSON: {canonical}\n"
    )


def _deliver(client: Any, config: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    ledger = _ledger(client, config)
    before = client.read_document(ledger["fileId"], ledger["title"])
    fingerprint_marker = f"judgmentJarReceiptFingerprint: {receipt['dedupFingerprint']}"
    id_marker = f"receiptId: {receipt['receiptId']}"
    duplicate = fingerprint_marker in before and id_marker in before
    if not duplicate:
        client.drive_operation("docs.update", {"fileId": ledger["fileId"], "appendText": _block(receipt)})
    after = client.read_document(ledger["fileId"], ledger["title"])
    if fingerprint_marker not in after or id_marker not in after:
        raise ReceiptError("Home Center receipt readback failed")
    return {
        **ledger,
        "duplicate": duplicate,
        "readbackVerified": True,
        "fingerprint": receipt["dedupFingerprint"],
    }


def flush(
    config: dict[str, Any],
    limit: int | None = None,
    client_factory: Callable[[], Any] | None = None,
    now_ms: int | None = None,
) -> dict[str, Any]:
    cfg = settings(config)
    state = paths(config)
    state["pending"].mkdir(parents=True, exist_ok=True)
    state["delivered"].mkdir(parents=True, exist_ok=True)
    pending = _pending_files(state["pending"])
    current = int(now_ms if now_ms is not None else time.time() * 1000)
    delivered_count = 0
    duplicates = 0
    blocked: dict[str, Any] | None = None
    client: Any | None = None
    for path in pending[: max(1, int(limit or cfg["batch"]))]:
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
            validate(receipt, config)
        except Exception as exc:
            quarantine = path.with_name("quarantine-" + path.name)
            path.replace(quarantine)
            blocked = {
                "state": "QUARANTINED",
                "path": str(quarantine),
                "error": f"{type(exc).__name__}: {exc}",
            }
            break
        if int(receipt.get("nextAttemptEpochMs") or 0) > current:
            blocked = {
                "state": "BACKOFF",
                "path": str(path),
                "nextAttemptEpochMs": receipt["nextAttemptEpochMs"],
            }
            break
        try:
            if client is None:
                if client_factory:
                    client = client_factory()
                else:
                    from home_center_mcp_client import HomeCenterMcp
                    client = HomeCenterMcp()
            home = _deliver(client, config, receipt)
            delivered = {
                **receipt,
                "receiptDeliveryState": "DELIVERED",
                "homeCenterDeliveryState": "DELIVERED",
                "deliveredAt": _now(),
                "deliveryAttempts": int(receipt.get("deliveryAttempts") or 0) + 1,
                "nextAttemptEpochMs": 0,
                "lastDeliveryError": "",
                "homeCenter": home,
            }
            write_atomic(state["delivered"] / f"{_safe(receipt['receiptId'])}.json", delivered)
            _append(state["deliveredLog"], delivered)
            write_atomic(state["lastDelivered"], delivered)
            path.unlink(missing_ok=True)
            delivered_count += 1
            duplicates += int(bool(home.get("duplicate")))
        except Exception as exc:
            attempts = int(receipt.get("deliveryAttempts") or 0) + 1
            backoff = min(cfg["maxBackoff"], 2 ** min(attempts, 10))
            receipt.update({
                "deliveryAttempts": attempts,
                "lastDeliveryAttemptAt": _now(),
                "lastDeliveryError": f"{type(exc).__name__}: {exc}",
                "nextAttemptEpochMs": current + backoff * 1000,
            })
            write_atomic(path, receipt)
            blocked = {
                "state": "DELIVERY_FAILED",
                "path": str(path),
                "attempts": attempts,
                "backoffSeconds": backoff,
                "error": receipt["lastDeliveryError"],
            }
            break
    remaining = len(_pending_files(state["pending"]))
    quarantined = len(_quarantine_files(state["pending"]))
    return {
        "ok": blocked is None or delivered_count > 0,
        "state": "DELIVERED" if remaining == 0 and blocked is None else "PENDING_HOME_CENTER",
        "delivered": delivered_count,
        "duplicates": duplicates,
        "pending": remaining,
        "quarantined": quarantined,
        "blocked": blocked,
        "stateDir": str(state["root"]),
        "ledger": json.loads(state["ledger"].read_text(encoding="utf-8")) if state["ledger"].is_file() else None,
    }


def status(config: dict[str, Any]) -> dict[str, Any]:
    cfg = settings(config)
    state = paths(config)
    delivered = len(list(state["delivered"].glob("*.json"))) if state["delivered"].is_dir() else 0
    return {
        "ok": True,
        "schema": cfg["schema"],
        "outputKinds": sorted(cfg["kinds"]),
        "surfaces": sorted(cfg["surfaces"]),
        "pending": len(_pending_files(state["pending"])),
        "quarantined": len(_quarantine_files(state["pending"])),
        "delivered": delivered,
        "stateDir": str(state["root"]),
        "homeCenterLedgerTitle": cfg["title"],
        "ledger": json.loads(state["ledger"].read_text(encoding="utf-8")) if state["ledger"].is_file() else None,
    }
