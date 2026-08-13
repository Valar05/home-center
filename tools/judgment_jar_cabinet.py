#!/usr/bin/env python3
"""Parse the Home Center Judgment Jar cabinet and discovery results."""
from __future__ import annotations

import re
from typing import Any

from judgment_jar_common import (
    CABINET_ORIGIN, DISCOVERY_ORIGIN, RegistryError, aliases_for, normalize_key, sha256_text,
)


def paragraphs(text: str) -> list[str]:
    text = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    return [line.strip() for line in text.split("\n") if line.strip()]


def url_source(url: str) -> tuple[str, str]:
    match = re.search(r"https://docs\.google\.com/(spreadsheets|document)/d/([^/\s?]+)", url)
    if not match:
        return "", "unknown"
    return match.group(2), "spreadsheet" if match.group(1) == "spreadsheets" else "document"


FIELD_PREFIXES = {
    "Governor": "governor", "Home": "home", "Legacy home": "home", "Status": "statusText",
    "Boundary": "boundary", "Judgment": "judgment", "Judgment question": "judgment",
    "Load-bearing mixed verdict": "mixedVerdict", "Hard gates": "hardGates",
    "Hard-gate families": "hardGates", "Hard boundary": "hardGates",
    "Forbidden flattening": "forbiddenFlattening", "Forbidden flattenings": "forbiddenFlattening",
    "Compact law": "compactLaw", "Run order": "runOrder", "Primary verdict": "primaryVerdict",
    "Baseline verdict": "primaryVerdict", "Current readback": "primaryVerdict",
    "Consultation rule": "consultationRule", "Native Jar": "nativeJar", "Wound": "wound",
    "Lineage": "lineage", "Capability state": "capabilityState",
}


def segment_fields(lines: list[str]) -> dict[str, str]:
    found: dict[str, str] = {}
    for line in lines:
        for prefix, key in FIELD_PREFIXES.items():
            marker = prefix + ":"
            if line.startswith(marker):
                found[key] = line[len(marker):].strip()
                break
    return found


def registry_section(lines: list[str], title_index: int) -> str:
    for index in range(title_index - 1, -1, -1):
        if lines[index].isupper() and len(lines[index]) > 5:
            return lines[index]
    return "UNSCOPED CABINET ENTRY"


def cabinet_entry(title: str, body: str, fields: dict[str, str], source_url: str,
                  registry_file_id: str, registry_title: str, section_name: str, order: int) -> dict[str, Any]:
    file_id, source_type = url_source(source_url)
    status_text = fields.get("statusText", "").lower()
    if "repair required" in status_text or source_type == "document":
        status = "repair-required"
    elif "candidate" in status_text or "candidate" in title.lower():
        status = "candidate"
    else:
        status = "mature"
    identifier = normalize_key(title)
    return {
        "id": identifier, "order": order, "title": title, "status": status,
        "scope": fields.get("home", section_name),
        "judgment": fields.get("judgment") or fields.get("boundary") or "",
        "origin": CABINET_ORIGIN, "sourceAuthority": "home-center-native-registry",
        "sourceCompleteness": "cabinet-summary; native source remains controlling",
        "sourcePath": f"home-center://drive/{file_id}", "sourceSha256": sha256_text(body),
        "sourceFileId": file_id, "sourceType": source_type, "sourceUrl": source_url,
        "registryFileId": registry_file_id, "registryTitle": registry_title,
        "registrySection": section_name, "aliases": aliases_for(identifier, title), "body": body,
        **{key: value for key, value in fields.items() if key not in {"statusText", "nativeJar"} and value},
    }


def parse_cabinet_registry(text: str, source_file_id: str, source_title: str) -> dict[str, Any]:
    lines = paragraphs(text)
    governors = [i for i, line in enumerate(lines) if line.startswith("Governor:")]
    entries: list[dict[str, Any]] = []
    for position, governor_index in enumerate(governors):
        title_index = governor_index - 1
        if title_index < 0:
            continue
        end = governors[position + 1] - 1 if position + 1 < len(governors) else len(lines)
        segment = lines[title_index:end]
        fields = segment_fields(segment)
        title = fields.get("nativeJar") or lines[title_index]
        urls = re.findall(r"https://docs\.google\.com/(?:spreadsheets|document)/d/[^\s]+", "\n".join(segment))
        if not urls:
            continue
        source_url = next((url for url in urls if "/spreadsheets/" in url), urls[0]).rstrip(".,);]")
        if not url_source(source_url)[0]:
            continue
        body = "\n".join(segment).rstrip() + "\n"
        entries.append(cabinet_entry(title, body, fields, source_url, source_file_id, source_title,
                                     registry_section(lines, title_index), 10_000 + len(entries)))

    missing: list[str] = []
    try:
        start = lines.index("MISSING EXECUTABLE FUNCTIONS") + 1
        end = lines.index("BUILD ORDER", start)
        missing = [line for line in lines[start:end] if re.match(r"^\d+\.\s+", line)]
    except ValueError:
        pass

    randi = re.search(
        r"(?ims)^RANDI — GOVERNING QUIRK THEORY:.*?^Existing workbook:\s*(https://docs\.google\.com/spreadsheets/d/[^\s]+).*?^Compact law:\s*(.+?)$",
        text,
    )
    if randi:
        source_url = randi.group(1).rstrip(".,);]")
        title = "Randi — Edge or Gloss"
        fields = {
            "governor": "Character — Randi",
            "home": "Judgment Jar cabinet",
            "judgment": "Does polish preserve recoverable truth and action, or disguise waste and uncertainty?",
            "compactLaw": randi.group(2).strip(),
        }
        entries.append(cabinet_entry(title, randi.group(0).strip() + "\n", fields, source_url,
                                     source_file_id, source_title,
                                     "RANDI — GOVERNING QUIRK THEORY", 10_000 + len(entries)))

    if "REGISTRY CORRECTION — DYONISIS DEBT CLOSED" in text:
        missing = [line for line in missing if "Dyonisis" not in line]
    if not entries:
        raise RegistryError("Home Center Judgment Jar registry contained no routed entries")
    ids: set[str] = set()
    for entry in entries:
        if entry["id"] in ids:
            raise RegistryError(f"duplicate Home Center cabinet Jar id: {entry['id']}")
        ids.add(entry["id"])
    return {
        "registryFileId": source_file_id, "registryTitle": source_title,
        "registryText": text, "registryTextSha256": sha256_text(text),
        "cabinetEntries": entries, "cabinetCount": len(entries),
        "missingExecutableFunctions": missing,
    }


def parse_discovered_files(files: list[dict[str, Any]], registered: set[str], registry_file_id: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in files:
        file_id = str(item.get("id") or "").strip()
        title = str(item.get("name") or item.get("title") or "").strip()
        if not file_id or file_id == registry_file_id or file_id in registered or file_id in seen or "jar" not in title.lower():
            continue
        mime = str(item.get("mimeType") or item.get("mime_type") or "")
        if "spreadsheet" in mime:
            source_type = "spreadsheet"
            source_url = str(item.get("webViewLink") or f"https://docs.google.com/spreadsheets/d/{file_id}/edit")
        elif "document" in mime:
            source_type = "document"
            source_url = str(item.get("webViewLink") or f"https://docs.google.com/document/d/{file_id}/edit")
        else:
            continue
        seen.add(file_id)
        identifier = normalize_key(title)
        body = f"{title}\nStatus: Discovered by Home Center search; missing from the cabinet registry.\nLink: {source_url}\nModified: {item.get('modifiedTime') or item.get('modified_time') or ''}\n"
        entries.append({
            "id": identifier, "order": 20_000 + len(entries), "title": title,
            "status": "unregistered", "scope": "Home Center discovery; cabinet registration required",
            "judgment": "", "origin": DISCOVERY_ORIGIN,
            "sourceAuthority": "home-center-drive-search",
            "sourceCompleteness": "metadata-only; native source and registry repair required",
            "sourcePath": f"home-center://drive/{file_id}", "sourceSha256": sha256_text(body),
            "sourceFileId": file_id, "sourceType": source_type, "sourceUrl": source_url,
            "modifiedTime": item.get("modifiedTime") or item.get("modified_time") or "",
            "aliases": aliases_for(identifier, title), "body": body,
        })
    return entries

