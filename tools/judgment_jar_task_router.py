#!/usr/bin/env python3
"""Resolve task-mentioned Judgment Jars through the canonical Drive registry.

This is the deterministic entrance that was missing from the phone worker.  Model
memory and Drive search may suggest names, but they never establish Jar authority.
A task-level Jar route is usable only after the canonical registry and exact native
Jar source have both been freshly read.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from judgment_jar_common import (
    CABINET_ORIGIN,
    CONFIG_PATH,
    DEFAULT_CACHE,
    LOCAL_ORIGIN,
    ROOT,
    RegistryError,
    normalize_key,
    read_config,
)
from judgment_jar_registry import ensure_registry, fetch_native_source


ARCHIVE_MARKERS = ("archive copy", "do not resolve")
JAR_WORDS = {"jar", "jars", "judgment-jar", "judgment-jars", "judgement-jar", "judgement-jars"}
_ALIAS_DIRECTIVE = re.compile(
    r"(?im)^(.+?) aliases for retrieval only:\s*(.+?)\.\s*Canonical Jar ID:\s*([A-Za-z0-9_-]+)\."
)


def _strip_alias(value: str) -> str:
    return str(value or "").strip().strip(" \t.;,:\"'“”‘’")


def _eligible(jar: dict[str, Any]) -> bool:
    if jar.get("origin") not in {LOCAL_ORIGIN, CABINET_ORIGIN}:
        return False
    title = str(jar.get("title") or "").lower()
    return not any(marker in title for marker in ARCHIVE_MARKERS)


def _canonical_by_file_id(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(jar.get("sourceFileId")): jar
        for jar in registry.get("jars") or []
        if _eligible(jar) and str(jar.get("sourceFileId") or "")
    }


def _alias_targets(registry: dict[str, Any]) -> dict[str, set[str]]:
    """Return normalized alias -> eligible Jar ids; ambiguous aliases retain >1 id."""
    targets: dict[str, set[str]] = {}

    def add(raw: str, jar_id: str) -> None:
        key = normalize_key(raw)
        if key:
            targets.setdefault(key, set()).add(jar_id)

    for jar in registry.get("jars") or []:
        if not _eligible(jar):
            continue
        jar_id = str(jar.get("id") or "")
        for alias in jar.get("aliases") or []:
            add(str(alias), jar_id)
        title = str(jar.get("title") or "")
        if title:
            add(title, jar_id)
            # Character/governor shorthand such as "Pasta’Fahr" must resolve even
            # when the workbook title continues with an em-dash subtitle.
            add(re.split(r"\s+[—–-]\s+", title, maxsplit=1)[0], jar_id)

    home = registry.get("homeCenter") or {}
    registry_text = str(home.get("registryText") or "")
    by_file_id = _canonical_by_file_id(registry)
    for match in _ALIAS_DIRECTIVE.finditer(registry_text):
        label, blob, file_id = match.groups()
        jar = by_file_id.get(file_id)
        if jar is None:
            continue
        jar_id = str(jar.get("id") or "")
        add(label, jar_id)
        for raw in blob.split(";"):
            alias = _strip_alias(raw)
            if alias:
                add(alias, jar_id)
    return targets


def resolve_task_jars(registry: dict[str, Any], task: str) -> list[dict[str, Any]]:
    """Resolve only explicit, unique aliases carried by the current utterance."""
    normalized = normalize_key(task)
    if not normalized:
        return []
    padded = f"-{normalized}-"
    targets = _alias_targets(registry)
    matched_ids: list[str] = []
    # Longest aliases win first; ambiguity is excluded rather than guessed.
    for alias, jar_ids in sorted(targets.items(), key=lambda item: (-len(item[0]), item[0])):
        if len(jar_ids) != 1 or len(alias) < 3:
            continue
        if f"-{alias}-" not in padded:
            continue
        jar_id = next(iter(jar_ids))
        if jar_id not in matched_ids:
            matched_ids.append(jar_id)
    by_id = {str(jar.get("id")): jar for jar in registry.get("jars") or [] if _eligible(jar)}
    return [by_id[jar_id] for jar_id in matched_ids if jar_id in by_id]


def has_explicit_jar_signal(task: str) -> bool:
    normalized = normalize_key(task)
    tokens = set(normalized.split("-"))
    return bool(tokens & {"jar", "jars"}) or any(word in normalized for word in JAR_WORDS)


def _source_text(snapshot: dict[str, Any]) -> str:
    if isinstance(snapshot.get("content"), str):
        return str(snapshot["content"])
    if isinstance(snapshot.get("sheet"), dict):
        return json.dumps(snapshot["sheet"], ensure_ascii=False, sort_keys=True)
    return ""


def task_source_packet(
    task: str,
    *,
    root: Path = ROOT,
    cache: Path = DEFAULT_CACHE,
    config_path: Path = CONFIG_PATH,
) -> str:
    """Freshly resolve and fetch every canonical Jar explicitly implicated by task.

    Returns an empty string for a task that names no known Jar and contains no Jar
    routing language.  Any explicit Jar request that cannot complete the canonical
    route fails closed with JAR_UNRESOLVED.
    """
    config = read_config(config_path)
    registry, _ = ensure_registry(
        root,
        cache,
        force_home_center=True,
        offline=False,
        config_path=config_path,
    )
    matched = resolve_task_jars(registry, task)
    explicit_signal = has_explicit_jar_signal(task)
    if not matched and not explicit_signal:
        return ""

    home = registry.get("homeCenter") or {}
    expected_registry_id = str((config.get("homeCenter") or {}).get("registryFileId") or "")
    registry_id = str(home.get("registryFileId") or "")
    if (
        not expected_registry_id
        or registry_id != expected_registry_id
        or home.get("state") != "synced"
        or home.get("complete") is False
    ):
        raise RegistryError(
            "JAR_UNRESOLVED: canonical Judgment Jar registry did not fresh-sync by exact file ID"
        )
    if not matched:
        raise RegistryError("JAR_UNRESOLVED: explicit Judgment Jar request has no unique canonical route")

    chunks = [
        "TASK-RESOLVED JUDGMENT JARS — CANONICAL DRIVE ROUTE",
        f"REGISTRY_FILE_ID: {registry_id}",
        f"REGISTRY_SHA256: {home.get('registryTextSha256') or ''}",
        "LAW: model memory/search ranking are discovery only; these exact native sources control.",
    ]
    for jar in matched:
        source = fetch_native_source(jar, config, cache, refresh=True, offline=False)
        source_state = str(source.get("state") or "")
        if jar.get("origin") == CABINET_ORIGIN and source_state != "synced":
            raise RegistryError(
                f"JAR_UNRESOLVED: canonical native source for {jar.get('title') or jar.get('id')} was not freshly fetched"
            )
        text = _source_text(source)
        if not text.strip():
            raise RegistryError(f"JAR_UNRESOLVED: canonical source for {jar.get('id')} was empty")
        chunks.extend([
            "",
            f"--- CANONICAL JAR: {jar.get('title') or jar.get('id')} ---",
            f"JAR_ID: {jar.get('id')}",
            f"SOURCE_FILE_ID: {jar.get('sourceFileId') or jar.get('sourcePath') or ''}",
            f"SOURCE_STATE: {source_state}",
            f"SOURCE_SHA256: {source.get('sourceSha256') or ''}",
            text.rstrip(),
        ])
    return "\n".join(chunks).rstrip() + "\n"
