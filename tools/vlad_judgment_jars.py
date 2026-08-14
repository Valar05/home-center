#!/usr/bin/env python3
"""Fast, receipt-bearing Judgment Jar access for Vlad.

Home Center is authoritative.  This tool stores a verified local SQLite snapshot for
low-latency/offline reads and a durable outbox for invocation receipts.  It never
promotes Vlad's cache into source truth.

The executable surface deliberately separates administrative lookup (``get``) from
actual jar use (``use``).  Every ``use`` opens a two-phase receipt; ``complete``
records what kind of output the jar produced and queues the receipt for Home Center.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import sqlite3
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

SCHEMA_VERSION = 1
DEFAULT_DB = "~/.local/share/vlad/judgment-jars.sqlite3"
DEFAULT_CONFIG = "config/judgment-jars.v1.json"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8767
DEFAULT_POLL_SECONDS = 300
DEFAULT_TIMEOUT_SECONDS = 20

OUTPUT_KINDS = {
    "verdict",
    "plan_review",
    "completion_review",
    "canon_review",
    "rewrite",
    "research_review",
    "risk_review",
    "routing_decision",
    "other",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def normalize_alias(value: str) -> str:
    return " ".join(
        "".join(ch.lower() if ch.isalnum() else " " for ch in value).split()
    )


def expand_path(value: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(value))).resolve()


def read_json_source(path: str) -> Any:
    if path == "-":
        return json.load(sys.stdin)
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def read_optional_text(text: str | None, path: str | None) -> str:
    if text is not None and path is not None:
        raise ValueError("Use either inline text or a file, not both")
    if path is not None:
        return Path(path).read_text(encoding="utf-8")
    return text or ""


def load_config(path: str | None) -> dict[str, Any]:
    candidate = path or DEFAULT_CONFIG
    config_path = Path(candidate)
    if not config_path.exists():
        return {}
    with config_path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("Judgment Jar config root must be an object")
    return value


def configured_db(config: Mapping[str, Any], override: str | None) -> Path:
    if override:
        return expand_path(override)
    vlad = config.get("vlad") if isinstance(config.get("vlad"), Mapping) else {}
    env_name = str(vlad.get("database_env") or "VLAD_JUDGMENT_JARS_DB")
    value = os.getenv(env_name) or str(vlad.get("default_database") or DEFAULT_DB)
    return expand_path(value)


def configured_url(
    config: Mapping[str, Any], override: str | None, key: str, default_env: str
) -> str | None:
    if override:
        return override
    sync = config.get("sync") if isinstance(config.get("sync"), Mapping) else {}
    env_name = str(sync.get(key) or default_env)
    return os.getenv(env_name)


def configured_token(config: Mapping[str, Any]) -> str | None:
    sync = config.get("sync") if isinstance(config.get("sync"), Mapping) else {}
    env_name = str(sync.get("bearer_token_env") or "HOME_CENTER_TOKEN")
    return os.getenv(env_name)


def configured_int(
    config: Mapping[str, Any], section: str, key: str, default: int
) -> int:
    block = config.get(section) if isinstance(config.get(section), Mapping) else {}
    try:
        return int(block.get(key, default))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class NormalizedJar:
    jar_id: str
    title: str
    aliases: tuple[str, ...]
    jurisdiction: str
    body: str
    source_ref: str
    source_revision: str
    status: str
    source_updated_at: str
    content_sha256: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "jar_id": self.jar_id,
            "title": self.title,
            "aliases": list(self.aliases),
            "jurisdiction": self.jurisdiction,
            "body": self.body,
            "source_ref": self.source_ref,
            "source_revision": self.source_revision,
            "status": self.status,
            "source_updated_at": self.source_updated_at,
            "content_sha256": self.content_sha256,
        }


def _first_text(record: Mapping[str, Any], keys: Sequence[str]) -> str:
    for key in keys:
        value = record.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def normalize_jar(record: Mapping[str, Any]) -> NormalizedJar:
    jar_id = _first_text(record, ("jar_id", "id", "canonical_id", "slug"))
    title = _first_text(record, ("title", "name", "display_name"))
    if not jar_id:
        if not title:
            raise ValueError("Jar record requires jar_id/id or title/name")
        jar_id = normalize_alias(title).replace(" ", "-")
    if not title:
        title = jar_id

    raw_aliases = record.get("aliases") or []
    if isinstance(raw_aliases, str):
        raw_aliases = [raw_aliases]
    if not isinstance(raw_aliases, Sequence):
        raise ValueError(f"Jar {jar_id}: aliases must be a list or string")

    aliases: list[str] = [title, jar_id]
    aliases.extend(str(value).strip() for value in raw_aliases if str(value).strip())
    deduped: list[str] = []
    seen: set[str] = set()
    for alias in aliases:
        normalized = normalize_alias(alias)
        if normalized and normalized not in seen:
            seen.add(normalized)
            deduped.append(alias)

    body = _first_text(record, ("body", "prompt", "content", "material", "text"))
    jurisdiction = _first_text(record, ("jurisdiction", "criterion", "purpose", "role"))
    source_ref = _first_text(record, ("source_ref", "source_url", "document_id", "file_id"))
    source_revision = _first_text(
        record, ("source_revision", "revision", "revision_id", "version")
    )
    status = _first_text(record, ("status",)) or "active"
    source_updated_at = _first_text(
        record, ("source_updated_at", "updated_at", "modified_at", "observed_at")
    )

    digest_payload = {
        "jar_id": jar_id,
        "title": title,
        "aliases": deduped,
        "jurisdiction": jurisdiction,
        "body": body,
        "source_ref": source_ref,
        "source_revision": source_revision,
        "status": status,
        "source_updated_at": source_updated_at,
    }
    digest = _first_text(record, ("content_sha256", "sha256")) or sha256_text(
        canonical_json(digest_payload)
    )
    return NormalizedJar(
        jar_id=jar_id,
        title=title,
        aliases=tuple(deduped),
        jurisdiction=jurisdiction,
        body=body,
        source_ref=source_ref,
        source_revision=source_revision,
        status=status,
        source_updated_at=source_updated_at,
        content_sha256=digest,
    )


class Registry:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    def _initialize(self) -> None:
        with self._lock, self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS jars (
                    jar_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    aliases_json TEXT NOT NULL,
                    jurisdiction TEXT NOT NULL,
                    body TEXT NOT NULL,
                    source_ref TEXT NOT NULL,
                    source_revision TEXT NOT NULL,
                    status TEXT NOT NULL,
                    source_updated_at TEXT NOT NULL,
                    content_sha256 TEXT NOT NULL,
                    snapshot_seen_at TEXT NOT NULL,
                    tombstoned_at TEXT
                );

                CREATE TABLE IF NOT EXISTS aliases (
                    alias_normalized TEXT PRIMARY KEY,
                    jar_id TEXT NOT NULL REFERENCES jars(jar_id) ON DELETE CASCADE,
                    alias_display TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_aliases_jar_id ON aliases(jar_id);
                CREATE INDEX IF NOT EXISTS idx_jars_title ON jars(title);
                CREATE INDEX IF NOT EXISTS idx_jars_status ON jars(status);

                CREATE TABLE IF NOT EXISTS receipts (
                    receipt_id TEXT PRIMARY KEY,
                    jar_id TEXT NOT NULL,
                    jar_revision TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    worker TEXT NOT NULL,
                    campaign TEXT NOT NULL,
                    input_sha256 TEXT NOT NULL,
                    opened_at TEXT NOT NULL,
                    output_kind TEXT,
                    output_ref TEXT,
                    output_sha256 TEXT,
                    status TEXT NOT NULL,
                    closed_at TEXT,
                    delivery_state TEXT NOT NULL,
                    delivery_attempts INTEGER NOT NULL DEFAULT 0,
                    delivered_at TEXT,
                    last_error TEXT,
                    UNIQUE(request_id, jar_id)
                );
                CREATE INDEX IF NOT EXISTS idx_receipts_delivery
                    ON receipts(delivery_state, opened_at);
                CREATE INDEX IF NOT EXISTS idx_receipts_request
                    ON receipts(request_id);
                """
            )
            connection.execute(
                "INSERT OR IGNORE INTO meta(key, value) VALUES('schema_version', ?)",
                (str(SCHEMA_VERSION),),
            )

    @staticmethod
    def _set_meta(connection: sqlite3.Connection, key: str, value: str) -> None:
        connection.execute(
            """
            INSERT INTO meta(key, value) VALUES(?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )

    @staticmethod
    def _get_meta(connection: sqlite3.Connection, key: str) -> str | None:
        row = connection.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return str(row["value"]) if row else None

    def import_snapshot(self, payload: Any, etag: str | None = None) -> dict[str, Any]:
        if isinstance(payload, list):
            raw_jars = payload
            source = "unspecified"
            complete = False
            observed_at = utc_now()
        elif isinstance(payload, Mapping):
            raw_jars = payload.get("jars")
            source = str(payload.get("source") or "home-center")
            complete = bool(payload.get("complete", True))
            observed_at = str(payload.get("observed_at") or utc_now())
        else:
            raise ValueError("Snapshot must be an object or a list of jar records")

        if not isinstance(raw_jars, list):
            raise ValueError("Snapshot object requires a jars array")
        normalized = [normalize_jar(record) for record in raw_jars if isinstance(record, Mapping)]
        if len(normalized) != len(raw_jars):
            raise ValueError("Every snapshot jar entry must be an object")

        ids = [jar.jar_id for jar in normalized]
        if len(ids) != len(set(ids)):
            raise ValueError("Snapshot contains duplicate jar_id values")

        snapshot_material = {
            "schema_version": SCHEMA_VERSION,
            "source": source,
            "complete": complete,
            "jars": [jar.as_dict() for jar in sorted(normalized, key=lambda item: item.jar_id)],
        }
        snapshot_sha256 = sha256_text(canonical_json(snapshot_material))
        inserted = 0
        updated = 0
        unchanged = 0
        tombstoned = 0

        with self._lock, self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            for jar in normalized:
                existing = connection.execute(
                    "SELECT content_sha256 FROM jars WHERE jar_id = ?", (jar.jar_id,)
                ).fetchone()
                if existing is None:
                    inserted += 1
                elif existing["content_sha256"] != jar.content_sha256:
                    updated += 1
                else:
                    unchanged += 1

                connection.execute(
                    """
                    INSERT INTO jars(
                        jar_id, title, aliases_json, jurisdiction, body, source_ref,
                        source_revision, status, source_updated_at, content_sha256,
                        snapshot_seen_at, tombstoned_at
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                    ON CONFLICT(jar_id) DO UPDATE SET
                        title = excluded.title,
                        aliases_json = excluded.aliases_json,
                        jurisdiction = excluded.jurisdiction,
                        body = excluded.body,
                        source_ref = excluded.source_ref,
                        source_revision = excluded.source_revision,
                        status = excluded.status,
                        source_updated_at = excluded.source_updated_at,
                        content_sha256 = excluded.content_sha256,
                        snapshot_seen_at = excluded.snapshot_seen_at,
                        tombstoned_at = NULL
                    """,
                    (
                        jar.jar_id,
                        jar.title,
                        canonical_json(list(jar.aliases)),
                        jar.jurisdiction,
                        jar.body,
                        jar.source_ref,
                        jar.source_revision,
                        jar.status,
                        jar.source_updated_at,
                        jar.content_sha256,
                        observed_at,
                    ),
                )
                connection.execute("DELETE FROM aliases WHERE jar_id = ?", (jar.jar_id,))
                for alias in jar.aliases:
                    normalized_alias = normalize_alias(alias)
                    collision = connection.execute(
                        "SELECT jar_id FROM aliases WHERE alias_normalized = ?",
                        (normalized_alias,),
                    ).fetchone()
                    if collision and collision["jar_id"] != jar.jar_id:
                        raise ValueError(
                            f"Alias collision: {alias!r} belongs to both "
                            f"{collision['jar_id']} and {jar.jar_id}"
                        )
                    connection.execute(
                        """
                        INSERT INTO aliases(alias_normalized, jar_id, alias_display)
                        VALUES(?, ?, ?)
                        ON CONFLICT(alias_normalized) DO UPDATE SET
                            jar_id = excluded.jar_id,
                            alias_display = excluded.alias_display
                        """,
                        (normalized_alias, jar.jar_id, alias),
                    )

            if complete:
                if ids:
                    placeholders = ",".join("?" for _ in ids)
                    rows = connection.execute(
                        f"""
                        SELECT jar_id FROM jars
                        WHERE jar_id NOT IN ({placeholders}) AND tombstoned_at IS NULL
                        """,
                        ids,
                    ).fetchall()
                    tombstoned = len(rows)
                    connection.execute(
                        f"""
                        UPDATE jars
                        SET status = 'tombstoned', tombstoned_at = ?
                        WHERE jar_id NOT IN ({placeholders}) AND tombstoned_at IS NULL
                        """,
                        [observed_at, *ids],
                    )
                else:
                    row = connection.execute(
                        "SELECT COUNT(*) AS count FROM jars WHERE tombstoned_at IS NULL"
                    ).fetchone()
                    tombstoned = int(row["count"])
                    connection.execute(
                        """
                        UPDATE jars SET status = 'tombstoned', tombstoned_at = ?
                        WHERE tombstoned_at IS NULL
                        """,
                        (observed_at,),
                    )

            self._set_meta(connection, "snapshot_source", source)
            self._set_meta(connection, "snapshot_complete", "true" if complete else "false")
            self._set_meta(connection, "snapshot_observed_at", observed_at)
            self._set_meta(connection, "snapshot_sha256", snapshot_sha256)
            self._set_meta(connection, "last_sync_at", utc_now())
            if etag:
                self._set_meta(connection, "snapshot_etag", etag)
            connection.commit()

        return {
            "status": "synced",
            "inserted": inserted,
            "updated": updated,
            "unchanged": unchanged,
            "tombstoned": tombstoned,
            "jar_count": len(normalized),
            "snapshot_sha256": snapshot_sha256,
            "snapshot_complete": complete,
            "source": source,
            "observed_at": observed_at,
        }

    @staticmethod
    def _row_to_jar(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "jar_id": row["jar_id"],
            "title": row["title"],
            "aliases": json.loads(row["aliases_json"]),
            "jurisdiction": row["jurisdiction"],
            "body": row["body"],
            "source_ref": row["source_ref"],
            "source_revision": row["source_revision"],
            "status": row["status"],
            "source_updated_at": row["source_updated_at"],
            "content_sha256": row["content_sha256"],
            "snapshot_seen_at": row["snapshot_seen_at"],
            "tombstoned_at": row["tombstoned_at"],
        }

    def resolve(self, key: str, include_tombstoned: bool = False) -> dict[str, Any] | None:
        normalized = normalize_alias(key)
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT j.* FROM jars j
                LEFT JOIN aliases a ON a.jar_id = j.jar_id
                WHERE j.jar_id = ? OR a.alias_normalized = ?
                ORDER BY CASE WHEN j.jar_id = ? THEN 0 ELSE 1 END
                LIMIT 1
                """,
                (key, normalized, key),
            ).fetchone()
            if row is None:
                return None
            jar = self._row_to_jar(row)
            if not include_tombstoned and jar["status"] == "tombstoned":
                return None
            return jar

    def list_jars(self, include_tombstoned: bool = False) -> list[dict[str, Any]]:
        with self.connect() as connection:
            if include_tombstoned:
                rows = connection.execute("SELECT * FROM jars ORDER BY title, jar_id").fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM jars WHERE status != 'tombstoned' ORDER BY title, jar_id"
                ).fetchall()
        return [self._row_to_jar(row) for row in rows]

    def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        tokens = [token for token in normalize_alias(query).split() if token]
        if not tokens:
            return []
        clauses: list[str] = []
        params: list[Any] = []
        for token in tokens:
            pattern = f"%{token}%"
            clauses.append(
                "(lower(j.title) LIKE ? OR lower(j.jurisdiction) LIKE ? "
                "OR lower(j.body) LIKE ? OR a.alias_normalized LIKE ?)"
            )
            params.extend((pattern, pattern, pattern, pattern))
        params.append(max(1, min(limit, 200)))
        sql = f"""
            SELECT DISTINCT j.* FROM jars j
            LEFT JOIN aliases a ON a.jar_id = j.jar_id
            WHERE j.status != 'tombstoned' AND {' AND '.join(clauses)}
            ORDER BY j.title, j.jar_id
            LIMIT ?
        """
        with self.connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [self._row_to_jar(row) for row in rows]

    def open_use(
        self,
        key: str,
        request_id: str,
        worker: str,
        campaign: str,
        input_text: str,
    ) -> dict[str, Any]:
        jar = self.resolve(key)
        if jar is None:
            raise KeyError(f"Unknown active Judgment Jar: {key}")
        if not request_id.strip():
            raise ValueError("request_id is required")
        receipt_id = str(uuid.uuid4())
        opened_at = utc_now()
        input_digest = sha256_text(input_text)
        jar_revision = jar["source_revision"] or jar["content_sha256"]
        with self._lock, self.connect() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO receipts(
                        receipt_id, jar_id, jar_revision, request_id, worker,
                        campaign, input_sha256, opened_at, status, delivery_state
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, 'open', 'not_ready')
                    """,
                    (
                        receipt_id,
                        jar["jar_id"],
                        jar_revision,
                        request_id,
                        worker,
                        campaign,
                        input_digest,
                        opened_at,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                existing = connection.execute(
                    """
                    SELECT receipt_id FROM receipts
                    WHERE request_id = ? AND jar_id = ?
                    """,
                    (request_id, jar["jar_id"]),
                ).fetchone()
                if existing:
                    raise ValueError(
                        f"Jar {jar['jar_id']} already used for request {request_id}; "
                        f"receipt={existing['receipt_id']}"
                    ) from exc
                raise
        return {
            "receipt": {
                "receipt_id": receipt_id,
                "jar_id": jar["jar_id"],
                "jar_revision": jar_revision,
                "request_id": request_id,
                "worker": worker,
                "campaign": campaign,
                "input_sha256": input_digest,
                "opened_at": opened_at,
                "status": "open",
            },
            "jar": jar,
        }

    def complete_use(
        self,
        receipt_id: str,
        output_kind: str,
        output_ref: str,
        output_text: str,
        status: str = "completed",
    ) -> dict[str, Any]:
        if output_kind not in OUTPUT_KINDS:
            raise ValueError(
                f"Unsupported output_kind {output_kind!r}; expected one of "
                f"{', '.join(sorted(OUTPUT_KINDS))}"
            )
        if status not in {"completed", "failed", "rejected", "blocked"}:
            raise ValueError("status must be completed, failed, rejected, or blocked")
        closed_at = utc_now()
        output_digest = sha256_text(output_text)
        with self._lock, self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM receipts WHERE receipt_id = ?", (receipt_id,)
            ).fetchone()
            if row is None:
                raise KeyError(f"Unknown receipt: {receipt_id}")
            if row["status"] != "open":
                raise ValueError(
                    f"Receipt {receipt_id} is already terminal with status={row['status']}"
                )
            connection.execute(
                """
                UPDATE receipts SET
                    output_kind = ?, output_ref = ?, output_sha256 = ?,
                    status = ?, closed_at = ?, delivery_state = 'pending',
                    last_error = NULL
                WHERE receipt_id = ?
                """,
                (output_kind, output_ref, output_digest, status, closed_at, receipt_id),
            )
            updated = connection.execute(
                "SELECT * FROM receipts WHERE receipt_id = ?", (receipt_id,)
            ).fetchone()
        return dict(updated)

    def pending_receipts(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM receipts
                WHERE delivery_state = 'pending'
                ORDER BY opened_at ASC, receipt_id ASC
                LIMIT ?
                """,
                (max(1, min(limit, 1000)),),
            ).fetchall()
        return [dict(row) for row in rows]

    def mark_receipts_delivered(self, receipt_ids: Iterable[str]) -> int:
        ids = list(dict.fromkeys(receipt_ids))
        if not ids:
            return 0
        placeholders = ",".join("?" for _ in ids)
        delivered_at = utc_now()
        with self._lock, self.connect() as connection:
            cursor = connection.execute(
                f"""
                UPDATE receipts SET delivery_state = 'delivered', delivered_at = ?,
                    last_error = NULL
                WHERE receipt_id IN ({placeholders}) AND delivery_state = 'pending'
                """,
                [delivered_at, *ids],
            )
        return int(cursor.rowcount)

    def mark_receipt_attempt_failure(self, receipt_ids: Iterable[str], error: str) -> None:
        ids = list(dict.fromkeys(receipt_ids))
        if not ids:
            return
        placeholders = ",".join("?" for _ in ids)
        with self._lock, self.connect() as connection:
            connection.execute(
                f"""
                UPDATE receipts SET
                    delivery_attempts = delivery_attempts + 1,
                    last_error = ?
                WHERE receipt_id IN ({placeholders}) AND delivery_state = 'pending'
                """,
                [error[:2000], *ids],
            )

    def status(self) -> dict[str, Any]:
        with self.connect() as connection:
            meta_rows = connection.execute("SELECT key, value FROM meta ORDER BY key").fetchall()
            jar_counts = connection.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN status != 'tombstoned' THEN 1 ELSE 0 END) AS active,
                    SUM(CASE WHEN status = 'tombstoned' THEN 1 ELSE 0 END) AS tombstoned
                FROM jars
                """
            ).fetchone()
            receipt_counts = connection.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) AS open,
                    SUM(CASE WHEN delivery_state = 'pending' THEN 1 ELSE 0 END) AS pending,
                    SUM(CASE WHEN delivery_state = 'delivered' THEN 1 ELSE 0 END) AS delivered
                FROM receipts
                """
            ).fetchone()
        return {
            "schema_version": SCHEMA_VERSION,
            "database": str(self.db_path),
            "meta": {row["key"]: row["value"] for row in meta_rows},
            "jars": {key: int(jar_counts[key] or 0) for key in jar_counts.keys()},
            "receipts": {key: int(receipt_counts[key] or 0) for key in receipt_counts.keys()},
        }

    def get_etag(self) -> str | None:
        with self.connect() as connection:
            return self._get_meta(connection, "snapshot_etag")


class HomeCenterSync:
    def __init__(
        self,
        registry: Registry,
        snapshot_url: str | None,
        receipt_url: str | None,
        token: str | None,
        timeout: int,
    ):
        self.registry = registry
        self.snapshot_url = snapshot_url
        self.receipt_url = receipt_url
        self.token = token
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "User-Agent": "vlad-judgment-jars/1"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def pull(self) -> dict[str, Any]:
        if not self.snapshot_url:
            return {"status": "skipped", "reason": "snapshot URL is not configured"}
        headers = self._headers()
        etag = self.registry.get_etag()
        if etag:
            headers["If-None-Match"] = etag
        request = urllib.request.Request(self.snapshot_url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = response.read()
                payload = json.loads(data.decode("utf-8"))
                response_etag = response.headers.get("ETag")
                return self.registry.import_snapshot(payload, etag=response_etag)
        except urllib.error.HTTPError as exc:
            if exc.code == HTTPStatus.NOT_MODIFIED:
                return {"status": "unchanged", "etag": etag}
            detail = exc.read().decode("utf-8", errors="replace")[:2000]
            raise RuntimeError(f"Home Center snapshot HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Home Center snapshot pull failed: {exc}") from exc

    def push_receipts(self, limit: int = 100) -> dict[str, Any]:
        pending = self.registry.pending_receipts(limit=limit)
        if not pending:
            return {"status": "idle", "pending": 0}
        if not self.receipt_url:
            return {
                "status": "queued",
                "pending": len(pending),
                "reason": "receipt URL is not configured",
            }
        payload = canonical_json(
            {
                "schema_version": SCHEMA_VERSION,
                "source": "vlad",
                "receipts": pending,
            }
        ).encode("utf-8")
        headers = self._headers()
        headers["Content-Type"] = "application/json"
        headers["Idempotency-Key"] = sha256_bytes(payload)
        request = urllib.request.Request(
            self.receipt_url, data=payload, headers=headers, method="POST"
        )
        ids = [str(item["receipt_id"]) for item in pending]
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read()
                accepted_ids = ids
                if body:
                    decoded = json.loads(body.decode("utf-8"))
                    if isinstance(decoded, Mapping) and isinstance(decoded.get("accepted"), list):
                        accepted_ids = [str(value) for value in decoded["accepted"]]
                count = self.registry.mark_receipts_delivered(accepted_ids)
                return {
                    "status": "delivered",
                    "attempted": len(ids),
                    "delivered": count,
                    "accepted": accepted_ids,
                }
        except Exception as exc:
            self.registry.mark_receipt_attempt_failure(ids, str(exc))
            if isinstance(exc, urllib.error.HTTPError):
                detail = exc.read().decode("utf-8", errors="replace")[:2000]
                raise RuntimeError(f"Home Center receipt HTTP {exc.code}: {detail}") from exc
            raise RuntimeError(f"Home Center receipt push failed: {exc}") from exc

    def sync_once(self) -> dict[str, Any]:
        result: dict[str, Any] = {"pulled": None, "pushed": None}
        try:
            result["pulled"] = self.pull()
        except Exception as exc:
            result["pulled"] = {"status": "error", "error": str(exc)}
        try:
            result["pushed"] = self.push_receipts()
        except Exception as exc:
            result["pushed"] = {"status": "error", "error": str(exc)}
        return result


class JsonHandler(BaseHTTPRequestHandler):
    registry: Registry
    sync: HomeCenterSync

    server_version = "VladJudgmentJars/1"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"{self.log_date_time_string()} {fmt % args}", file=sys.stderr)

    def _send(self, status: int, payload: Any) -> None:
        data = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _body(self) -> dict[str, Any]:
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("Invalid Content-Length") from exc
        if size <= 0:
            return {}
        if size > 10 * 1024 * 1024:
            raise ValueError("Request body exceeds 10 MiB")
        value = json.loads(self.rfile.read(size).decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("JSON body must be an object")
        return value

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        try:
            if parsed.path == "/v1/status":
                self._send(200, self.registry.status())
                return
            if parsed.path == "/v1/jars":
                self._send(200, {"jars": self.registry.list_jars()})
                return
            if parsed.path == "/v1/search":
                query = urllib.parse.parse_qs(parsed.query).get("q", [""])[0]
                self._send(200, {"query": query, "jars": self.registry.search(query)})
                return
            if parsed.path.startswith("/v1/jars/"):
                key = urllib.parse.unquote(parsed.path[len("/v1/jars/") :])
                jar = self.registry.resolve(key)
                if jar is None:
                    self._send(404, {"error": "jar_not_found", "key": key})
                else:
                    self._send(
                        200,
                        {
                            "jar": jar,
                            "warning": "Administrative lookup only. Use POST /v1/use for actual judgment so a receipt is opened.",
                        },
                    )
                return
            self._send(404, {"error": "not_found"})
        except Exception as exc:
            self._send(500, {"error": type(exc).__name__, "message": str(exc)})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        try:
            body = self._body()
            if parsed.path == "/v1/use":
                result = self.registry.open_use(
                    key=str(body.get("jar") or body.get("jar_id") or ""),
                    request_id=str(body.get("request_id") or ""),
                    worker=str(body.get("worker") or "vlad"),
                    campaign=str(body.get("campaign") or ""),
                    input_text=str(body.get("input") or ""),
                )
                self._send(201, result)
                return
            if parsed.path.startswith("/v1/receipts/") and parsed.path.endswith("/complete"):
                receipt_id = urllib.parse.unquote(
                    parsed.path[len("/v1/receipts/") : -len("/complete")].rstrip("/")
                )
                result = self.registry.complete_use(
                    receipt_id=receipt_id,
                    output_kind=str(body.get("output_kind") or "other"),
                    output_ref=str(body.get("output_ref") or ""),
                    output_text=str(body.get("output") or ""),
                    status=str(body.get("status") or "completed"),
                )
                self._send(200, {"receipt": result})
                return
            if parsed.path == "/v1/sync":
                self._send(200, self.sync.sync_once())
                return
            self._send(404, {"error": "not_found"})
        except KeyError as exc:
            self._send(404, {"error": "not_found", "message": str(exc)})
        except (ValueError, json.JSONDecodeError) as exc:
            self._send(400, {"error": "invalid_request", "message": str(exc)})
        except Exception as exc:
            self._send(500, {"error": type(exc).__name__, "message": str(exc)})


def make_handler(registry: Registry, sync: HomeCenterSync) -> type[JsonHandler]:
    class BoundHandler(JsonHandler):
        pass

    BoundHandler.registry = registry
    BoundHandler.sync = sync
    return BoundHandler


def run_server(
    registry: Registry,
    sync: HomeCenterSync,
    host: str,
    port: int,
    stop_event: threading.Event | None = None,
) -> None:
    server = ThreadingHTTPServer((host, port), make_handler(registry, sync))
    server.daemon_threads = True
    if stop_event is None:
        server.serve_forever()
        return
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    stop_event.wait()
    server.shutdown()
    server.server_close()
    thread.join(timeout=10)


def run_daemon(
    registry: Registry,
    sync: HomeCenterSync,
    host: str,
    port: int,
    poll_seconds: int,
) -> None:
    stop_event = threading.Event()

    def stop_handler(signum: int, frame: Any) -> None:
        del signum, frame
        stop_event.set()

    signal.signal(signal.SIGINT, stop_handler)
    signal.signal(signal.SIGTERM, stop_handler)

    def loop() -> None:
        while not stop_event.is_set():
            result = sync.sync_once()
            print(canonical_json({"event": "sync", "at": utc_now(), **result}), flush=True)
            stop_event.wait(max(5, poll_seconds))

    sync_thread = threading.Thread(target=loop, daemon=True)
    sync_thread.start()
    try:
        run_server(registry, sync, host, port, stop_event=stop_event)
    finally:
        stop_event.set()
        sync_thread.join(timeout=10)


def print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", help=f"Config path (default: {DEFAULT_CONFIG})")
    parser.add_argument("--db", help="SQLite database path")
    sub = parser.add_subparsers(dest="command", required=True)

    sync_file = sub.add_parser("sync-file", help="Import a Home Center snapshot JSON file")
    sync_file.add_argument("snapshot", help="Snapshot JSON path, or - for stdin")

    pull = sub.add_parser("pull", help="Pull the authoritative snapshot from Home Center")
    pull.add_argument("--url", help="Override Home Center snapshot URL")

    push = sub.add_parser("push-receipts", help="Push oldest pending receipts to Home Center")
    push.add_argument("--url", help="Override Home Center receipt URL")
    push.add_argument("--limit", type=int, default=100)

    sub.add_parser("sync", help="Pull snapshot and push pending receipts once")

    list_parser = sub.add_parser("list", help="List cached jars")
    list_parser.add_argument("--include-tombstoned", action="store_true")

    get = sub.add_parser("get", help="Administrative jar lookup; does not count as use")
    get.add_argument("jar")
    get.add_argument("--include-tombstoned", action="store_true")

    search = sub.add_parser("search", help="Search the local cache")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=20)

    use = sub.add_parser("use", help="Open a receipt and retrieve a jar for judgment")
    use.add_argument("jar")
    use.add_argument("--request-id", required=True)
    use.add_argument("--worker", default="vlad")
    use.add_argument("--campaign", default="")
    use.add_argument("--input-text")
    use.add_argument("--input-file")

    complete = sub.add_parser("complete", help="Close a jar-use receipt and queue it")
    complete.add_argument("receipt_id")
    complete.add_argument("--output-kind", required=True, choices=sorted(OUTPUT_KINDS))
    complete.add_argument("--output-ref", default="")
    complete.add_argument("--output-text")
    complete.add_argument("--output-file")
    complete.add_argument(
        "--status", default="completed", choices=("completed", "failed", "rejected", "blocked")
    )

    pending = sub.add_parser("pending", help="Show pending receipt outbox")
    pending.add_argument("--limit", type=int, default=100)

    sub.add_parser("status", help="Show cache and receipt state")

    serve = sub.add_parser("serve", help="Serve the loopback fast-access API")
    serve.add_argument("--host")
    serve.add_argument("--port", type=int)

    daemon = sub.add_parser("daemon", help="Serve Vlad and continuously sync Home Center")
    daemon.add_argument("--host")
    daemon.add_argument("--port", type=int)
    daemon.add_argument("--poll-seconds", type=int)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        registry = Registry(configured_db(config, args.db))
        snapshot_url = configured_url(
            config, getattr(args, "url", None) if args.command == "pull" else None,
            "snapshot_url_env", "HOME_CENTER_JUDGMENT_JARS_SNAPSHOT_URL"
        )
        receipt_url = configured_url(
            config, getattr(args, "url", None) if args.command == "push-receipts" else None,
            "receipt_url_env", "HOME_CENTER_JUDGMENT_JARS_RECEIPT_URL"
        )
        timeout = configured_int(config, "sync", "timeout_seconds", DEFAULT_TIMEOUT_SECONDS)
        sync = HomeCenterSync(
            registry=registry,
            snapshot_url=snapshot_url,
            receipt_url=receipt_url,
            token=configured_token(config),
            timeout=timeout,
        )

        if args.command == "sync-file":
            print_json(registry.import_snapshot(read_json_source(args.snapshot)))
        elif args.command == "pull":
            print_json(sync.pull())
        elif args.command == "push-receipts":
            print_json(sync.push_receipts(limit=args.limit))
        elif args.command == "sync":
            print_json(sync.sync_once())
        elif args.command == "list":
            print_json({"jars": registry.list_jars(args.include_tombstoned)})
        elif args.command == "get":
            jar = registry.resolve(args.jar, args.include_tombstoned)
            if jar is None:
                raise KeyError(f"Unknown Judgment Jar: {args.jar}")
            print_json(
                {
                    "jar": jar,
                    "warning": "Administrative lookup only. Use `use` for actual judgment so a receipt is opened.",
                }
            )
        elif args.command == "search":
            print_json({"query": args.query, "jars": registry.search(args.query, args.limit)})
        elif args.command == "use":
            input_text = read_optional_text(args.input_text, args.input_file)
            print_json(
                registry.open_use(
                    args.jar, args.request_id, args.worker, args.campaign, input_text
                )
            )
        elif args.command == "complete":
            output_text = read_optional_text(args.output_text, args.output_file)
            print_json(
                {
                    "receipt": registry.complete_use(
                        args.receipt_id,
                        args.output_kind,
                        args.output_ref,
                        output_text,
                        args.status,
                    )
                }
            )
        elif args.command == "pending":
            print_json({"receipts": registry.pending_receipts(args.limit)})
        elif args.command == "status":
            print_json(registry.status())
        elif args.command in {"serve", "daemon"}:
            vlad = config.get("vlad") if isinstance(config.get("vlad"), Mapping) else {}
            host = args.host or str(vlad.get("local_http_host") or DEFAULT_HOST)
            port = args.port or int(vlad.get("local_http_port") or DEFAULT_PORT)
            if host not in {"127.0.0.1", "localhost", "::1"}:
                raise ValueError("Fast-access API must bind to loopback unless code is explicitly changed")
            if args.command == "serve":
                run_server(registry, sync, host, port)
            else:
                poll = args.poll_seconds or configured_int(
                    config, "sync", "poll_seconds", DEFAULT_POLL_SECONDS
                )
                run_daemon(registry, sync, host, port, poll)
        else:
            parser.error(f"Unsupported command: {args.command}")
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print_json({"status": "error", "error": type(exc).__name__, "message": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
