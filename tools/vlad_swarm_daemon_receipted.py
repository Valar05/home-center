#!/usr/bin/env python3
"""Receipt-aware entrypoint for the existing Vlad swarm daemon.

This is not a second watcher. It patches the canonical daemon heartbeat so the
same process synchronizes the repository-backed Jar catalog and retries the
oldest pending Jar usage receipt before ordinary health/review work.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import judgement_jar_runtime as jar_runtime
import vlad_swarm_daemon as daemon

_ORIGINAL_HEARTBEAT = daemon.heartbeat


def heartbeat(repo_root):
    try:
        pending = jar_runtime.sync_pending()
        catalog = jar_runtime.sync_catalog()
        daemon.append_receipt({
            "kind": "judgement.jar.sync.heartbeat",
            "ok": pending.get("ok") is True and catalog.get("ok") is True,
            "pendingState": pending.get("state"),
            "pendingRemaining": pending.get("remaining", 0),
            "catalogState": catalog.get("state"),
            "catalogSha256": catalog.get("snapshot", {}).get("catalogSha256"),
            "jarCount": catalog.get("snapshot", {}).get("count"),
            "sameDaemon": True,
        })
    except Exception as exc:
        daemon.append_receipt({
            "kind": "judgement.jar.sync.heartbeat",
            "ok": False,
            "state": "capture_or_sync_error",
            "error": f"{type(exc).__name__}: {exc}",
            "sameDaemon": True,
        })
    return _ORIGINAL_HEARTBEAT(repo_root)


daemon.heartbeat = heartbeat


def main():
    return daemon.main()


if __name__ == "__main__":
    raise SystemExit(main())
