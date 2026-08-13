#!/usr/bin/env python3
"""Append-only Judgment Jar usage receipts delivered to Atom/Home Center.

The canonical Jar registry remains `judgment_jar_registry.py`: repository
operational Jars plus the Home Center cabinet/discovery cache. This module adds
no second corpus. It records one usage receipt for every Jar actually loaded
or applied and requires the caller to name the kind of output produced.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from judgment_jar_common import CONFIG_PATH, DEFAULT_CACHE, RegistryError, read_config, write_atomic
from judgment_jar_registry import resolve_jar

RECEIPT_SCHEMA = "home-center.judgment-jar-usage-receipt.v1"
ACK_SCHEMA = "home-center.judgment-jar-usage-ack.v1"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_text(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def receipt_config(config: dict[str, Any]) -> dict[str, Any]:
    value = dict(config.get("receipts") or {})
    kinds = [str(item) for item in value.get("outputKinds") or [] if str(item).strip()]
    if not kinds:
        raise RegistryError("Judgment Jar receipt outputKinds are missing from config")
    value["outputKinds"] = kinds
    value.setdefault("schema", RECEIPT_SCHEMA)
    value.setdefault("atomBaseUrlEnv", "HC_ATOM_URL")
    value.setdefault("atomDefaultBaseUrl", "http://127.0.0.1:8788")
    value.setdefault("atomReceiptPath", "/v1/atom/vlad/jars/receipts")
    value.setdefault("timeoutSeconds", 1.5)
    return value


def output_kinds(config: dict[str, Any]) -> frozenset[str]:
    return frozenset(receipt_config(config)["outputKinds"])


def receipt_state_dir(cache: Path = DEFAULT_CACHE) -> Path:
    configured = os.environ.get("HC_JUDGMENT_JAR_RECEIPT_STATE", "").strip()
    return Path(configured).expanduser() if configured else cache.expanduser().parent / "judgment-jar-usage"


def paths(cache: Path = DEFAULT_CACHE) -> dict[str, Path]:
    root = receipt_state_dir(cache)
    return {
        "root": root,
        "history": root / "usage.jsonl",
        "acks": root / "delivery-acks.jsonl",
        "last": root / "last-usage.json",
        "lastAck": root / "last-delivery-ack.json",
        "outbox": root / "outbox",
    }


def public_identity(registry: dict[str, Any], jar: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "id", "order", "title", "status", "origin", "sourceAuthority", "sourceCompleteness",
        "sourcePath", "sourceSha256", "sourceFileId", "sourceType", "sourceUrl",
        "registryFileId", "registrySection",
    )
    return {
        **{key: jar.get(key) for key in keys if jar.get(key) not in (None, "")},
        "registryDigest": registry.get("registryDigest"),
        "registrySchema": registry.get("schema"),
        "registrySourceCommit": registry.get("sourceCommit"),
    }


def resolve_required(registry: dict[str, Any], reference: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(reference, dict):
        jar = resolve_jar(registry, str(reference.get("id") or reference.get("sourcePath") or ""))
    else:
        jar = resolve_jar(registry, str(reference or ""))
    if jar is None:
        raise RegistryError(f"unknown Judgment Jar: {reference}")
    return jar


def atom_contract(config: dict[str, Any]) -> tuple[str, str, float]:
    current = receipt_config(config)
    base = os.environ.get(str(current["atomBaseUrlEnv"]), str(current["atomDefaultBaseUrl"])).rstrip("/")
    return base, str(current["atomReceiptPath"]), float(current["timeoutSeconds"])


def post_json(config: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    base, endpoint, timeout = atom_contract(config)
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        base + endpoint,
        data=raw,
        method="POST",
        headers={"content-type": "application/json", "accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            value = json.loads(body or "{}")
            return {
                "ok": 200 <= response.status < 300 and value.get("ok") is not False,
                "status": response.status,
                "body": value,
            }
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8", errors="replace") or "{}")
        except (json.JSONDecodeError, OSError):
            detail = {"error": str(exc)}
        return {"ok": False, "status": exc.code, "body": detail, "error": f"HTTPError: {exc}"}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def outbox_path(cache: Path, receipt: dict[str, Any]) -> Path:
    state = paths(cache)
    return state["outbox"] / f"{int(receipt['createdAtEpochMs']):013d}-{receipt['receiptId']}.json"


def sync_pending(registry: dict[str, Any], config: dict[str, Any], cache: Path = DEFAULT_CACHE) -> dict[str, Any]:
    state = paths(cache)
    state["outbox"].mkdir(parents=True, exist_ok=True)
    delivered: list[str] = []
    for path in sorted(state["outbox"].glob("*.json")):
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return {
                "ok": False,
                "state": "BLOCKED",
                "delivered": delivered,
                "blocked": {"path": str(path), "error": f"invalid_outbox_shard:{type(exc).__name__}:{exc}"},
            }
        jar = resolve_jar(registry, str((receipt.get("jar") or {}).get("id") or ""))
        if jar is None:
            return {
                "ok": False,
                "state": "BLOCKED",
                "delivered": delivered,
                "blocked": {"path": str(path), "receiptId": receipt.get("receiptId"), "error": "jar_no_longer_resolves"},
            }
        identity = receipt.get("jar") or {}
        if str(jar.get("sourceSha256") or "") != str(identity.get("sourceSha256") or ""):
            return {
                "ok": False,
                "state": "BLOCKED",
                "delivered": delivered,
                "blocked": {
                    "path": str(path),
                    "receiptId": receipt.get("receiptId"),
                    "error": "jar_source_changed_before_delivery",
                    "capturedSourceSha256": identity.get("sourceSha256"),
                    "currentSourceSha256": jar.get("sourceSha256"),
                },
            }
        result = post_json(config, receipt)
        if not result.get("ok"):
            return {
                "ok": False,
                "state": "PENDING",
                "delivered": delivered,
                "blocked": {"path": str(path), "receiptId": receipt.get("receiptId"), "atom": result},
            }
        ack = {
            "schema": ACK_SCHEMA,
            "receiptId": receipt.get("receiptId"),
            "jarId": identity.get("id"),
            "outputKind": (receipt.get("output") or {}).get("kind"),
            "deliveredAt": now_iso(),
            "homeCenterDeliveryState": "DELIVERED",
            "atom": result,
        }
        append_jsonl(state["acks"], ack)
        write_atomic(state["lastAck"], ack)
        path.unlink()
        delivered.append(str(receipt.get("receiptId") or ""))
    remaining = sorted(state["outbox"].glob("*.json"))
    return {
        "ok": not remaining,
        "state": "DELIVERED" if not remaining else "PENDING",
        "delivered": delivered,
        "remaining": len(remaining),
    }


def record_usage(
    registry: dict[str, Any],
    config: dict[str, Any],
    jar_reference: str | dict[str, Any],
    *,
    output_kind: str,
    output_summary: str,
    source: str,
    cache: Path = DEFAULT_CACHE,
    status: str = "created",
    input_text: str = "",
    output_text: str = "",
    request_id: str | None = None,
    group_id: str | None = None,
    output_refs: Iterable[str] = (),
    native_source: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current = receipt_config(config)
    kind = str(output_kind or "").strip()
    if kind not in set(current["outputKinds"]):
        raise RegistryError(f"output kind must be one of {', '.join(current['outputKinds'])}; got {kind!r}")
    jar = resolve_required(registry, jar_reference)
    receipt_id = str(uuid.uuid4())
    created_epoch_ms = int(time.time() * 1000)
    input_value = str(input_text or "")
    output_value = str(output_text or "")
    native = None
    if native_source:
        native = {
            key: native_source.get(key)
            for key in (
                "state", "sourceType", "sourcePath", "sourceFileId", "sourceUrl",
                "sourceSha256", "fetchedAtEpoch", "lastError",
            )
            if native_source.get(key) not in (None, "")
        }
    receipt = {
        "schema": str(current["schema"]),
        "receiptId": receipt_id,
        "createdAt": now_iso(),
        "createdAtEpochMs": created_epoch_ms,
        "captureState": "CAPTURED",
        "homeCenterDeliveryState": "PENDING",
        "jar": public_identity(registry, jar),
        "invocation": {
            "source": str(source or "unknown"),
            "requestId": str(request_id or receipt_id),
            "groupId": str(group_id or request_id or receipt_id),
            "inputSha256": sha256_text(input_value),
            "inputBytes": len(input_value.encode("utf-8")),
        },
        "output": {
            "kind": kind,
            "status": str(status or "created"),
            "summary": str(output_summary or "")[:2000],
            "sha256": sha256_text(output_value),
            "bytes": len(output_value.encode("utf-8")),
            "references": [str(item) for item in output_refs if str(item).strip()],
        },
        "nativeSource": native,
        "metadata": dict(metadata or {}),
    }
    state = paths(cache)
    append_jsonl(state["history"], receipt)
    write_atomic(state["last"], receipt)
    pending = outbox_path(cache, receipt)
    write_atomic(pending, receipt)
    sync = sync_pending(registry, config, cache)
    delivered = not pending.exists()
    return {
        "receipt": receipt,
        "capturePath": str(state["history"]),
        "outboxPath": None if delivered else str(pending),
        "homeCenter": {
            "ok": delivered,
            "state": "DELIVERED" if delivered else "PENDING",
            "sync": sync,
        },
    }


def record_many(
    registry: dict[str, Any],
    config: dict[str, Any],
    jar_references: Iterable[str | dict[str, Any]],
    *,
    output_kind: str,
    output_summary: str,
    source: str,
    cache: Path = DEFAULT_CACHE,
    status: str = "created",
    input_text: str = "",
    output_text: str = "",
    request_id: str | None = None,
    output_refs: Iterable[str] = (),
    metadata: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    group = str(request_id or uuid.uuid4())
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for reference in jar_references:
        jar = resolve_required(registry, reference)
        if jar["id"] in seen:
            continue
        seen.add(jar["id"])
        unique.append(jar)
    if not unique:
        raise RegistryError("at least one Judgment Jar is required for a usage receipt")
    return [
        record_usage(
            registry,
            config,
            jar,
            output_kind=output_kind,
            output_summary=output_summary,
            source=source,
            cache=cache,
            status=status,
            input_text=input_text,
            output_text=output_text,
            request_id=group,
            group_id=group,
            output_refs=output_refs,
            metadata={"usageGroupId": group, **dict(metadata or {})},
        )
        for jar in unique
    ]


def status(registry: dict[str, Any], config: dict[str, Any], cache: Path = DEFAULT_CACHE) -> dict[str, Any]:
    state = paths(cache)
    pending = sorted(state["outbox"].glob("*.json")) if state["outbox"].exists() else []
    return {
        "schema": "home-center.judgment-jar-usage-status.v1",
        "ok": True,
        "registryDigest": registry.get("registryDigest"),
        "jarCount": registry.get("jarCount", 0),
        "outputKinds": list(receipt_config(config)["outputKinds"]),
        "historyPath": str(state["history"]),
        "ackPath": str(state["acks"]),
        "pendingOutboxPath": str(state["outbox"]),
        "pendingUsageReceipts": len(pending),
        "atomBaseUrl": atom_contract(config)[0],
    }


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    return read_config(path)
