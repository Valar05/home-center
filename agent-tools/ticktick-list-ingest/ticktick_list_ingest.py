#!/usr/bin/env python3
"""Agent-facing TickTick list ingestion tool for Home Center.

Fetches a TickTick project/list through the public Open API and echoes active
items as plain terminal lines. The tool intentionally has no Android UI or app
state dependency, so agents can use it directly from Termux.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

PROJECTS_URL = "https://api.ticktick.com/open/v1/project"
DEFAULT_CACHE = Path(__file__).resolve().parent / "data" / "last_ingest.json"
TOKEN_ENV_KEYS = ("TICKTICK_TOKEN", "TICKTICK_API_TOKEN", "TIKTIK_TOKEN")


@dataclass(frozen=True)
class Project:
    id: str
    name: str


class TickTickIngestError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def normalize(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def simplify_list_name(value: str | None) -> str:
    cleaned = re.sub(r"[^a-z0-9 ]", " ", normalize(value))
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if cleaned.endswith(" list"):
        cleaned = cleaned[:-5].strip()
    if cleaned in {"shopping list", "groceries", "grocery", "shop"}:
        return "shopping"
    return cleaned


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
    tmp.replace(path)


def read_token_file(path: Path) -> str:
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return ""
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.strip() in TOKEN_ENV_KEYS:
            return value.strip().strip('"').strip("'")
    return raw.splitlines()[0].strip().strip('"').strip("'")


def resolve_token(args: argparse.Namespace) -> str:
    if getattr(args, "token", None):
        return args.token.strip()
    if getattr(args, "token_file", None):
        return read_token_file(Path(args.token_file).expanduser())
    for key in TOKEN_ENV_KEYS:
        value = os.environ.get(key, "").strip()
        if value:
            return value
    return ""


def http_json(url: str, token: str, timeout: int = 25) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "home-center-agent-ticktick-ingest/1.0",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise TickTickIngestError(f"TickTick returned HTTP {exc.code}: {body[:240]}") from exc
    except urllib.error.URLError as exc:
        raise TickTickIngestError(f"TickTick request failed: {exc.reason}") from exc
    if not body.strip():
        return None
    return json.loads(body)


def fetch_projects(token: str) -> list[Project]:
    data = http_json(PROJECTS_URL, token)
    if not isinstance(data, list):
        raise TickTickIngestError("TickTick project response was not a JSON list")
    projects: list[Project] = []
    for row in data:
        if not isinstance(row, dict):
            continue
        project_id = str(row.get("id") or row.get("projectId") or "").strip()
        name = str(row.get("name") or row.get("title") or "").strip()
        if project_id and name:
            projects.append(Project(project_id, name))
    return projects


def find_project(projects: Iterable[Project], requested_name: str) -> Project:
    project_list = list(projects)
    target = simplify_list_name(requested_name)
    for project in project_list:
        if simplify_list_name(project.name) == target:
            return project
    for project in project_list:
        candidate = simplify_list_name(project.name)
        if target and (target in candidate or candidate in target):
            return project
    if target == "shopping":
        for project in project_list:
            candidate = simplify_list_name(project.name)
            if "shopping" in candidate or "grocery" in candidate or "grocerie" in candidate:
                return project
    available = ", ".join(project.name for project in project_list[:8]) or "no TickTick lists"
    if len(project_list) > 8:
        available += f", and {len(project_list) - 8} more"
    raise TickTickIngestError(f"Could not find list {requested_name!r}. Available: {available}")


def fetch_project_data(token: str, project_id: str) -> dict[str, Any]:
    data = http_json(f"{PROJECTS_URL}/{project_id}/data", token)
    if not isinstance(data, dict):
        raise TickTickIngestError("TickTick project data response was not a JSON object")
    return data


def is_completed(task: dict[str, Any]) -> bool:
    if task.get("deleted") is True:
        return True
    if task.get("completed") is True:
        return True
    status = task.get("status")
    try:
        status_int = int(status)
    except (TypeError, ValueError):
        status_int = 0
    return status_int == 2 or (status_int == 1 and bool(task.get("completedTime")))


def title_for_task(task: dict[str, Any]) -> str:
    for key in ("title", "content"):
        value = task.get(key)
        if isinstance(value, str) and value.strip():
            return re.sub(r"\s+", " ", value).strip()
    return ""


def extract_items(project_data: dict[str, Any]) -> list[dict[str, Any]]:
    tasks = project_data.get("tasks")
    if tasks is None:
        tasks = project_data.get("syncTaskBean")
    if not isinstance(tasks, list):
        return []
    items: list[dict[str, Any]] = []
    seen_titles: set[str] = set()
    for task in tasks:
        if not isinstance(task, dict) or is_completed(task):
            continue
        title = title_for_task(task)
        if not title:
            continue
        dedupe_key = normalize(title)
        if dedupe_key in seen_titles:
            continue
        seen_titles.add(dedupe_key)
        items.append({
            "title": title,
            "id": str(task.get("id") or task.get("taskId") or ""),
            "status": task.get("status", 0),
        })
    return items


def live_ingest(args: argparse.Namespace) -> dict[str, Any]:
    token = resolve_token(args)
    if not token:
        keys = ", ".join(TOKEN_ENV_KEYS)
        raise TickTickIngestError(f"Missing TickTick token. Set one of: {keys}, or pass --token-file.")
    projects = fetch_projects(token)
    project = find_project(projects, args.list)
    project_data = fetch_project_data(token, project.id)
    items = extract_items(project_data)
    return build_document("ticktick", args.list, project.name, project.id, items)


def fixture_ingest(args: argparse.Namespace) -> dict[str, Any]:
    source = read_json(Path(args.fixture))
    if isinstance(source, dict) and "items" in source and all(isinstance(item, str) for item in source["items"]):
        items = [{"title": item, "id": "", "status": 0} for item in source["items"]]
        return build_document("fixture", args.list, source.get("list_name", args.list), source.get("project_id", ""), items)
    if not isinstance(source, dict):
        raise TickTickIngestError("Fixture must be a TickTick project-data object or an ingest document")
    items = extract_items(source)
    return build_document("fixture", args.list, source.get("name", args.list), source.get("projectId", ""), items)


def cache_ingest(args: argparse.Namespace) -> dict[str, Any]:
    path = Path(args.cache or DEFAULT_CACHE)
    data = read_json(path)
    if not isinstance(data, dict) or "items" not in data:
        raise TickTickIngestError(f"Cache {path} is not an ingest document")
    return data


def build_document(source: str, requested: str, list_name: str, project_id: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "source": source,
        "fetched_at": now_iso(),
        "list_requested": requested,
        "list_name": list_name,
        "project_id": project_id,
        "item_count": len(items),
        "items": items,
    }


def load_document(args: argparse.Namespace) -> dict[str, Any]:
    if args.fixture:
        return fixture_ingest(args)
    if args.from_cache:
        return cache_ingest(args)
    return live_ingest(args)


def item_titles(document: dict[str, Any]) -> list[str]:
    titles: list[str] = []
    for item in document.get("items", []):
        if isinstance(item, str):
            title = item.strip()
        elif isinstance(item, dict):
            title = str(item.get("title") or "").strip()
        else:
            title = ""
        if title:
            titles.append(title)
    return titles


def verify_count(titles: list[str], expected: int | None) -> None:
    if expected is None:
        return
    if len(titles) != expected:
        raise TickTickIngestError(f"Expected {expected} items, got {len(titles)}")


def add_common_source_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--list", default="shopping", help="TickTick list/project name to ingest; default: shopping")
    parser.add_argument("--token", help="TickTick token. Prefer environment or --token-file so shell history does not capture secrets.")
    parser.add_argument("--token-file", help="File containing a raw token or TICKTICK_TOKEN=value")
    parser.add_argument("--fixture", help="Read a local TickTick project-data JSON fixture instead of calling TickTick")
    parser.add_argument("--from-cache", action="store_true", help="Read the last ingest/cache document instead of calling TickTick")
    parser.add_argument("--cache", default=str(DEFAULT_CACHE), help="Cache path for ingest/readback")
    parser.add_argument("--expect-count", type=int, help="Fail unless this many active items are present")


def command_echo(args: argparse.Namespace) -> int:
    document = load_document(args)
    titles = item_titles(document)
    verify_count(titles, args.expect_count)
    for title in titles:
        print(title)
    print(f"echoed {len(titles)} items from {document.get('list_name', args.list)}", file=sys.stderr)
    return 0


def command_ingest(args: argparse.Namespace) -> int:
    document = load_document(args)
    titles = item_titles(document)
    verify_count(titles, args.expect_count)
    write_json(Path(args.cache), document)
    if args.echo:
        for title in titles:
            print(title)
    else:
        print(json.dumps({
            "cache": str(Path(args.cache)),
            "list_name": document.get("list_name"),
            "item_count": len(titles),
        }, indent=2, sort_keys=True))
    return 0


def command_projects(args: argparse.Namespace) -> int:
    token = resolve_token(args)
    if not token:
        keys = ", ".join(TOKEN_ENV_KEYS)
        raise TickTickIngestError(f"Missing TickTick token. Set one of: {keys}, or pass --token-file.")
    for project in fetch_projects(token):
        print(project.name)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch and echo Home Center shopping items from TickTick for agents.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    echo = subparsers.add_parser("echo", help="Print active list items, one per line")
    add_common_source_args(echo)
    echo.set_defaults(func=command_echo)

    ingest = subparsers.add_parser("ingest", help="Fetch/read list items and write a cache document")
    add_common_source_args(ingest)
    ingest.add_argument("--echo", action="store_true", help="Also print item titles, one per line")
    ingest.set_defaults(func=command_ingest)

    projects = subparsers.add_parser("projects", help="Print available TickTick project/list names")
    projects.add_argument("--token", help="TickTick token. Prefer environment or --token-file.")
    projects.add_argument("--token-file", help="File containing a raw token or TICKTICK_TOKEN=value")
    projects.set_defaults(func=command_projects)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except TickTickIngestError as exc:
        print(f"ticktick-list-ingest: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
