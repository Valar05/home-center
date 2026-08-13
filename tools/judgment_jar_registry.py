#!/usr/bin/env python3
"""Compile and hydrate Vlad's two-authority Judgment Jar cache."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

from judgment_jar_common import (
    CABINET_ORIGIN, CONFIG_PATH, DEFAULT_CACHE, DISCOVERY_ORIGIN, LOCAL_ORIGIN, SCHEMA,
    RegistryError, aliases_for, digest, normalize_key, parse_local_jar, read_config,
    read_registry, sha256_text, source_commit, source_files, source_stat_digest, write_atomic,
)
from judgment_jar_cabinet import parse_cabinet_registry, parse_discovered_files


def native_source_cache_path(cache: Path, jar: dict[str, Any]) -> Path:
    return cache.expanduser().parent / "judgment-jar-sources" / f"{jar['id']}.json"


def read_native_source_cache(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) and value.get("schema") == "home-center.judgment-jar-source.v1" else None


def fetch_native_source(jar: dict[str, Any], config: dict[str, Any], cache: Path,
                        refresh: bool = False, offline: bool = False,
                        fetcher: Callable[[dict[str, Any], dict[str, Any]], Any] | None = None) -> dict[str, Any]:
    if jar.get("origin") == LOCAL_ORIGIN:
        body = str(jar.get("body") or "")
        return {
            "schema": "home-center.judgment-jar-source.v1", "ok": True, "state": "repository",
            "jarId": jar["id"], "title": jar.get("title"), "sourceType": "repository",
            "sourcePath": jar.get("sourcePath"), "sourceSha256": sha256_text(body),
            "fetchedAtEpoch": int(time.time()), "content": body,
        }

    file_id = str(jar.get("sourceFileId") or "").strip()
    source_type = str(jar.get("sourceType") or "").strip()
    if not file_id or source_type not in {"document", "spreadsheet"}:
        raise RegistryError(f"Judgment Jar {jar.get('id')} has no readable native Home Center source")

    path = native_source_cache_path(cache, jar)
    previous = read_native_source_cache(path)
    ttl = int((config.get("homeCenter") or {}).get("nativeSourceRefreshSeconds") or 3600)
    due = refresh or not previous or int(time.time()) - int(previous.get("fetchedAtEpoch") or 0) >= ttl
    if offline or not due:
        if previous:
            return {**previous, "state": "stale" if offline else "cached", "ok": True}
        if offline:
            raise RegistryError(f"native source for {jar['id']} is not cached for offline use")

    def default_fetch(current: dict[str, Any], current_config: dict[str, Any]) -> Any:
        try:
            from home_center_mcp_client import HomeCenterMcp
        except ImportError as exc:
            raise RegistryError(f"Home Center MCP client is missing: {exc}") from exc
        client = HomeCenterMcp()
        if current["sourceType"] == "document":
            return client.read_document(current["sourceFileId"], str(current.get("title") or ""))
        cell_range = str((current_config.get("homeCenter") or {}).get("spreadsheetDefaultRange") or "A1:ZZ1000")
        return client.read_sheet(current["sourceFileId"], cell_range)

    try:
        raw = (fetcher or default_fetch)(jar, config)
        if source_type == "document":
            content = str(raw or "")
            payload = {"content": content}
        elif isinstance(raw, dict):
            payload = {"sheet": raw}
            content = json.dumps(raw, ensure_ascii=False, sort_keys=True)
        else:
            raise RegistryError(f"native spreadsheet source for {jar['id']} returned an unsupported payload")
        if not content.strip():
            raise RegistryError(f"native source for {jar['id']} was empty")
        snapshot = {
            "schema": "home-center.judgment-jar-source.v1", "ok": True, "state": "synced",
            "jarId": jar["id"], "title": jar.get("title"), "sourceType": source_type,
            "sourceFileId": file_id, "sourceUrl": jar.get("sourceUrl"),
            "sourceSha256": sha256_text(content), "fetchedAtEpoch": int(time.time()),
            **payload,
        }
        write_atomic(path, snapshot)
        return snapshot
    except Exception as exc:
        if previous:
            return {**previous, "state": "stale", "ok": True,
                    "lastError": f"{type(exc).__name__}: {exc}"}
        if isinstance(exc, RegistryError):
            raise
        raise RegistryError(f"native source fetch failed for {jar['id']}: {exc}") from exc


def home_center_fetcher(config: dict[str, Any]) -> dict[str, Any]:
    try:
        from home_center_mcp_client import HomeCenterError, HomeCenterMcp
    except ImportError as exc:
        raise RegistryError(f"Home Center MCP client is missing: {exc}") from exc
    home = config["homeCenter"]
    try:
        client = HomeCenterMcp()
        registry_text = client.read_document(str(home["registryFileId"]), str(home.get("registryTitle") or ""))
        discovered: list[dict[str, Any]] = []
        for query in home.get("discoveryQueries") or []:
            discovered.extend(client.search_drive(str(query), int(home.get("discoveryPageSize") or 10)))
        return {"registryText": registry_text, "discoveredFiles": discovered}
    except HomeCenterError as exc:
        raise RegistryError(str(exc)) from exc


def home_snapshot(config: dict[str, Any], previous: dict[str, Any] | None, force: bool,
                  offline: bool, fetcher: Callable[[dict[str, Any]], Any] | None) -> tuple[dict[str, Any], dict[str, Any]]:
    home_config = config["homeCenter"]
    now = int(time.time())
    previous_home = previous.get("homeCenter") if previous else None
    due = force or not previous_home or now - int((previous_home or {}).get("lastSuccessEpoch") or 0) >= int(home_config.get("refreshSeconds") or 300)
    if offline or not due:
        if previous_home:
            return previous_home, {"attempted": False, "changed": False}
        state = "offline" if offline else "unavailable"
        return {
            "state": state, "complete": False, "registryFileId": home_config["registryFileId"],
            "registryTitle": home_config.get("registryTitle", ""), "cabinetEntries": [], "cabinetCount": 0,
            "discoveredUnregistered": [], "discoveredUnregisteredCount": 0,
            "missingExecutableFunctions": [], "lastError": "offline sync" if offline else "not yet synchronized",
        }, {"attempted": False, "changed": False}
    try:
        fetched = (fetcher or home_center_fetcher)(config)
        if isinstance(fetched, str):
            text, discovered_files = fetched, []
        elif isinstance(fetched, dict):
            text = str(fetched.get("registryText") or "")
            discovered_files = [item for item in (fetched.get("discoveredFiles") or []) if isinstance(item, dict)]
        else:
            raise RegistryError("Home Center fetcher returned an unsupported payload")
        parsed = parse_cabinet_registry(text, str(home_config["registryFileId"]), str(home_config.get("registryTitle") or ""))
        registered = {entry.get("sourceFileId", "") for entry in parsed["cabinetEntries"]}
        discovered = parse_discovered_files(discovered_files, registered, str(home_config["registryFileId"]))
        parsed.update({"discoveredUnregistered": discovered, "discoveredUnregisteredCount": len(discovered)})
        minimum = int(home_config.get("minimumCabinetEntries") or 1)
        if parsed["cabinetCount"] < minimum:
            raise RegistryError(f"Home Center cabinet coverage regressed: {parsed['cabinetCount']} < {minimum}")
        current = {"state": "synced", "complete": True, "lastSuccessEpoch": now,
                   "lastAttemptEpoch": now, "lastError": "", **parsed}
        return current, {"attempted": True, "changed": (previous_home or {}).get("registryTextSha256") != current["registryTextSha256"]}
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        if previous_home and previous_home.get("cabinetEntries"):
            return {**previous_home, "state": "stale", "complete": False,
                    "lastAttemptEpoch": now, "lastError": error}, {"attempted": True, "changed": False, "failed": True}
        return {
            "state": "unavailable", "complete": False, "registryFileId": home_config["registryFileId"],
            "registryTitle": home_config.get("registryTitle", ""), "cabinetEntries": [], "cabinetCount": 0,
            "discoveredUnregistered": [], "discoveredUnregisteredCount": 0,
            "missingExecutableFunctions": [], "lastAttemptEpoch": now, "lastError": error,
        }, {"attempted": True, "changed": False, "failed": True}


def alias_index(jars: list[dict[str, Any]]) -> dict[str, str]:
    index: dict[str, str] = {}
    ambiguous: set[str] = set()
    for jar in jars:
        for alias in jar.get("aliases", []):
            if alias in ambiguous:
                continue
            existing = index.get(alias)
            if existing and existing != jar["id"]:
                index.pop(alias, None)
                ambiguous.add(alias)
            else:
                index[alias] = jar["id"]
    return index


def compile_registry(root: Path, config: dict[str, Any], previous: dict[str, Any] | None = None,
                     force_home_center: bool = False, offline: bool = False,
                     fetcher: Callable[[dict[str, Any]], Any] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    root = root.resolve()
    files = source_files(root, config)
    local = [parse_local_jar(root, path) for path in files]
    home, home_sync = home_snapshot(config, previous, force_home_center, offline, fetcher)
    cabinet = list(home.get("cabinetEntries") or [])
    discovered = list(home.get("discoveredUnregistered") or [])
    jars = local + cabinet + discovered
    seen: set[str] = set()
    for jar in jars:
        if jar["id"] in seen:
            raise RegistryError(f"duplicate Judgment Jar id across authorities: {jar['id']}")
        seen.add(jar["id"])
    paths = [path.relative_to(root).as_posix() for path in files]
    basis = {
        "schema": SCHEMA,
        "local": [{**{k: v for k, v in jar.items() if k != "body"}, "bodySha256": sha256_text(jar["body"])} for jar in local],
        "homeCenterRegistrySha256": home.get("registryTextSha256", ""),
        "cabinet": [{**{k: v for k, v in jar.items() if k != "body"}, "bodySha256": sha256_text(jar["body"])} for jar in cabinet],
        "discovered": [{**{k: v for k, v in jar.items() if k != "body"}, "bodySha256": sha256_text(jar["body"])} for jar in discovered],
    }
    return {
        "schema": SCHEMA, "generatedAtEpoch": int(time.time()), "sourceCommit": source_commit(root),
        "repositorySourcePattern": config["repositorySourcePattern"], "repositorySourcePaths": paths,
        "repositorySourceStatDigest": source_stat_digest(root, files), "localJarCount": len(local),
        "cabinetJarCount": len(cabinet), "unregisteredJarCount": len(discovered), "jarCount": len(jars),
        "complete": bool(home.get("complete")),
        "activeJarIds": [jar["id"] for jar in jars if jar.get("status") == "active"],
        "jars": jars, "aliasIndex": alias_index(jars), "homeCenter": home, "registryDigest": digest(basis),
    }, home_sync


def ensure_registry(root: Path, cache: Path = DEFAULT_CACHE, force: bool = False,
                    force_home_center: bool = False, offline: bool = False,
                    config_path: Path = CONFIG_PATH,
                    fetcher: Callable[[dict[str, Any]], Any] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    root, cache = root.resolve(), cache.expanduser()
    config, previous = read_config(config_path), read_registry(cache)
    files = source_files(root, config)
    expected_paths = [path.relative_to(root).as_posix() for path in files]
    local_unchanged = bool(previous and previous.get("repositorySourceStatDigest") == source_stat_digest(root, files)
                           and previous.get("repositorySourcePaths") == expected_paths)
    registry, home_sync = compile_registry(root, config, previous, force_home_center, offline, fetcher)
    semantic_changed = not previous or previous.get("registryDigest") != registry.get("registryDigest")
    status_changed = bool(previous and (
        previous.get("complete") != registry.get("complete")
        or (previous.get("homeCenter") or {}).get("state") != (registry.get("homeCenter") or {}).get("state")
        or (previous.get("homeCenter") or {}).get("lastError") != (registry.get("homeCenter") or {}).get("lastError")
    ))
    rewrite = bool(force or not previous or semantic_changed or status_changed or not local_unchanged
                   or previous.get("sourceCommit") != registry.get("sourceCommit") or home_sync.get("attempted"))
    if rewrite:
        write_atomic(cache, registry)
    else:
        registry = previous
    return registry, {
        "changed": semantic_changed, "cacheRewritten": rewrite,
        "homeCenterAttempted": bool(home_sync.get("attempted")),
        "homeCenterChanged": bool(home_sync.get("changed")),
        "homeCenterFailed": bool(home_sync.get("failed")),
    }


def resolve_jar(registry: dict[str, Any], key: str) -> dict[str, Any] | None:
    identifier = registry.get("aliasIndex", {}).get(normalize_key(key), normalize_key(key))
    return next((jar for jar in registry.get("jars", []) if jar.get("id") == identifier), None)


PUBLIC_KEYS = [
    "id", "order", "title", "status", "scope", "judgment", "origin", "sourceAuthority",
    "sourceCompleteness", "sourcePath", "sourceSha256", "sourceFileId", "sourceType", "sourceUrl",
    "registrySection", "governor", "home", "boundary", "mixedVerdict", "hardGates",
    "forbiddenFlattening", "compactLaw", "runOrder", "primaryVerdict", "consultationRule",
    "wound", "lineage", "capabilityState", "aliases",
]


def public_jar(jar: dict[str, Any], include_body: bool = False) -> dict[str, Any]:
    value = {key: jar.get(key) for key in PUBLIC_KEYS if jar.get(key) not in (None, "")}
    if include_body:
        value["body"] = jar.get("body", "")
    return value


def search_jars(registry: dict[str, Any], query: str) -> list[dict[str, Any]]:
    normalized = normalize_key(query)
    tokens = [token for token in normalized.split("-") if token]
    ranked = []
    for jar in registry.get("jars", []):
        haystack = normalize_key(" ".join(str(value) for value in [
            jar.get("id", ""), jar.get("title", ""), jar.get("scope", ""), jar.get("judgment", ""),
            jar.get("compactLaw", ""), jar.get("hardGates", ""), " ".join(jar.get("aliases", [])), jar.get("body", ""),
        ]))
        score = 100 + len(tokens) if normalized and normalized in haystack else sum(token in haystack for token in tokens)
        if score:
            ranked.append((score, int(jar.get("order", 9999)), jar))
    ranked.sort(key=lambda row: (-row[0], row[1], row[2].get("id", "")))
    return [public_jar(row[2]) for row in ranked]


def summary(registry: dict[str, Any], cache: Path, sync: dict[str, Any] | None = None) -> dict[str, Any]:
    home = registry.get("homeCenter") or {}
    return {
        "ok": True, "complete": bool(registry.get("complete")), "schema": registry.get("schema"),
        "cachePath": str(cache.expanduser()), "jarCount": registry.get("jarCount", 0),
        "localJarCount": registry.get("localJarCount", 0), "cabinetJarCount": registry.get("cabinetJarCount", 0),
        "unregisteredJarCount": registry.get("unregisteredJarCount", 0), "activeJarIds": registry.get("activeJarIds", []),
        "registryDigest": registry.get("registryDigest"), "sourceCommit": registry.get("sourceCommit"),
        "repositorySourcePattern": registry.get("repositorySourcePattern"),
        "homeCenterState": home.get("state", "unavailable"), "homeCenterRegistryFileId": home.get("registryFileId"),
        "homeCenterRegistrySha256": home.get("registryTextSha256"),
        "homeCenterLastSuccessEpoch": home.get("lastSuccessEpoch"), "homeCenterLastError": home.get("lastError", ""),
        "missingExecutableFunctions": home.get("missingExecutableFunctions", []), **(sync or {}),
    }


def prompt_text(registry: dict[str, Any], keys: list[str], include_all: bool = False) -> str:
    selected: list[dict[str, Any]] = []
    if keys:
        missing = []
        for key in keys:
            jar = resolve_jar(registry, key)
            if jar is None:
                missing.append(key)
            elif jar["id"] not in {item["id"] for item in selected}:
                selected.append(jar)
        if missing:
            raise RegistryError("unknown Judgment Jar(s): " + ", ".join(missing))
    elif include_all:
        selected = list(registry.get("jars", []))
    else:
        selected = [jar for jar in registry.get("jars", []) if jar.get("origin") == LOCAL_ORIGIN and jar.get("status") == "active"]
    chunks = [
        f"JUDGMENT JAR REGISTRY: {registry.get('registryDigest')}",
        f"SOURCE COMMIT: {registry.get('sourceCommit')}",
        f"HOME CENTER: {(registry.get('homeCenter') or {}).get('state', 'unavailable')}",
        f"SELECTED: {', '.join(jar['id'] for jar in selected)}",
        *(jar.get("body", "").rstrip() for jar in selected),
    ]
    return "\n\n".join(chunks).rstrip() + "\n"

