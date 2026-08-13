#!/usr/bin/env python3
"""Public receipt API with strict delivery and quarantine truth."""
from __future__ import annotations

from typing import Any, Callable

from judgment_jar_receipts import (
    ReceiptError,
    build,
    capture,
    fingerprint,
    flush as _flush,
    jar_identity,
    paths,
    record,
    resolve_jar,
    settings,
    status as _status,
    validate,
)


def _strict(value: dict[str, Any]) -> dict[str, Any]:
    quarantined = int(value.get("quarantined") or 0)
    if quarantined <= 0:
        return value
    prior_block = value.get("blocked") if isinstance(value.get("blocked"), dict) else None
    blocked: dict[str, Any] = {
        "state": "QUARANTINED",
        "count": quarantined,
        "error": "One or more Judgment Jar receipt shards require explicit repair.",
    }
    if prior_block:
        blocked["alsoBlocked"] = prior_block
    return {
        **value,
        "ok": False,
        "state": "QUARANTINED",
        "blocked": blocked,
    }


def flush(
    config: dict[str, Any],
    limit: int | None = None,
    client_factory: Callable[[], Any] | None = None,
    now_ms: int | None = None,
) -> dict[str, Any]:
    value = _flush(config, limit=limit, client_factory=client_factory, now_ms=now_ms)
    if (
        value.get("state") == "DELIVERED"
        and int(value.get("delivered") or 0) == 0
        and int(value.get("pending") or 0) == 0
    ):
        value["state"] = "NO_CHANGE"
    return _strict(value)


def status(config: dict[str, Any]) -> dict[str, Any]:
    value = _status(config)
    pending = int(value.get("pending") or 0)
    delivered = int(value.get("delivered") or 0)
    value["state"] = "PENDING_HOME_CENTER" if pending else ("DELIVERED" if delivered else "IDLE")
    return _strict(value)


__all__ = [
    "ReceiptError",
    "build",
    "capture",
    "fingerprint",
    "flush",
    "jar_identity",
    "paths",
    "record",
    "resolve_jar",
    "settings",
    "status",
    "validate",
]
