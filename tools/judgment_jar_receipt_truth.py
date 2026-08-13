#!/usr/bin/env python3
"""Public receipt API with strict quarantine truth.

The storage module preserves malformed shards in terminal quarantine. This
facade ensures every CLI/daemon caller reports that quarantine as a failed
state instead of rounding an otherwise empty pending queue up to DELIVERED.
"""
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
    blocked = value.get("blocked")
    if not isinstance(blocked, dict):
        blocked = {
            "state": "QUARANTINED",
            "count": quarantined,
            "error": "One or more Judgment Jar receipt shards require explicit repair.",
        }
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
    return _strict(_flush(config, limit=limit, client_factory=client_factory, now_ms=now_ms))


def status(config: dict[str, Any]) -> dict[str, Any]:
    value = _status(config)
    value.setdefault("state", "PENDING_HOME_CENTER" if int(value.get("pending") or 0) else "DELIVERED")
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
