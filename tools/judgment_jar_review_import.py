#!/usr/bin/env python3
"""Convert durable Venice review records into typed Judgment Jar receipts."""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from pathlib import Path
from typing import Any

from judgment_jar_common import normalize_key, write_atomic
from judgment_jar_receipts import build, capture, fingerprint


def _state_root() -> Path:
    return Path(os.path.expanduser(os.environ.get("HC_STATE_DIR", "~/.local/state/home-center")))


def _receipt_root(config: dict[str, Any]) -> Path:
    raw = config.get("receipts") or {}
    env_name = str(raw.get("stateDirEnv") or "HC_JUDGMENT_JAR_RECEIPT_STATE_DIR")
    return Path(os.environ.get(env_name, str(raw.get("stateDir") or "~/.local/state/home-center/vlad-swarm/judgment-jar-receipts"))).expanduser()


def _sources() -> list[Path]:
    root = _state_root()
    return [
        root / "venice" / "plan-reviews.jsonl",
        root / "adam-daemon" / "venice-plan-reviews.jsonl",
        root / "adam-daemon" / "venice-reviews.jsonl",
    ]


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _relative_jar_path(value: str) -> str:
    text = str(value or "").replace("\\", "/")
    marker = ".continue/rules/"
    index = text.find(marker)
    return text[index:] if index >= 0 else text


def _resolve(registry: dict[str, Any], reference: str) -> dict[str, Any] | None:
    raw = str(reference or "").strip()
    if not raw:
        return None
    relative = _relative_jar_path(raw)
    for jar in registry.get("jars") or []:
        if relative == str(jar.get("sourcePath") or ""):
            return jar
        if raw == str(jar.get("id") or "") or raw == str(jar.get("title") or ""):
            return jar
    key = normalize_key(raw)
    jar_id = (registry.get("aliasIndex") or {}).get(key, key)
    return next((jar for jar in registry.get("jars") or [] if jar.get("id") == jar_id), None)


def _references(record: dict[str, Any], source: Path) -> list[str]:
    found: list[str] = []
    for field in ("selectedJudgmentJars", "selectedJarManifest", "selectedJars"):
        value = record.get(field)
        if not isinstance(value, list):
            continue
        for item in value:
            if isinstance(item, dict):
                candidate = item.get("path") or item.get("sourcePath") or item.get("id") or item.get("title")
            else:
                candidate = item
            if candidate and str(candidate) not in found:
                found.append(str(candidate))
    if source.name == "venice-reviews.jsonl":
        found.append(".continue/rules/70-judgement-jar-venice-review-gate.md")
    if not found and "plan" in source.name:
        found.append(".continue/rules/70-judgement-jar-venice-review-gate.md")
    return found


def _status(record: dict[str, Any]) -> str:
    directive = str(record.get("directive") or "").upper()
    if directive in {"PLAN_ALLOWED", "STOP_ALLOWED"}:
        return "allowed"
    if directive in {"REPLAN_REQUIRED", "CONTINUE_REQUIRED"}:
        return "continue_required"
    if directive == "HALT_REQUIRED":
        return "halted"
    return str(record.get("verdict") or "created").lower()


def _summary(record: dict[str, Any]) -> str:
    verdict = str(record.get("verdict") or "UNKNOWN")
    directive = str(record.get("directive") or "UNKNOWN")
    findings = [str(value) for value in record.get("findings") or [] if str(value).strip()]
    suffix = "; ".join(findings[:3])
    return f"Venice review created {verdict}/{directive}" + (f": {suffix}" if suffix else "")


def _quarantine(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def import_review_receipts(registry: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    root = _receipt_root(config)
    cursor_path = root / "review-import-cursors.json"
    quarantine_path = root / "review-import-quarantine.jsonl"
    cursors: dict[str, int] = {}
    if cursor_path.is_file():
        try:
            loaded = json.loads(cursor_path.read_text(encoding="utf-8"))
            cursors = {str(key): int(value) for key, value in (loaded.get("lines") or {}).items()}
        except (OSError, ValueError, json.JSONDecodeError):
            cursors = {}

    imported = duplicates = quarantined = 0
    source_results: list[dict[str, Any]] = []
    for source in _sources():
        if not source.is_file():
            source_results.append({"source": str(source), "state": "ABSENT"})
            continue
        lines = source.read_text(encoding="utf-8", errors="replace").splitlines()
        start = max(0, cursors.get(str(source), 0))
        source_imported = source_duplicates = source_quarantined = 0
        for index, raw in enumerate(lines[start:], start=start):
            if not raw.strip():
                cursors[str(source)] = index + 1
                continue
            try:
                record = json.loads(raw)
                if not isinstance(record, dict):
                    raise ValueError("review record is not an object")
                jars: list[dict[str, Any]] = []
                for reference in _references(record, source):
                    jar = _resolve(registry, reference)
                    if jar and jar.get("id") not in {item.get("id") for item in jars}:
                        jars.append(jar)
                if not jars:
                    raise ValueError("review record has no resolvable Judgment Jar")
                canonical = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                source_hash = _sha(canonical)
                for jar in jars:
                    receipt = build(
                        registry,
                        jar,
                        output_kind="review_verdict",
                        output_text=canonical,
                        summary=_summary(record),
                        actor=str(record.get("reviewer") or "Venice"),
                        intent="perform the mandatory Judgment Jar review gate",
                        surface="vlad",
                        decision_action=str(record.get("directive") or record.get("verdict") or "reviewed"),
                        input_text=str(record.get("commission") or record.get("task") or canonical),
                        output_status=_status(record),
                        request_id=f"venice-review:{source_hash}",
                        group_id=f"{source}:{index + 1}",
                        references=[str(source), str(record.get("receipt") or "")],
                        source="judgment-jar-review-import",
                        metadata={
                            "sourceSchema": record.get("schema"),
                            "sourceLine": index + 1,
                            "sourceSha256": source_hash,
                            "verdict": record.get("verdict"),
                            "directive": record.get("directive"),
                            "findings": record.get("findings") or [],
                        },
                    )
                    receipt["receiptId"] = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source}:{index + 1}:{source_hash}:{jar.get('id')}:review_verdict"))
                    receipt["dedupFingerprint"] = fingerprint(receipt)
                    result = capture(receipt, config)
                    if result.get("duplicate"):
                        source_duplicates += 1
                        duplicates += 1
                    else:
                        source_imported += 1
                        imported += 1
            except Exception as exc:
                source_quarantined += 1
                quarantined += 1
                _quarantine(quarantine_path, {
                    "schema": "home-center.judgment-jar-review-import-quarantine.v1",
                    "source": str(source),
                    "line": index + 1,
                    "raw": raw,
                    "error": f"{type(exc).__name__}: {exc}",
                })
            cursors[str(source)] = index + 1
        source_results.append({
            "source": str(source),
            "state": "IMPORTED" if source_imported else "NO_CHANGE",
            "imported": source_imported,
            "duplicates": source_duplicates,
            "quarantined": source_quarantined,
            "line": cursors.get(str(source), start),
        })

    write_atomic(cursor_path, {
        "schema": "home-center.judgment-jar-review-import-cursors.v1",
        "lines": cursors,
        "quarantine": str(quarantine_path),
    })
    return {
        "ok": quarantined == 0,
        "state": "IMPORTED" if imported else "NO_CHANGE",
        "imported": imported,
        "duplicates": duplicates,
        "quarantined": quarantined,
        "cursor": str(cursor_path),
        "quarantine": str(quarantine_path),
        "sources": source_results,
    }
