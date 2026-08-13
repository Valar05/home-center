#!/usr/bin/env python3
"""Vlad fast access to repository and Home Center Judgment Jars."""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from judgment_jar_atom_import import import_atom_receipts
from judgment_jar_common import CONFIG_PATH, DEFAULT_CACHE, LOCAL_ORIGIN, ROOT, RegistryError, read_config
from judgment_jar_receipt_truth import ReceiptError, flush as flush_receipts, record as record_receipt, status as receipt_status
from judgment_jar_registry import ensure_registry, fetch_native_source, prompt_text, public_jar, resolve_jar, search_jars, summary
from judgment_jar_review_import import import_review_receipts


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="vlad-jars", description="Vlad fast access to repository and Home Center Judgment Jars")
    root.add_argument("--root", default=str(ROOT)); root.add_argument("--cache", default=str(DEFAULT_CACHE))
    root.add_argument("--config", default=str(CONFIG_PATH)); root.add_argument("--offline", action="store_true")
    commands = root.add_subparsers(dest="command", required=True)
    sync = commands.add_parser("sync"); sync.add_argument("--force", action="store_true"); sync.add_argument("--force-home-center", action="store_true")
    commands.add_parser("status"); commands.add_parser("list")
    get = commands.add_parser("get"); get.add_argument("key")
    source = commands.add_parser("source"); source.add_argument("key"); source.add_argument("--refresh", action="store_true")
    search = commands.add_parser("search"); search.add_argument("query", nargs="+")
    prompt = commands.add_parser("prompt"); prompt.add_argument("--all", action="store_true", dest="include_all"); prompt.add_argument("keys", nargs="*")
    commands.add_parser("registry"); commands.add_parser("receipt-status")
    flushing = commands.add_parser("flush-receipts"); flushing.add_argument("--limit", type=int)
    return root


def selected_prompt_jars(registry: dict, keys: list[str], include_all: bool) -> list[dict]:
    if include_all:
        return list(registry.get("jars") or [])
    if not keys:
        return [jar for jar in registry.get("jars") or [] if jar.get("origin") == LOCAL_ORIGIN and jar.get("status") == "active"]
    selected, missing = [], []
    for key in keys:
        jar = resolve_jar(registry, key)
        if jar is None:
            missing.append(key)
        elif jar.get("id") not in {item.get("id") for item in selected}:
            selected.append(jar)
    if missing:
        raise RegistryError("unknown Judgment Jar(s): " + ", ".join(missing))
    return selected


def refs(jar: dict) -> list[str]:
    return [str(value) for value in (jar.get("sourcePath"), jar.get("sourceUrl"), jar.get("sourceFileId")) if value]


def context_receipt(registry: dict, jar: dict, config: dict, output: str, source: str, intent: str, action: str, input_text: str, request_id: str = "", group_id: str = "") -> dict:
    try:
        return record_receipt(
            registry, jar, config,
            output_kind="context_packet", output_text=output,
            summary=f"Loaded Judgment Jar context: {jar.get('title') or jar.get('id')}",
            actor="Vlad", intent=intent, surface="jar", decision_action=action,
            input_text=input_text, request_id=request_id, group_id=group_id,
            references=refs(jar), source=source,
        )
    except (ReceiptError, OSError, ValueError) as exc:
        return {"ok": False, "state": "RECEIPT_CAPTURE_FAILED", "error": f"{type(exc).__name__}: {exc}"}


def _quarantine_count(path_value: object) -> int:
    path = Path(str(path_value or "")).expanduser()
    if not path.is_file():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip())


def import_usage(registry: dict, config: dict) -> dict:
    values = {
        "atom": import_atom_receipts(config),
        "veniceReviews": import_review_receipts(registry, config),
    }
    for value in values.values():
        count = _quarantine_count(value.get("quarantine"))
        value["quarantineCount"] = count
        if count:
            value["ok"] = False
            value["state"] = "QUARANTINED"
    return values


def apply_import_truth(usage: dict, imports: dict) -> dict:
    failures = {name: value for name, value in imports.items() if value.get("ok") is not True}
    value = {**usage, "imports": imports}
    if failures:
        value.update({
            "ok": False,
            "state": "IMPORT_QUARANTINED",
            "blocked": {
                "state": "IMPORT_QUARANTINED",
                "imports": failures,
                "error": "One or more Judgment Jar usage sources require explicit quarantine repair.",
            },
        })
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    cache, config_path = Path(args.cache).expanduser(), Path(args.config).expanduser()
    try:
        config = read_config(config_path)
        if args.command == "receipt-status":
            result = receipt_status(config)
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)); return 0 if result.get("ok") is True else 1
        if args.command == "flush-receipts":
            registry, _ = ensure_registry(Path(args.root), cache, offline=True, config_path=config_path)
            imports = import_usage(registry, config)
            result = apply_import_truth(flush_receipts(config, limit=args.limit), imports)
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)); return 0 if result.get("ok") is True else 1
        registry, sync_state = ensure_registry(
            Path(args.root), cache,
            force=bool(getattr(args, "force", False)),
            force_home_center=bool(getattr(args, "force_home_center", False)),
            offline=bool(args.offline), config_path=config_path,
        )
        if args.command == "sync":
            imports = import_usage(registry, config)
            usage = receipt_status(config) if args.offline else flush_receipts(config)
            usage = apply_import_truth(usage, imports)
            print(json.dumps({**summary(registry, cache, sync_state), "judgmentJarUsageReceipts": usage}, ensure_ascii=False, sort_keys=True)); return 0 if usage.get("ok") is True else 1
        if args.command == "status":
            print(json.dumps({**summary(registry, cache, sync_state), "judgmentJarUsageReceipts": receipt_status(config)}, ensure_ascii=False, sort_keys=True)); return 0
        if args.command == "list":
            print(json.dumps({**summary(registry, cache), "jars": [public_jar(jar) for jar in registry.get("jars", [])]}, ensure_ascii=False, indent=2, sort_keys=True)); return 0
        if args.command == "get":
            jar = resolve_jar(registry, args.key)
            if jar is None: raise RegistryError(f"unknown Judgment Jar: {args.key}")
            packet = {**summary(registry, cache), "jar": public_jar(jar, True)}
            raw = json.dumps(packet, ensure_ascii=False, sort_keys=True)
            packet["usage"] = context_receipt(registry, jar, config, raw, "vlad-jars.get", "retrieve bounded Judgment Jar context", "returned cached Jar body and provenance", args.key)
            print(json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True)); return 0 if packet["usage"].get("ok") is True else 1
        if args.command == "source":
            jar = resolve_jar(registry, args.key)
            if jar is None: raise RegistryError(f"unknown Judgment Jar: {args.key}")
            native = fetch_native_source(jar, config, cache, refresh=bool(args.refresh), offline=bool(args.offline))
            packet = {**summary(registry, cache), "jar": public_jar(jar), "source": native}
            raw = json.dumps(packet, ensure_ascii=False, sort_keys=True)
            packet["usage"] = context_receipt(registry, jar, config, raw, "vlad-jars.source", "retrieve authoritative native Judgment Jar source", "returned native source or explicit stale cache", args.key)
            print(json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True)); return 0 if packet["usage"].get("ok") is True else 1
        if args.command == "search":
            query = " ".join(args.query)
            print(json.dumps({**summary(registry, cache), "query": query, "matches": search_jars(registry, query)}, ensure_ascii=False, indent=2, sort_keys=True)); return 0
        if args.command == "prompt":
            text = prompt_text(registry, args.keys, args.include_all)
            group_id, request_id = str(uuid.uuid4()), str(uuid.uuid4())
            usage = [context_receipt(registry, jar, config, text, "vlad-jars.prompt", "assemble bounded Judgment Jar prompt context", "included Jar in compiled context packet", " ".join(args.keys), request_id, group_id) for jar in selected_prompt_jars(registry, args.keys, args.include_all)]
            print(json.dumps({"judgmentJarUsage": usage}, ensure_ascii=False, sort_keys=True), file=sys.stderr)
            if not all(result.get("ok") is True for result in usage):
                raise ReceiptError("one or more Judgment Jar context receipts failed capture")
            sys.stdout.write(text); return 0
        if args.command == "registry":
            text = (registry.get("homeCenter") or {}).get("registryText") or ""
            if not text: raise RegistryError("Home Center cabinet registry is not cached")
            sys.stdout.write(text.rstrip() + "\n"); return 0
        raise RegistryError(f"unsupported command: {args.command}")
    except (RegistryError, ReceiptError, OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc), "cachePath": str(cache)}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
