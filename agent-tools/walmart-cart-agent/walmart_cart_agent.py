#!/usr/bin/env python3
"""Assisted Walmart cart mapper for Home Center agents.

V1 does not scrape a logged-in Walmart account or place orders. It turns a live
shopping list into a durable review queue, preserves problem areas, and opens
Walmart Buy Again/search/product links for human-confirmed add-to-cart work.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.parse
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
TICKTICK = ROOT / "agent-tools" / "ticktick-list-ingest" / "ticktick_list_ingest.py"
DEFAULT_TOKEN_FILE = ROOT / "agent-tools" / "ticktick-list-ingest" / ".secrets" / "ticktick_token"
DEFAULT_REVIEW = Path(__file__).resolve().parent / "data" / "review_queue.json"
DEFAULT_PROBLEMS = Path(__file__).resolve().parent / "data" / "problem_areas.jsonl"
DEFAULT_ACCEPTED = Path(__file__).resolve().parent / "data" / "accepted_mappings.json"
DEFAULT_EXPORT_DIR = Path("/storage/emulated/0/Download/HomeCenter/cart-review")
EXPORT_REVIEW_NAME = "review-latest.json"
EXPORT_COMMANDS_NAME = "review-latest.commands.txt"
WALMART_SEARCH = "https://www.walmart.com/search?q={query}"
WALMART_BUY_AGAIN = "https://www.walmart.com/my-items"
WALMART_PRODUCT = "https://www.walmart.com/ip/{sku}"

QUANTITY_RE = re.compile(r"(?:\s|^)x\s*(\d+|many)\s*$", re.IGNORECASE)
QUESTION_RE = re.compile(r"\?\s*$")
SPLIT_EXACT = {
    "hot dogs and sausages and buns": ["hot dogs", "sausages", "buns"],
    "flour, and sugar x 2": ["flour", "sugar x 2"],
}


@dataclass
class ReviewItem:
    key: str
    raw: str
    item: str
    quantity: int | None
    quantity_text: str
    status: str
    reason: str
    candidate_count: int
    candidates: list[dict[str, Any]]
    walmart_search_url: str
    walmart_buy_again_url: str
    save_command: str


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def key_for(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", normalize(value)).strip("_")
    return cleaned or "item"


def search_url(query: str) -> str:
    return WALMART_SEARCH.format(query=urllib.parse.quote_plus(query))


def product_url(sku: str) -> str:
    return WALMART_PRODUCT.format(sku=urllib.parse.quote(str(sku).strip()))


def parse_item(raw: str) -> tuple[str, int | None, str, list[str]]:
    clean = raw.strip()
    quantity: int | None = 1
    quantity_text = "1"
    if QUESTION_RE.search(clean):
        clean = QUESTION_RE.sub("", clean).strip()
        quantity = None
        quantity_text = "?"
    match = QUANTITY_RE.search(clean)
    if match:
        token = match.group(1).lower()
        clean = QUANTITY_RE.sub("", clean).strip()
        if token == "many":
            quantity = None
            quantity_text = "many"
        else:
            quantity = int(token)
            quantity_text = token
    exact = normalize(raw)
    split_items = SPLIT_EXACT.get(exact, [])
    return clean, quantity, quantity_text, split_items


def split_shopping_items(items: list[str]) -> list[tuple[str, str]]:
    expanded: list[tuple[str, str]] = []
    for raw in items:
        _item, _quantity, _quantity_text, split_items = parse_item(raw)
        if split_items:
            for split in split_items:
                expanded.append((raw, split))
        else:
            expanded.append((raw, raw))
    return expanded


def load_items(args: argparse.Namespace) -> list[str]:
    if args.fixture:
        data = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [str(item) for item in data]
        if isinstance(data, dict) and "items" in data:
            out = []
            for item in data["items"]:
                if isinstance(item, str):
                    out.append(item)
                elif isinstance(item, dict):
                    out.append(str(item.get("title") or item.get("name") or ""))
            return [item for item in out if item]
        raise SystemExit("fixture must be a list, ingest document, or object with items")
    cmd = [sys.executable, str(TICKTICK), "ingest", "--list", args.list, "--cache", str(args.ticktick_cache)]
    if args.expect_count:
        cmd.extend(["--expect-count", str(args.expect_count)])
    if args.token_file:
        cmd.extend(["--token-file", args.token_file])
    elif DEFAULT_TOKEN_FILE.exists():
        cmd.extend(["--token-file", str(DEFAULT_TOKEN_FILE)])
    subprocess.run(cmd, cwd=ROOT, check=True, text=True, capture_output=True)
    data = json.loads(Path(args.ticktick_cache).read_text(encoding="utf-8"))
    return [str(item.get("title") or item.get("name") or "") for item in data.get("items", []) if isinstance(item, dict)]


def load_mappings(path: str | None) -> dict[str, Any]:
    candidates = [Path(path)] if path else [DEFAULT_ACCEPTED]
    for candidate in candidates:
        if candidate.exists():
            data = json.loads(candidate.read_text(encoding="utf-8"))
            return data.get("storeTargets", data) if isinstance(data, dict) else {}
    return {}


def mapping_for(mappings: dict[str, Any], item: str) -> dict[str, Any] | None:
    key = key_for(item)
    record = mappings.get(key) or mappings.get(normalize(item))
    return record if isinstance(record, dict) else None


def candidate_from_mapping(record: dict[str, Any]) -> dict[str, Any]:
    sku = str(record.get("sku") or "").strip()
    url = str(record.get("productUrl") or "").strip() or (product_url(sku) if sku else "")
    return {
        "source": record.get("source") or "saved_mapping",
        "sku": sku,
        "productName": record.get("productName") or "",
        "productUrl": url,
        "quantity": record.get("quantity") or "",
        "confidence": record.get("confidence") or "confirmed",
    }


def target_spec(candidate: dict[str, Any], quantity: int | None, quantity_text: str) -> str:
    fields = {
        "sku": candidate.get("sku", ""),
        "productUrl": candidate.get("productUrl", ""),
        "productName": candidate.get("productName", ""),
        "quantity": str(quantity) if quantity is not None else "",
        "unitPreference": quantity_text if quantity is None else "",
        "source": candidate.get("source", "agent_review"),
        "confidence": candidate.get("confidence", "confirmed"),
    }
    return "|".join(f"{name}={str(value).replace('|', ' ').strip()}" for name, value in fields.items() if str(value).strip())


def build_review(args: argparse.Namespace) -> dict[str, Any]:
    raw_items = load_items(args)
    mappings = load_mappings(args.mappings)
    review: list[ReviewItem] = []
    problems: list[dict[str, Any]] = []
    for original, expanded in split_shopping_items(raw_items):
        item, quantity, quantity_text, _split = parse_item(expanded)
        key = key_for(item)
        record = mapping_for(mappings, item)
        candidates: list[dict[str, Any]] = []
        status = "needs_choice"
        reason = "open Walmart Buy Again first; use search fallback if history does not match"
        if record:
            candidate = candidate_from_mapping(record)
            candidates.append(candidate)
            status = "mapped" if quantity is not None else "needs_quantity"
            reason = "saved Walmart mapping found" if quantity is not None else "saved mapping found but quantity needs review"
        elif quantity is None:
            status = "needs_quantity"
            reason = "quantity is vague or marked for review"
        if original != expanded:
            reason = "split from combined shopping-list entry; " + reason
        if status != "mapped":
            problems.append({
                "at": now_iso(),
                "key": key,
                "raw": original,
                "item": item,
                "status": status,
                "reason": reason,
                "walmartBuyAgainUrl": WALMART_BUY_AGAIN,
                "walmartSearchUrl": search_url(item),
            })
        spec = target_spec(candidates[0], quantity, quantity_text) if candidates else "sku=REPLACE_ME|productUrl=REPLACE_ME|productName=REPLACE_ME|quantity=" + (str(quantity) if quantity is not None else "REVIEW") + "|source=buy_again|confidence=confirmed"
        review.append(ReviewItem(
            key=key,
            raw=original,
            item=item,
            quantity=quantity,
            quantity_text=quantity_text,
            status=status,
            reason=reason,
            candidate_count=len(candidates),
            candidates=candidates,
            walmart_search_url=search_url(item),
            walmart_buy_again_url=WALMART_BUY_AGAIN,
            save_command=f"map {item} to walmart target {spec}",
        ))
    return {
        "generatedAt": now_iso(),
        "source": "ticktick" if not args.fixture else "fixture",
        "itemCount": len(review),
        "statusCounts": status_counts(review),
        "review": [asdict(item) for item in review],
        "problemAreas": problems,
    }


def status_counts(items: list[ReviewItem]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        counts[item.status] = counts.get(item.status, 0) + 1
    return counts


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def read_review(path: str | Path) -> dict[str, Any]:
    review_path = Path(path)
    if not review_path.exists():
        raise SystemExit(f"review file not found: {review_path}")
    data = json.loads(review_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("review"), list):
        raise SystemExit("review file must contain a review array")
    return data


def actionable_items(data: dict[str, Any]) -> list[dict[str, Any]]:
    done_statuses = {"mapped", "saved", "verified"}
    return [item for item in data.get("review", []) if str(item.get("status") or "") not in done_statuses]


def find_review_item(data: dict[str, Any], key: str | None, item_name: str | None = None) -> tuple[int, dict[str, Any]]:
    clean_key = key_for(key or item_name or "") if key or item_name else ""
    for index, item in enumerate(data.get("review", [])):
        item_key = str(item.get("key") or "")
        item_name_value = str(item.get("item") or "")
        if clean_key and (item_key == clean_key or key_for(item_name_value) == clean_key):
            return index, item
    raise SystemExit(f"review item not found: {key or item_name}")


def refresh_review_counts(data: dict[str, Any]) -> None:
    counts: dict[str, int] = {}
    for item in data.get("review", []):
        status = str(item.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    data["itemCount"] = len(data.get("review", []))
    data["statusCounts"] = counts


def verified_product_name(item_name: str, brand: str, size: str, explicit: str) -> str:
    if explicit.strip():
        return explicit.strip()
    parts = [part.strip() for part in [brand, item_name, size] if part and part.strip()]
    return " ".join(parts)


def verified_target_spec(item: dict[str, Any], args: argparse.Namespace) -> str:
    product_name = verified_product_name(str(item.get("item") or ""), args.brand, args.size, args.product_name or "")
    fields = {
        "sku": args.sku or "",
        "productUrl": args.product_url or "",
        "productName": product_name,
        "quantity": str(args.quantity),
        "unitPreference": args.size or "",
        "brand": args.brand or "",
        "size": args.size or "",
        "source": args.source or "agent_verified",
        "confidence": args.confidence or "confirmed",
    }
    return "|".join(f"{name}={str(value).replace('|', ' ').strip()}" for name, value in fields.items() if str(value).strip())


def write_commands(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    commands = []
    for item in data.get("review", []):
        command = str(item.get("save_command") or "").strip()
        if command:
            commands.append(command)
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    tmp.write_text("\n".join(commands) + ("\n" if commands else ""), encoding="utf-8")
    tmp.replace(path)


def refresh_android_path(path: Path) -> bool:
    if os.name != "posix":
        return False
    uri = "file://" + urllib.parse.quote(str(path), safe="/")
    try:
        subprocess.run([
            "am",
            "broadcast",
            "-a",
            "android.intent.action.MEDIA_SCANNER_SCAN_FILE",
            "-d",
            uri,
        ], check=False, text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except FileNotFoundError:
        return False


def append_problems(path: Path, problems: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for problem in problems:
            handle.write(json.dumps(problem, sort_keys=True) + "\n")


def command_build_review(args: argparse.Namespace) -> int:
    doc = build_review(args)
    output = Path(args.output)
    write_json(output, doc)
    if args.problem_log:
        append_problems(Path(args.problem_log), doc["problemAreas"])
    print(json.dumps({
        "output": str(output),
        "itemCount": doc["itemCount"],
        "statusCounts": doc["statusCounts"],
        "problemCount": len(doc["problemAreas"]),
    }, indent=2, sort_keys=True))
    return 0


def command_export(args: argparse.Namespace) -> int:
    doc = build_review(args)
    output_dir = Path(args.output_dir)
    review_path = output_dir / EXPORT_REVIEW_NAME
    commands_path = output_dir / EXPORT_COMMANDS_NAME
    write_json(review_path, doc)
    write_commands(commands_path, doc)
    if args.problem_log:
        append_problems(Path(args.problem_log), doc["problemAreas"])
    refreshed = False
    if not args.no_refresh:
        refreshed = refresh_android_path(review_path)
        refreshed = refresh_android_path(commands_path) or refreshed
        refreshed = refresh_android_path(output_dir) or refreshed
    print(json.dumps({
        "review": str(review_path),
        "commands": str(commands_path),
        "itemCount": doc["itemCount"],
        "statusCounts": doc["statusCounts"],
        "problemCount": len(doc["problemAreas"]),
        "androidRefreshRequested": refreshed,
    }, indent=2, sort_keys=True))
    return 0


def command_next_item(args: argparse.Namespace) -> int:
    data = read_review(args.review)
    selected: dict[str, Any] | None = None
    selected_index = -1
    if args.key or args.item:
        selected_index, selected = find_review_item(data, args.key, args.item)
    else:
        for index, item in enumerate(data.get("review", [])):
            if str(item.get("status") or "") not in {"mapped", "saved", "verified"}:
                selected_index, selected = index, item
                break
    if selected is None:
        print(json.dumps({
            "done": True,
            "message": "all review items are mapped, saved, or verified",
            "itemCount": data.get("itemCount", 0),
            "statusCounts": data.get("statusCounts", {}),
        }, indent=2, sort_keys=True))
        return 0
    item_key = str(selected.get("key") or key_for(str(selected.get("item") or "")))
    agent_command = f"{sys.executable} {Path(__file__).resolve()}"
    print(json.dumps({
        "done": False,
        "index": selected_index + 1,
        "total": len(data.get("review", [])),
        "remaining": len(actionable_items(data)),
        "requiredVerification": ["brand", "size", "quantity"],
        "openBuyAgainCommand": f"{agent_command} open --review {args.review} --key {item_key} --surface buy-again",
        "openSearchCommand": f"{agent_command} open --review {args.review} --key {item_key} --surface search",
        "verifyCommandTemplate": f"{agent_command} verify-item --review {args.review} --key {item_key} --brand BRAND --size SIZE --quantity QUANTITY --sku SKU --product-url URL",
        "item": selected,
    }, indent=2, sort_keys=True))
    return 0


def command_verify_item(args: argparse.Namespace) -> int:
    data = read_review(args.review)
    index, item = find_review_item(data, args.key, args.item)
    item_name = str(item.get("item") or "").strip()
    product_name = verified_product_name(item_name, args.brand, args.size, args.product_name or "")
    candidate = {
        "source": args.source,
        "sku": args.sku or "",
        "productName": product_name,
        "productUrl": args.product_url or (product_url(args.sku) if args.sku else ""),
        "quantity": args.quantity,
        "brand": args.brand,
        "size": args.size,
        "confidence": args.confidence,
    }
    item["status"] = "verified"
    item["reason"] = "brand, size, and quantity verified by agent"
    item["quantity"] = args.quantity
    item["quantity_text"] = str(args.quantity)
    item["candidate_count"] = 1
    item["candidates"] = [candidate]
    item["verified"] = {
        "brand": args.brand,
        "size": args.size,
        "quantity": args.quantity,
        "verifiedAt": now_iso(),
        "verifiedBy": "agent",
    }
    item["save_command"] = f"map {item_name} to walmart target {verified_target_spec(item, args)}"
    data["review"][index] = item
    data["updatedAt"] = now_iso()
    refresh_review_counts(data)
    write_json(Path(args.review), data)
    if args.commands_output:
        write_commands(Path(args.commands_output), data)
    print(json.dumps({
        "review": str(Path(args.review)),
        "key": item.get("key"),
        "item": item_name,
        "status": item.get("status"),
        "verified": item.get("verified"),
        "save_command": item.get("save_command"),
        "nextRemaining": len(actionable_items(data)),
        "statusCounts": data.get("statusCounts", {}),
    }, indent=2, sort_keys=True))
    return 0


def command_report(args: argparse.Namespace) -> int:
    data = json.loads(Path(args.review).read_text(encoding="utf-8"))
    print("Walmart cart review")
    print("items:", data.get("itemCount", 0))
    print("statuses:", json.dumps(data.get("statusCounts", {}), sort_keys=True))
    for item in data.get("review", []):
        if item.get("status") == "mapped" and not args.all:
            continue
        print(f"- [{item.get('status')}] {item.get('item')} qty={item.get('quantity_text')} reason={item.get('reason')}")
        print(f"  buy-again: {item.get('walmart_buy_again_url')}")
        print(f"  search: {item.get('walmart_search_url')}")
        if item.get("save_command"):
            print(f"  save: {item.get('save_command')}")
    return 0


def command_open(args: argparse.Namespace) -> int:
    data = json.loads(Path(args.review).read_text(encoding="utf-8"))
    selected = None
    for item in data.get("review", []):
        if args.key and item.get("key") != args.key:
            continue
        if args.status and item.get("status") != args.status:
            continue
        selected = item
        break
    if not selected:
        print("no matching review item", file=sys.stderr)
        return 1
    url = selected.get("walmart_buy_again_url") if args.surface == "buy-again" else selected.get("walmart_search_url")
    if args.surface == "product" and selected.get("candidates"):
        url = selected["candidates"][0].get("productUrl") or url
    if args.dry_run:
        print(url)
        return 0
    opener = args.opener or "termux-open-url"
    subprocess.run([opener, url], check=True)
    print(f"opened {selected.get('key')} -> {url}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and operate a Home Center Walmart cart review queue.")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build-review", help="Ingest shopping items and write a Walmart review queue")
    build.add_argument("--list", default="shopping")
    build.add_argument("--expect-count", type=int, default=0)
    build.add_argument("--token-file")
    build.add_argument("--fixture")
    build.add_argument("--mappings")
    build.add_argument("--ticktick-cache", default=str(Path(__file__).resolve().parent / "data" / "ticktick_last_ingest.json"))
    build.add_argument("--output", default=str(DEFAULT_REVIEW))
    build.add_argument("--problem-log", default=str(DEFAULT_PROBLEMS))
    build.set_defaults(func=command_build_review)
    export = sub.add_parser("export", help="Write Android-visible review-latest files for the Home Center Cart Review UI")
    export.add_argument("--list", default="shopping")
    export.add_argument("--expect-count", type=int, default=0)
    export.add_argument("--token-file")
    export.add_argument("--fixture")
    export.add_argument("--mappings")
    export.add_argument("--ticktick-cache", default=str(Path(__file__).resolve().parent / "data" / "ticktick_last_ingest.json"))
    export.add_argument("--output-dir", default=str(DEFAULT_EXPORT_DIR))
    export.add_argument("--problem-log", default=str(DEFAULT_PROBLEMS))
    export.add_argument("--no-refresh", action="store_true")
    export.set_defaults(func=command_export)
    next_item = sub.add_parser("next-item", help="Emit the next item that needs brand, size, and quantity verification")
    next_item.add_argument("--review", default=str(DEFAULT_REVIEW))
    next_item.add_argument("--key")
    next_item.add_argument("--item")
    next_item.set_defaults(func=command_next_item)
    verify_item = sub.add_parser("verify-item", help="Mark one review item verified after checking brand, size, and quantity")
    verify_item.add_argument("--review", default=str(DEFAULT_REVIEW))
    verify_item.add_argument("--key")
    verify_item.add_argument("--item")
    verify_item.add_argument("--brand", required=True)
    verify_item.add_argument("--size", required=True)
    verify_item.add_argument("--quantity", required=True, type=int)
    verify_item.add_argument("--sku")
    verify_item.add_argument("--product-url")
    verify_item.add_argument("--product-name")
    verify_item.add_argument("--source", default="agent_verified")
    verify_item.add_argument("--confidence", default="confirmed")
    verify_item.add_argument("--commands-output")
    verify_item.set_defaults(func=command_verify_item)
    report = sub.add_parser("report", help="Print unresolved review items and save commands")
    report.add_argument("--review", default=str(DEFAULT_REVIEW))
    report.add_argument("--all", action="store_true")
    report.set_defaults(func=command_report)
    open_cmd = sub.add_parser("open", help="Open the first matching Walmart handoff link")
    open_cmd.add_argument("--review", default=str(DEFAULT_REVIEW))
    open_cmd.add_argument("--key")
    open_cmd.add_argument("--status")
    open_cmd.add_argument("--surface", choices=["buy-again", "search", "product"], default="buy-again")
    open_cmd.add_argument("--opener")
    open_cmd.add_argument("--dry-run", action="store_true")
    open_cmd.set_defaults(func=command_open)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
