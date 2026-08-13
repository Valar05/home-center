#!/usr/bin/env python3
"""Fast deterministic Judgment Jar access for Vlad.

`vlad jars` lists the current repository-backed catalog.
`vlad jar <id>` returns one exact Jar and receipts the context packet.
`vlad jar receipt ...` records the output produced by an already-completed use.
All other `vlad ...` text remains the existing bounded Vlad consultation lane.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import adam
import judgement_jar_runtime as jars


def _print_catalog(as_json: bool = False) -> int:
    pending = jars.sync_pending()
    sync = jars.sync_catalog()
    values = jars.catalog(include_text=False)
    if as_json:
        print(json.dumps({
            "schema": "vlad-judgement-jar-catalog-response.v1",
            "ok": True,
            "count": len(values),
            "jars": values,
            "pendingSync": pending,
            "catalogSync": sync,
        }, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    for item in values:
        print(f"{int(item['order']):02d}  {item['id']}  {item['title']}")
    print(f"{len(values)} Judgment Jars; source=.continue/rules; Home Center sync={sync.get('state')}")
    return 0


def _show(reference: str, as_json: bool = False) -> int:
    item = jars.resolve_jar(reference, include_text=True)
    usage = jars.record_usage(
        str(item["path"]),
        output_kind="context_packet",
        output_summary=f"Vlad loaded exact Judgment Jar context: {item['title']}",
        source="vlad.jar.show",
        status="created",
        input_text=reference,
        output_text=str(item.get("text") or ""),
        output_refs=[str(item["path"])],
        metadata={"access": "fast", "catalogSha256": jars.catalog_snapshot()["catalogSha256"]},
    )
    if as_json:
        print(json.dumps({"ok": True, "jar": item, "usage": usage}, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(str(item.get("text") or "").rstrip())
        receipt = usage["receipt"]
        print(f"\nJAR_RECEIPT {receipt['receiptId']} output={receipt['output']['kind']} HomeCenter={usage['homeCenter'].get('state', 'PENDING')}")
    return 0


def _receipt(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="vlad jar receipt")
    parser.add_argument("jar")
    parser.add_argument("--output-kind", required=True, choices=sorted(jars.OUTPUT_KINDS))
    parser.add_argument("--summary", required=True)
    parser.add_argument("--source", default="vlad.jar.receipt")
    parser.add_argument("--status", default="created")
    parser.add_argument("--request-id")
    parser.add_argument("--input", default="")
    parser.add_argument("--output", default="")
    parser.add_argument("--ref", action="append", default=[])
    args = parser.parse_args(argv)
    result = jars.record_usage(
        args.jar,
        output_kind=args.output_kind,
        output_summary=args.summary,
        source=args.source,
        status=args.status,
        input_text=args.input,
        output_text=args.output,
        request_id=args.request_id,
        output_refs=args.ref,
        metadata={"recordedBy": "Vlad"},
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _jar_command(argv: list[str]) -> int:
    if not argv or argv[0] in {"list", "ls", "jars"}:
        return _print_catalog("--json" in argv)
    command = argv[0]
    if command == "sync":
        print(json.dumps({"pending": jars.sync_pending(), "catalog": jars.sync_catalog()}, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if command == "status":
        print(json.dumps(jars.status(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if command in {"receipt", "use"}:
        return _receipt(argv[1:])
    if command in {"show", "get"}:
        parser = argparse.ArgumentParser(prog=f"vlad jar {command}")
        parser.add_argument("jar")
        parser.add_argument("--json", action="store_true")
        args = parser.parse_args(argv[1:])
        return _show(args.jar, args.json)
    as_json = "--json" in argv[1:]
    return _show(command, as_json)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"jars", "jar"}:
        if not args:
            return _print_catalog(False)
        return _jar_command(args[1:])
    return adam.run_mode("vlad", " ".join(args), str(Path.cwd().resolve()), 300)


if __name__ == "__main__":
    raise SystemExit(main())
