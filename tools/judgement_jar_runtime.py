#!/usr/bin/env python3
"""Shared deterministic Judgment Jar registry and usage receipts.

The .continue rule files remain source truth. This module gives Vlad and every
Jar-governed worker one fast catalog plus one append-only usage receipt shape.
Every usage names the kind of output it produced. Home Center's Atom daemon is
the delivery target; a local oldest-first outbox prevents loss during outages.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "judgement-jar-runtime.v1.json"
STATE_ROOT = Path(os.path.expanduser(os.environ.get("HC_STATE_DIR", "~/.local/state/home-center")))
STATE_DIR = STATE_ROOT / "judgement-jars"
RECEIPTS_PATH = STATE_DIR / "usage-receipts.jsonl"
LAST_PATH = STATE_DIR / "last-usage.json"
ACKS_PATH = STATE_DIR / "sync-acks.jsonl"
LAST_SYNC_PATH = STATE_DIR / "last-sync.json"
CATALOG_PATH = STATE_DIR / "catalog.json"
CATALOG_PENDING_PATH = STATE_DIR / "catalog-pending.json"
OUTBOX_DIR = STATE_DIR / "outbox"


def _load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


CONFIG = _load_config()
OUTPUT_KINDS = frozenset(str(x) for x in CONFIG.get("outputKinds", []))
RECEIPT_SCHEMA = str(CONFIG.get("receipt", {}).get("schema") or "home-center.judgement-jar-usage-receipt.v1")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha_text(value: str) -> str:
    return _sha_bytes(str(value or "").encode("utf-8"))


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(path)


def _append_jsonl(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def _jar_id(path: Path) -> tuple[int, str]:
    match = re.match(r"^(\d+)-judgement-jar-(.+)\.md$", path.name)
    if not match:
        raise ValueError(f"not an active Judgment Jar path: {path}")
    return int(match.group(1)), match.group(2)


def _title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("#"):
            value = line.lstrip("# ").strip()
            if value:
                return value
    return fallback


def catalog(*, include_text: bool = False, sync: bool = False) -> list[dict[str, Any]]:
    pattern = str(CONFIG.get("sourceGlob") or ".continue/rules/*judgement-jar*.md")
    jars: list[dict[str, Any]] = []
    for path in sorted(ROOT.glob(pattern)):
        if not path.is_file():
            continue
        raw = path.read_bytes()
        text = raw.decode("utf-8", errors="replace")
        order, slug = _jar_id(path)
        item: dict[str, Any] = {
            "id": slug,
            "order": order,
            "title": _title(text, path.name),
            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "filename": path.name,
            "sha256": _sha_bytes(raw),
            "bytes": len(raw),
        }
        if include_text:
            item["text"] = text
        jars.append(item)
    jars.sort(key=lambda item: (int(item["order"]), str(item["id"])))
    if sync:
        sync_catalog(jars)
    return jars


def resolve_jar(reference: str, *, include_text: bool = True) -> dict[str, Any]:
    needle = str(reference or "").strip().lower()
    if not needle:
        raise KeyError("Judgment Jar reference is required")
    matches: list[dict[str, Any]] = []
    for item in catalog(include_text=include_text):
        aliases = {
            str(item["id"]).lower(),
            str(item["order"]),
            f"{int(item['order']):02d}",
            str(item["filename"]).lower(),
            str(item["path"]).lower(),
            str(item["title"]).lower(),
        }
        if needle in aliases:
            matches.append(item)
    if not matches:
        prefix = [
            item for item in catalog(include_text=include_text)
            if str(item["id"]).lower().startswith(needle)
            or str(item["filename"]).lower().startswith(needle)
        ]
        matches = prefix
    if len(matches) != 1:
        raise KeyError(f"Judgment Jar reference {reference!r} resolved to {len(matches)} jars")
    return matches[0]


def _daemon_contract() -> tuple[str, float, str, str]:
    cfg = CONFIG.get("homeCenterDaemon", {})
    base = os.environ.get(str(cfg.get("baseUrlEnv") or "HC_ATOM_URL"), str(cfg.get("defaultBaseUrl") or "http://127.0.0.1:8788"))
    return (
        base.rstrip("/"),
        float(cfg.get("timeoutSeconds") or 1.5),
        str(cfg.get("catalogPath") or "/v1/atom/vlad/jars/sync"),
        str(cfg.get("receiptPath") or "/v1/atom/vlad/jars/receipts"),
    )


def _post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    base, timeout, _, _ = _daemon_contract()
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        base + path,
        data=raw,
        method="POST",
        headers={"content-type": "application/json", "accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            data = json.loads(body or "{}")
            return {"ok": 200 <= response.status < 300 and data.get("ok") is not False, "status": response.status, "body": data}
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def _catalog_snapshot(jars: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    values = jars if jars is not None else catalog(include_text=False)
    return {
        "schema": "home-center.judgement-jar-catalog.v1",
        "generatedAt": _now_iso(),
        "source": "repository:.continue/rules/*judgement-jar*.md",
        "count": len(values),
        "jars": values,
        "catalogSha256": _sha_text(json.dumps(values, ensure_ascii=False, sort_keys=True)),
    }


def sync_catalog(jars: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    snapshot = _catalog_snapshot(jars)
    _atomic_json(CATALOG_PATH, snapshot)
    _, _, catalog_endpoint, _ = _daemon_contract()
    result = _post(catalog_endpoint, snapshot)
    if result.get("ok"):
        if CATALOG_PENDING_PATH.exists():
            CATALOG_PENDING_PATH.unlink()
        ack = {
            "schema": "home-center.judgement-jar-sync-ack.v1",
            "kind": "catalog",
            "at": _now_iso(),
            "catalogSha256": snapshot["catalogSha256"],
            "count": snapshot["count"],
            "daemon": result,
        }
        _append_jsonl(ACKS_PATH, ack)
        _atomic_json(LAST_SYNC_PATH, ack)
        return {"ok": True, "state": "DELIVERED", "snapshot": snapshot, "daemon": result}
    _atomic_json(CATALOG_PENDING_PATH, snapshot)
    return {"ok": False, "state": "PENDING", "snapshot": snapshot, "daemon": result}


def _receipt_outbox_path(receipt_id: str, created_epoch_ms: int) -> Path:
    return OUTBOX_DIR / f"{created_epoch_ms:013d}-{receipt_id}.json"


def _deliver_receipt_file(path: Path) -> dict[str, Any]:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    _, _, _, receipt_endpoint = _daemon_contract()
    result = _post(receipt_endpoint, receipt)
    if not result.get("ok"):
        return {"ok": False, "path": str(path), "daemon": result, "receiptId": receipt.get("receiptId")}
    ack = {
        "schema": "home-center.judgement-jar-sync-ack.v1",
        "kind": "usage",
        "at": _now_iso(),
        "receiptId": receipt.get("receiptId"),
        "jarId": receipt.get("jar", {}).get("id"),
        "outputKind": receipt.get("output", {}).get("kind"),
        "daemon": result,
    }
    _append_jsonl(ACKS_PATH, ack)
    _atomic_json(LAST_SYNC_PATH, ack)
    path.unlink()
    return {"ok": True, "state": "DELIVERED", "ack": ack}


def sync_pending() -> dict[str, Any]:
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    delivered: list[str] = []
    for path in sorted(OUTBOX_DIR.glob("*.json")):
        result = _deliver_receipt_file(path)
        if not result.get("ok"):
            return {"ok": False, "state": "PENDING", "delivered": delivered, "blocked": result}
        delivered.append(str(result.get("ack", {}).get("receiptId") or ""))
    catalog_result = None
    if CATALOG_PENDING_PATH.exists():
        snapshot = json.loads(CATALOG_PENDING_PATH.read_text(encoding="utf-8"))
        _, _, catalog_endpoint, _ = _daemon_contract()
        posted = _post(catalog_endpoint, snapshot)
        if posted.get("ok"):
            CATALOG_PENDING_PATH.unlink()
            catalog_result = {"ok": True, "state": "DELIVERED", "daemon": posted}
        else:
            catalog_result = {"ok": False, "state": "PENDING", "daemon": posted}
    return {"ok": not OUTBOX_DIR.glob("*.json"), "state": "DELIVERED" if not list(OUTBOX_DIR.glob("*.json")) else "PENDING", "delivered": delivered, "catalog": catalog_result}


def record_usage(
    jar_reference: str,
    *,
    output_kind: str,
    output_summary: str,
    source: str,
    status: str = "created",
    input_text: str = "",
    output_text: str = "",
    request_id: str | None = None,
    output_refs: Iterable[str] = (),
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    kind = str(output_kind or "").strip()
    if kind not in OUTPUT_KINDS:
        raise ValueError(f"output_kind must be one of {sorted(OUTPUT_KINDS)}; got {kind!r}")
    jar = resolve_jar(jar_reference, include_text=False)
    created_epoch_ms = int(time.time() * 1000)
    receipt_id = str(uuid.uuid4())
    input_value = str(input_text or "")
    output_value = str(output_text or "")
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "receiptId": receipt_id,
        "createdAt": _now_iso(),
        "createdAtEpochMs": created_epoch_ms,
        "captureState": "CAPTURED",
        "homeCenterDeliveryState": "PENDING",
        "jar": jar,
        "invocation": {
            "source": str(source or "unknown"),
            "requestId": str(request_id or receipt_id),
            "inputSha256": _sha_text(input_value),
            "inputBytes": len(input_value.encode("utf-8")),
        },
        "output": {
            "kind": kind,
            "status": str(status or "created"),
            "summary": str(output_summary or "")[:2000],
            "sha256": _sha_text(output_value),
            "bytes": len(output_value.encode("utf-8")),
            "references": [str(x) for x in output_refs if str(x).strip()],
        },
        "metadata": dict(metadata or {}),
    }
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    _append_jsonl(RECEIPTS_PATH, receipt)
    _atomic_json(LAST_PATH, receipt)
    outbox_path = _receipt_outbox_path(receipt_id, created_epoch_ms)
    _atomic_json(outbox_path, receipt)
    delivered = _deliver_receipt_file(outbox_path)
    return {
        "receipt": receipt,
        "capturePath": str(RECEIPTS_PATH),
        "outboxPath": str(outbox_path) if outbox_path.exists() else None,
        "homeCenter": delivered,
    }


def record_many(
    jar_references: Iterable[str],
    *,
    output_kind: str,
    output_summary: str,
    source: str,
    status: str = "created",
    input_text: str = "",
    output_text: str = "",
    request_id: str | None = None,
    output_refs: Iterable[str] = (),
    metadata: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    group_id = str(request_id or uuid.uuid4())
    results = []
    seen: set[str] = set()
    for reference in jar_references:
        jar = resolve_jar(reference, include_text=False)
        path = str(jar["path"])
        if path in seen:
            continue
        seen.add(path)
        results.append(record_usage(
            path,
            output_kind=output_kind,
            output_summary=output_summary,
            source=source,
            status=status,
            input_text=input_text,
            output_text=output_text,
            request_id=group_id,
            output_refs=output_refs,
            metadata={"usageGroupId": group_id, **dict(metadata or {})},
        ))
    if not results:
        raise ValueError("at least one Judgment Jar is required")
    return results


def status() -> dict[str, Any]:
    jars = catalog(include_text=False)
    pending = sorted(OUTBOX_DIR.glob("*.json")) if OUTBOX_DIR.exists() else []
    return {
        "schema": "home-center.judgement-jar-runtime-status.v1",
        "ok": True,
        "jarCount": len(jars),
        "outputKinds": sorted(OUTPUT_KINDS),
        "catalogPath": str(CATALOG_PATH),
        "usageReceiptsPath": str(RECEIPTS_PATH),
        "pendingUsageReceipts": len(pending),
        "catalogPending": CATALOG_PENDING_PATH.exists(),
        "homeCenterDaemon": _daemon_contract()[0],
    }
