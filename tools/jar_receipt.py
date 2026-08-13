#!/usr/bin/env python3
"""Record or flush typed Judgment Jar output receipts."""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from judgment_jar_common import CONFIG_PATH, DEFAULT_CACHE, RegistryError, read_config, read_registry
from judgment_jar_receipt_truth import ReceiptError, flush, record, resolve_jar, status


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="jar-receipt")
    root.add_argument("--config", default=str(CONFIG_PATH))
    root.add_argument("--cache", default=str(DEFAULT_CACHE))
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("status")
    flushing = commands.add_parser("flush")
    flushing.add_argument("--limit", type=int)
    create = commands.add_parser("record")
    create.add_argument("jars", nargs="+")
    create.add_argument("--output-kind", required=True)
    create.add_argument("--summary", required=True)
    create.add_argument("--actor", default="Vlad")
    create.add_argument("--intent", required=True)
    create.add_argument("--surface", choices=["jar", "home_center", "vlad"], default="vlad")
    create.add_argument("--decision-action", required=True)
    create.add_argument("--input-text", default="")
    create.add_argument("--output-text", default="")
    create.add_argument("--input-file")
    create.add_argument("--output-file")
    create.add_argument("--output-status", default="created")
    create.add_argument("--request-id", default="")
    create.add_argument("--reference", action="append", default=[])
    return root


def read_value(path: str | None, value: str) -> str:
    return Path(path).expanduser().read_text(encoding="utf-8", errors="replace") if path else value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        config = read_config(Path(args.config).expanduser())
        if args.command == "status":
            print(json.dumps(status(config), ensure_ascii=False, indent=2, sort_keys=True))
            return 0
        if args.command == "flush":
            result = flush(config, limit=args.limit)
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
            return 0 if result.get("ok") is True else 1
        registry = read_registry(Path(args.cache).expanduser())
        if registry is None:
            raise ReceiptError("Judgment Jar cache is unavailable; run vlad-jars sync first")
        input_text = read_value(args.input_file, args.input_text)
        output_text = read_value(args.output_file, args.output_text)
        request_id, group_id = args.request_id or str(uuid.uuid4()), str(uuid.uuid4())
        results = []
        for key in args.jars:
            jar = resolve_jar(registry, key)
            if jar is None:
                raise RegistryError(f"unknown Judgment Jar: {key}")
            references = [str(x) for x in (jar.get("sourcePath"), jar.get("sourceUrl"), jar.get("sourceFileId")) if x]
            results.append(record(
                registry, jar, config,
                output_kind=args.output_kind,
                output_text=output_text,
                summary=args.summary,
                actor=args.actor,
                intent=args.intent,
                surface=args.surface,
                decision_action=args.decision_action,
                input_text=input_text,
                output_status=args.output_status,
                request_id=request_id,
                group_id=group_id,
                references=[*references, *args.reference],
                source="jar-receipt",
            ))
        print(json.dumps({
            "ok": all(result.get("ok") for result in results),
            "requestId": request_id,
            "groupId": group_id,
            "receipts": results,
        }, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (ReceiptError, RegistryError, OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
