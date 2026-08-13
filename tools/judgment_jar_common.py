#!/usr/bin/env python3
"""Shared primitives for Vlad's Judgment Jar registry."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = Path(os.environ.get("HC_JUDGMENT_JARS_CONFIG", ROOT / "config/judgment-jars.v1.json")).expanduser()
DEFAULT_CACHE = Path(os.environ.get("HC_JUDGMENT_JARS_CACHE", "~/.local/state/home-center/vlad-swarm/judgment-jars.json")).expanduser()
SCHEMA = "home-center.judgment-jars.registry.v2"
LOCAL_ORIGIN = "repository-operational-core"
CABINET_ORIGIN = "home-center-cabinet"
DISCOVERY_ORIGIN = "home-center-discovery"


class RegistryError(RuntimeError):
    pass


def normalize_key(value: str) -> str:
    value = str(value or "").strip().lower().replace("judgement", "judgment")
    value = value.replace("’", "'").replace("×", " x ")
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def digest(value: Any) -> str:
    return sha256_text(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def read_config(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RegistryError(f"invalid Judgment Jar config {path}: {exc}") from exc
    if value.get("schema") != "home-center.judgment-jars.config.v1":
        raise RegistryError(f"unsupported Judgment Jar config schema in {path}")
    pattern = str(value.get("repositorySourcePattern") or "")
    if not pattern.startswith(".continue/rules/"):
        raise RegistryError("repositorySourcePattern must stay under .continue/rules")
    return value


def source_files(root: Path, config: dict[str, Any]) -> list[Path]:
    pattern = str(config["repositorySourcePattern"]).removeprefix(".continue/rules/")
    files = sorted(p for p in (root / ".continue" / "rules").glob(pattern) if p.is_file())
    if not files:
        raise RegistryError(f"no Judgment Jars found for {config['repositorySourcePattern']}")
    return files


def source_stat_digest(root: Path, files: list[Path]) -> str:
    return digest([
        {"path": p.relative_to(root).as_posix(), "size": p.stat().st_size, "mtimeNs": p.stat().st_mtime_ns}
        for p in files
    ])


def source_commit(root: Path) -> str:
    try:
        result = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], text=True, capture_output=True, timeout=5)
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def field(text: str, name: str, default: str = "") -> str:
    match = re.search(rf"(?im)^{re.escape(name)}\s*:\s*(.+?)\s*$", text)
    return match.group(1).strip() if match else default


def section(text: str, heading: str) -> str:
    match = re.search(rf"(?ims)^##\s+{re.escape(heading)}\s*$\n(.*?)(?=^##\s+|\Z)", text)
    return match.group(1).strip() if match else ""


def aliases_for(identifier: str, title: str, extras: list[str] | None = None) -> list[str]:
    short = re.sub(r"(?i)^judg(?:e)?ment\s+jar\s*[:—-]\s*", "", title).strip()
    values = {identifier, title, short, f"judgment jar {short}", f"judgement jar {short}", *(extras or [])}
    return sorted({normalize_key(value) for value in values if normalize_key(value)})


def parse_local_jar(root: Path, path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    title_match = re.search(r"(?m)^#\s+(.+?)\s*$", text)
    title = title_match.group(1).strip() if title_match else path.stem
    order_match = re.match(r"^(\d+)-", path.stem)
    order = int(order_match.group(1)) if order_match else 9999
    identifier = normalize_key(re.sub(r"^judgement-jar-", "", re.sub(r"^\d+-", "", path.stem)))
    return {
        "id": identifier,
        "order": order,
        "title": title,
        "status": field(text, "Status", "unknown").lower(),
        "scope": field(text, "Scope"),
        "judgment": section(text, "Judgement") or section(text, "Judgment"),
        "origin": LOCAL_ORIGIN,
        "sourceAuthority": "git-repository",
        "sourceCompleteness": "complete-body",
        "sourcePath": path.relative_to(root).as_posix(),
        "sourceSha256": sha256_text(text),
        "aliases": aliases_for(identifier, title, [path.stem]),
        "body": text.rstrip() + "\n",
    }


def read_registry(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) and value.get("schema") == SCHEMA else None


def write_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, path)

