#!/usr/bin/env python3
"""Vlad fast access to repository and Home Center Judgment Jars.

Catalog discovery/search is read-only. Commands that actually load Jar context
(`get`, `source`, and `prompt`) emit one append-only usage receipt per Jar and
name the output they created. `receipt` records a later Jar-governed output.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from judgment_jar_common import (  # noqa: E402
    CABINET_ORIGIN, CONFIG_PATH, DEFAULT_CACHE, DISCOVERY_ORIGIN, LOCAL_ORIGIN, ROOT,
    RegistryError, read_config, read_registry,
)
from judgment_jar_receipts import (  # noqa: E402
    output_kinds, record_many, record_usage, status as usage_status, sync_pending,
)
from judgment_jar_registry import (  # noqa: E402
    ensure_registry, fetch_native_source, prompt_text, public_jar, resolve_jar, search_jars, summary,
)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="vlad-jars", description="Vlad fast access to repository and Home Center Judgment Jars")
    root.add_argument("--root", default=str(ROOT)); root.add_argument("--cache", default=str(DEFAULT_CACHE))
    root.add_argument("--config", default=str(CONFIG_PATH)); root.add_argument("--offline", action="store_true")
    commands = root.add_subparsers(dest="command", required=True)
    sync = commands.add_parser("sync"); sync.add_argument("--force", action="store_true"); sync.add_argument("--force-home-center", action="store_true")
    commands.add_parser("status"); commands.add_parser("list"); commands.add_parser("usage-status"); commands.add_parser("flush-receipts")
    get = commands.add_parser("get"); get.add_argument("key")
    source = commands.add_parser("source"); source.add_argument("key"); source.add_argument("--refresh", action="store_true")
    search = commands.add_parser("search"); search.add_argument("query", nargs="+")
    prompt = commands.add_parser("prompt"); prompt.add_argument("--all", action="store_true", dest="include_all"); prompt.add_argument("keys", nargs="*")
    usage = commands.add_parser("receipt")
    usage.add_argument("keys", nargs="+")
    usage.add_argument("--output-kind", required=True)
    usage.add_argument("--summary", required=True)
    usage.add_argument("--source", default="vlad.jar.receipt")
    usage.add_argument("--status", default="created")
    usage.add_argument("--request-id")
    usage.add_argument("--input", default="")
    usage.add_argument("--output", default="")
    usage.add_argument("--ref", action="append", default=[])
    commands.add_parser("registry")
    return root


def selected_for_prompt(registry: dict, keys: list[str], include_all: bool) -> list[dict]:
    if keys:
        selected, missing, seen = [], [], set()
        for key in keys:
            jar = resolve_jar(registry, key)
            if jar is None:
                missing.append(key)
            elif jar["id"] not in seen:
                selected.append(jar); seen.add(jar["id"])
        if missing:
            raise RegistryError("unknown Judgment Jar(s): " + ", ".join(missing))
        return selected
    if include_all:
        return list(registry.get("jars", []))
    return [jar for jar in registry.get("jars", []) if jar.get("origin") == LOCAL_ORIGIN and jar.get("status") == "active"]


def usage_summary(results: list[dict]) -> dict:
    return {
        "schema": "home-center.judgment-jar-usage-batch.v1",
        "receiptIds": [item["receipt"]["receiptId"] for item in results],
        "jarIds": [item["receipt"]["jar"]["id"] for item in results],
        "outputKind": results[0]["receipt"]["output"]["kind"] if results else None,
        "homeCenterStates": [item["homeCenter"]["state"] for item in results],
    }


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    cache, config_path = Path(args.cache).expanduser(), Path(args.config).expanduser()
    try:
        config = read_config(config_path)
        previous = read_registry(cache)
        preflush = sync_pending(previous, config, cache) if previous else {"ok": True, "state": "NO_CACHE", "delivered": [], "remaining": 0}
        registry, sync = ensure_registry(
            Path(args.root), cache,
            force=bool(getattr(args, "force", False)),
            force_home_center=bool(getattr(args, "force_home_center", False)),
            offline=bool(args.offline), config_path=config_path,
        )
        if args.command == "sync":
            pending = sync_pending(registry, config, cache)
            print(json.dumps({**summary(registry, cache, sync), "usageReceiptsPreSync": preflush, "usageReceipts": pending}, ensure_ascii=False, sort_keys=True)); return 0
        if args.command == "status":
            print(json.dumps({**summary(registry, cache, sync), "usageReceiptsPreSync": preflush, "usageReceipts": usage_status(registry, config, cache)}, ensure_ascii=False, sort_keys=True)); return 0
        if args.command == "usage-status":
            print(json.dumps(usage_status(registry, config, cache), ensure_ascii=False, indent=2, sort_keys=True)); return 0
        if args.command == "flush-receipts":
            print(json.dumps(sync_pending(registry, config, cache), ensure_ascii=False, indent=2, sort_keys=True)); return 0
        if args.command == "list":
            print(json.dumps({**summary(registry, cache), "jars": [public_jar(jar) for jar in registry.get("jars", [])]}, ensure_ascii=False, indent=2, sort_keys=True)); return 0
        if args.command == "get":
            jar = resolve_jar(registry, args.key)
            if jar is None: raise RegistryError(f"unknown Judgment Jar: {args.key}")
            packet = {**summary(registry, cache), "jar": public_jar(jar, True)}
            output = json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True)
            receipt = record_usage(
                registry, config, jar,
                output_kind="context_packet",
                output_summary=f"Vlad loaded Judgment Jar context: {jar['title']}",
                source="vlad.jars.get", cache=cache,
                input_text=args.key, output_text=output,
                output_refs=[str(jar.get("sourcePath") or "")],
                metadata={"command": "get"},
            )
            print(json.dumps({**packet, "usage": receipt}, ensure_ascii=False, indent=2, sort_keys=True)); return 0
        if args.command == "source":
            jar = resolve_jar(registry, args.key)
            if jar is None: raise RegistryError(f"unknown Judgment Jar: {args.key}")
            native = fetch_native_source(jar, config, cache, refresh=bool(args.refresh), offline=bool(args.offline))
            packet = {**summary(registry, cache), "jar": public_jar(jar), "source": native}
            output = json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True)
            receipt = record_usage(
                registry, config, jar,
                output_kind="context_packet",
                output_summary=f"Vlad loaded authoritative Judgment Jar source: {jar['title']}",
                source="vlad.jars.source", cache=cache,
                input_text=args.key, output_text=output,
                output_refs=[value for value in (jar.get("sourcePath"), jar.get("sourceUrl")) if value],
                native_source=native,
                metadata={"command": "source", "refresh": bool(args.refresh)},
            )
            print(json.dumps({**packet, "usage": receipt}, ensure_ascii=False, indent=2, sort_keys=True)); return 0
        if args.command == "search":
            query = " ".join(args.query)
            print(json.dumps({**summary(registry, cache), "query": query, "matches": search_jars(registry, query)}, ensure_ascii=False, indent=2, sort_keys=True)); return 0
        if args.command == "prompt":
            selected = selected_for_prompt(registry, args.keys, args.include_all)
            output = prompt_text(registry, args.keys, args.include_all)
            receipts = record_many(
                registry, config, selected,
                output_kind="context_packet",
                output_summary="Vlad compiled a Judgment Jar prompt context packet.",
                source="vlad.jars.prompt", cache=cache,
                input_text=json.dumps({"keys": args.keys, "all": bool(args.include_all)}, sort_keys=True),
                output_text=output,
                output_refs=[str(item.get("sourcePath") or "") for item in selected],
                metadata={"command": "prompt", "selectedJarIds": [item["id"] for item in selected]},
            )
            print(json.dumps(usage_summary(receipts), ensure_ascii=False, sort_keys=True), file=sys.stderr)
            sys.stdout.write(output); return 0
        if args.command == "receipt":
            if args.output_kind not in output_kinds(config):
                raise RegistryError(f"output kind must be one of: {', '.join(sorted(output_kinds(config)))}")
            results = record_many(
                registry, config, args.keys,
                output_kind=args.output_kind,
                output_summary=args.summary,
                source=args.source, cache=cache,
                status=args.status,
                input_text=args.input, output_text=args.output,
                request_id=args.request_id,
                output_refs=args.ref,
                metadata={"command": "receipt", "recordedBy": "Vlad"},
            )
            print(json.dumps({"ok": True, **usage_summary(results), "results": results}, ensure_ascii=False, indent=2, sort_keys=True)); return 0
        if args.command == "registry":
            text = (registry.get("homeCenter") or {}).get("registryText") or ""
            if not text: raise RegistryError("Home Center cabinet registry is not cached")
            sys.stdout.write(text.rstrip() + "\n"); return 0
        raise RegistryError(f"unsupported command: {args.command}")
    except RegistryError as exc:
        print(json.dumps({"ok": False, "error": str(exc), "cachePath": str(cache)}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
