#!/usr/bin/env python3
"""Vlad fast access to repository and Home Center Judgment Jars."""
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
    RegistryError,
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
    commands.add_parser("status"); commands.add_parser("list")
    get = commands.add_parser("get"); get.add_argument("key")
    source = commands.add_parser("source"); source.add_argument("key"); source.add_argument("--refresh", action="store_true")
    search = commands.add_parser("search"); search.add_argument("query", nargs="+")
    prompt = commands.add_parser("prompt"); prompt.add_argument("--all", action="store_true", dest="include_all"); prompt.add_argument("keys", nargs="*")
    commands.add_parser("registry")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    cache, config = Path(args.cache).expanduser(), Path(args.config).expanduser()
    try:
        registry, sync = ensure_registry(Path(args.root), cache,
            force=bool(getattr(args, "force", False)), force_home_center=bool(getattr(args, "force_home_center", False)),
            offline=bool(args.offline), config_path=config)
        if args.command in {"sync", "status"}:
            print(json.dumps(summary(registry, cache, sync), ensure_ascii=False, sort_keys=True)); return 0
        if args.command == "list":
            print(json.dumps({**summary(registry, cache), "jars": [public_jar(jar) for jar in registry.get("jars", [])]}, ensure_ascii=False, indent=2, sort_keys=True)); return 0
        if args.command == "get":
            jar = resolve_jar(registry, args.key)
            if jar is None: raise RegistryError(f"unknown Judgment Jar: {args.key}")
            print(json.dumps({**summary(registry, cache), "jar": public_jar(jar, True)}, ensure_ascii=False, indent=2, sort_keys=True)); return 0
        if args.command == "source":
            jar = resolve_jar(registry, args.key)
            if jar is None: raise RegistryError(f"unknown Judgment Jar: {args.key}")
            source = fetch_native_source(jar, config, cache, refresh=bool(args.refresh), offline=bool(args.offline))
            print(json.dumps({**summary(registry, cache), "jar": public_jar(jar), "source": source}, ensure_ascii=False, indent=2, sort_keys=True)); return 0
        if args.command == "search":
            query = " ".join(args.query)
            print(json.dumps({**summary(registry, cache), "query": query, "matches": search_jars(registry, query)}, ensure_ascii=False, indent=2, sort_keys=True)); return 0
        if args.command == "prompt":
            sys.stdout.write(prompt_text(registry, args.keys, args.include_all)); return 0
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
