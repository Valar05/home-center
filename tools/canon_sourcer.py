#!/usr/bin/env python3
"""Deterministic, phone-local canon cache and bounded scene packet compiler."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = Path(os.environ.get("HC_CANON_CONFIG", ROOT / "config/canon-sources.v1.json")).expanduser()
DEFAULT_CACHE = Path(os.environ.get("HC_CANON_CACHE", "~/.local/state/home-center/canon")).expanduser()
SCHEMA = "home-center.canon-sources.config.v1"


class CanonError(RuntimeError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, path)


def load_config(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CanonError(f"invalid canon config {path}: {exc}") from exc
    if value.get("schema") != SCHEMA:
        raise CanonError(f"unsupported canon config schema: {value.get('schema')}")
    seen: set[str] = set()
    for source in value.get("sources") or []:
        identifier = str(source.get("id") or "").strip()
        if not identifier or identifier in seen:
            raise CanonError(f"missing or duplicate canon source id: {identifier}")
        seen.add(identifier)
        classification = source.get("classification")
        policy = source.get("syncPolicy")
        if classification not in {"canon", "noncanon"}:
            raise CanonError(f"{identifier}: classification must be canon or noncanon")
        if classification == "canon" and policy != "always":
            raise CanonError(f"{identifier}: every canon source must use syncPolicy=always")
        if classification == "noncanon" and policy != "on_demand":
            raise CanonError(f"{identifier}: noncanon sources must use syncPolicy=on_demand")
        if source.get("sourceType") not in {"document", "spreadsheet", "drive_text"}:
            raise CanonError(f"{identifier}: unsupported sourceType")
        if not source.get("sourceFileId") and source.get("resolveExactTitle") is not True:
            raise CanonError(f"{identifier}: sourceFileId or resolveExactTitle=true is required")
    return value


def exact_file_id(client: Any, source: dict[str, Any]) -> str:
    current = str(source.get("sourceFileId") or "").strip()
    if current:
        return current
    title = str(source.get("title") or "").strip()
    matches = [item for item in client.search_drive(title, 10) if str(item.get("name") or "") == title]
    ids = sorted({str(item.get("id") or "").strip() for item in matches if item.get("id")})
    if len(ids) != 1:
        raise CanonError(f"{source['id']}: exact title resolved {len(ids)} files; expected one")
    return ids[0]


def default_fetch(source: dict[str, Any]) -> dict[str, Any]:
    try:
        from home_center_mcp_client import HomeCenterMcp
    except ImportError as exc:
        raise CanonError(f"Home Center MCP client missing: {exc}") from exc
    client = HomeCenterMcp()
    file_id = exact_file_id(client, source)
    source_type = source["sourceType"]
    if source_type == "document":
        content: Any = client.read_document(file_id, str(source.get("title") or ""))
    elif source_type == "spreadsheet":
        content = client.read_sheet(file_id, str(source.get("range") or "A1:ZZ1000"))
    else:
        value = client.call_tool("drive_read", {"fileId": file_id})
        content = value.get("content") if isinstance(value, dict) else None
        if not content:
            raise CanonError(f"{source['id']}: drive_read returned no text")
    return {"fileId": file_id, "content": content}


def snapshot_path(cache: Path, source_id: str) -> Path:
    return cache / "sources" / f"{source_id}.json"


def read_snapshot(cache: Path, source_id: str) -> dict[str, Any] | None:
    try:
        value = json.loads(snapshot_path(cache, source_id).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if value.get("schema") == "home-center.canon-source.snapshot.v1" else None


def source_terms(source: dict[str, Any]) -> set[str]:
    values = [source.get("id"), source.get("title"), *(source.get("entities") or []), *(source.get("keywords") or [])]
    return {token for value in values for token in normalize(str(value or "")).split() if len(token) > 1}


def relevant(source: dict[str, Any], query: str) -> bool:
    query_terms = set(normalize(query).split())
    return bool(query_terms & source_terms(source))


def sync(config: dict[str, Any], cache: Path, selected: set[str] | None = None,
         fetcher: Callable[[dict[str, Any]], dict[str, Any]] = default_fetch,
         offline: bool = False) -> dict[str, Any]:
    selected = selected or set()
    results = []
    for source in config.get("sources") or []:
        required = source["classification"] == "canon" or source["id"] in selected
        previous = read_snapshot(cache, source["id"])
        if not required:
            results.append({"id": source["id"], "state": "not_requested", "classification": source["classification"]})
            continue
        if offline:
            if not previous:
                raise CanonError(f"{source['id']}: required source is not cached")
            results.append({"id": source["id"], "state": "cached", "sha256": previous["sha256"]})
            continue
        try:
            fetched = fetcher(source)
            content = fetched["content"]
            text = content if isinstance(content, str) else canonical_json(content)
            if not text.strip():
                raise CanonError("empty content")
            snapshot = {
                "schema": "home-center.canon-source.snapshot.v1",
                "id": source["id"], "title": source.get("title", ""),
                "classification": source["classification"], "sourceType": source["sourceType"],
                "sourceFileId": fetched["fileId"], "fetchedAtEpoch": int(time.time()),
                "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "content": content,
            }
            atomic_json(snapshot_path(cache, source["id"]), snapshot)
            results.append({"id": source["id"], "state": "synced", "sha256": snapshot["sha256"]})
        except Exception as exc:
            if previous:
                results.append({"id": source["id"], "state": "stale", "sha256": previous["sha256"], "error": f"{type(exc).__name__}: {exc}"})
            else:
                raise CanonError(f"{source['id']}: required sync failed: {exc}") from exc
    index = {
        "schema": "home-center.canon-cache.index.v1", "generatedAtEpoch": int(time.time()),
        "configDigest": digest(config), "results": results,
        "canonComplete": all(item["state"] in {"synced", "cached", "stale"} for item in results if next(s for s in config["sources"] if s["id"] == item["id"])["classification"] == "canon"),
    }
    atomic_json(cache / "index.json", index)
    return index


def bounded_text(content: Any, query: str, limit: int) -> str:
    text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False, sort_keys=True)
    terms = [term for term in normalize(query).split() if len(term) > 2]
    blocks = re.split(r"(?m)(?=^#{1,4}\s+)", text)
    picked = [block.strip() for block in blocks if any(term in normalize(block) for term in terms)]
    value = "\n\n".join(picked) if picked else text
    return value[:limit].rstrip()


def packet(config: dict[str, Any], cache: Path, query: str) -> dict[str, Any]:
    candidates = [source for source in config.get("sources") or [] if relevant(source, query)]
    if not candidates:
        raise CanonError("no deterministic canon source matched the scene")
    maximum = int(config.get("maximumPacketCharacters") or 18000)
    per_source = max(1000, maximum // len(candidates))
    sources, chunks = [], []
    for source in candidates:
        snap = read_snapshot(cache, source["id"])
        if not snap:
            raise CanonError(f"{source['id']}: relevant source is not cached")
        excerpt = bounded_text(snap["content"], query, per_source)
        sources.append({"id": source["id"], "classification": source["classification"], "sourceFileId": snap["sourceFileId"], "sha256": snap["sha256"]})
        chunks.append(f"## {source['title']}\n{excerpt}")
    body = "\n\n".join(chunks)[:maximum].rstrip() + "\n"
    return {"schema": "home-center.canon-packet.v1", "query": query, "sources": sources, "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(), "text": body}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="adam-canon")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG)); parser.add_argument("--cache", default=str(DEFAULT_CACHE))
    parser.add_argument("--offline", action="store_true")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("sync")
    pack = commands.add_parser("packet"); pack.add_argument("query", nargs="+")
    commands.add_parser("status")
    args = parser.parse_args(argv)
    try:
        config, cache = load_config(Path(args.config).expanduser()), Path(args.cache).expanduser()
        if args.command == "sync":
            print(json.dumps(sync(config, cache, offline=args.offline), ensure_ascii=False, indent=2, sort_keys=True)); return 0
        if args.command == "packet":
            query = " ".join(args.query)
            selected = {source["id"] for source in config["sources"] if source["classification"] == "noncanon" and relevant(source, query)}
            sync(config, cache, selected, offline=args.offline)
            print(json.dumps(packet(config, cache, query), ensure_ascii=False, indent=2, sort_keys=True)); return 0
        index = json.loads((cache / "index.json").read_text(encoding="utf-8"))
        print(json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True)); return 0
    except (CanonError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True), file=__import__("sys").stderr); return 2


if __name__ == "__main__":
    raise SystemExit(main())
