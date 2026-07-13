#!/usr/bin/env python3
"""Scan exported Google Doc text for structured Drive Narrate speaker profiles.

Inputs are local .txt/.md/.json exports. JSON may be a Home Center _drive_read
payload with {name, fileId, text}. The scanner only trusts explicit structured
cues: [voice:id], [speaker:name], and uppercase speaker headings like NAME:.
It can merge new starter rows into the Home Drive character registry markdown.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

DEFAULT_GATEWAY = "https://us-central1-home-center-dclar.cloudfunctions.net"
DEFAULT_ACOUSTIC = "artificial voice pitch; satisfying acoustic distortion"
DEFAULT_NARRATOR = "Brian"

VOICE_HINTS = {
    "narrator": "Cartesia Narrator",
    "drew": "Chris - Charming, Down-to-Earth",
    "andrew": "Daniel - Steady Broadcaster",
    "droobiedoo": "Droobiedoo",
    "she-raw": "",
    "sheraw": "",
    "care-unit": "Alice - Clear, Engaging Educator",
    "elvis": "Roger - Laid-Back, Casual, Resonant",
    "washington": "Bill - Wise, Mature, Balanced",
    "george-washington": "Bill - Wise, Mature, Balanced",
    "mara": "Sarah - Mature, Reassuring, Confident",
    "tomas": "Will - Relaxed Optimist",
    "continuity-director": "Adam - Dominant, Firm",
    "director": "Adam - Dominant, Firm",
    "clerk": "River - Relaxed, Neutral, Informative",
    "doctor": "Matilda - Knowledgable, Professional",
    "technician": "Liam - Energetic, Social Media Creator",
    "maintenance-technician": "Liam - Energetic, Social Media Creator",
    "planning-director": "Eric - Smooth, Trustworthy",
    "quartermaster": "Callum - Husky Trickster",
    "camp-harrow": "Miles",
}

ROLE_HINTS = {
    "narrator": "narrator",
}

IGNORE_IDS = {
    "voice", "speaker", "section", "act", "scene", "title", "black", "sound",
    "visual", "choose", "consequences", "outcomes", "appendix", "format", "state",
    "truth-label", "fact-check", "documented-fact", "strong-inference", "weak-inference",
    "performance-note", "opening", "closing-image", "end-card", "system-effects",
}

@dataclass
class SourceDoc:
    name: str
    file_id: str
    text: str

@dataclass
class Candidate:
    name: str
    speaker_id: str
    cue: str
    source_name: str
    count: int = 1


def normalize_id(value: str) -> str:
    clean = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return clean or "speaker"


def title_name(value: str) -> str:
    value = re.sub(r"[_-]+", " ", value or "")
    value = re.sub(r"\s+", " ", value).strip()
    if not value:
        return ""
    if value == value.upper():
        small = {"and", "of", "the", "a", "an"}
        parts = []
        for part in value.lower().split():
            if part in small and parts:
                parts.append(part)
            else:
                parts.append(part[:1].upper() + part[1:])
        return " ".join(parts)
    return value


def load_doc(path: Path) -> SourceDoc:
    raw = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() == ".json":
        payload = json.loads(raw)
        text = payload.get("text") or payload.get("content") or ""
        meta = payload.get("metadata") or {}
        name = payload.get("name") or meta.get("name") or path.stem
        file_id = payload.get("fileId") or meta.get("id") or ""
        return SourceDoc(str(name), str(file_id), str(text))
    return SourceDoc(path.stem, "", raw)


def iter_input_files(paths: Iterable[str]) -> Iterable[Path]:
    for item in paths:
        path = Path(item)
        if path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.suffix.lower() in {".txt", ".md", ".json"}:
                    yield child
        else:
            yield path


def add_candidate(candidates: dict[str, Candidate], name: str, cue: str, source: SourceDoc) -> None:
    display = title_name(name)
    if len(display) < 2 or len(display) > 64:
        return
    speaker_id = normalize_id(display)
    if speaker_id in IGNORE_IDS:
        return
    if speaker_id in candidates:
        candidates[speaker_id].count += 1
        return
    candidates[speaker_id] = Candidate(display, speaker_id, cue, source.name)


def scan_doc(source: SourceDoc) -> dict[str, Candidate]:
    candidates: dict[str, Candidate] = {}
    for match in re.finditer(r"(?i)\[(?:speaker|voice):([^\]]+)\]", source.text):
        add_candidate(candidates, match.group(1), "tag", source)
    heading = re.compile(r"^\s*([A-Z][A-Z0-9 .'’\-]{1,48})\s*:\s*(?:\S.*)?$")
    for line in source.text.splitlines():
        match = heading.match(line)
        if match:
            add_candidate(candidates, match.group(1), "speaker-heading", source)
    return candidates


def fetch_voice_catalog(gateway: str, limit: int) -> tuple[list[dict], str]:
    url = gateway.rstrip("/") + f"/ttsVoices?limit={limit}"
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8", "replace"))
    except Exception as exc:
        return [], f"voice catalog unavailable: {exc}"
    voices = payload.get("voices") or []
    return [voice for voice in voices if isinstance(voice, dict)], ""


def choose_voice(candidate: Candidate, voices: list[dict]) -> str:
    hinted = VOICE_HINTS.get(candidate.speaker_id, "")
    if hinted:
        return hinted
    if not voices:
        return DEFAULT_NARRATOR
    usable = [voice for voice in voices if voice.get("name") and "Cartesia" not in voice.get("name", "")]
    if not usable:
        usable = voices
    digest = hashlib.sha256(candidate.speaker_id.encode("utf-8")).hexdigest()
    index = int(digest[:8], 16) % len(usable)
    return usable[index].get("name", DEFAULT_NARRATOR)


def parse_existing_ids(registry_text: str) -> set[str]:
    ids = set()
    for line in registry_text.splitlines():
        if not line.startswith("|") or "| Character |" in line or re.match(r"^\|[\s:-]+\|", line):
            continue
        cells = [cell.strip() for cell in line.split("|")]
        if len(cells) > 1:
            ids.add(normalize_id(cells[1]))
    return ids


def row(candidate: Candidate, voices: list[dict]) -> str:
    voice = choose_voice(candidate, voices)
    role = ROLE_HINTS.get(candidate.speaker_id, "dialogue")
    tags = f"[voice:{candidate.speaker_id}], [speaker:{candidate.name}], {candidate.name.upper()}:"
    note = f"auto starter from {candidate.source_name} via {candidate.cue}; count={candidate.count}; overrideable in app"
    return f"| {candidate.name} | {candidate.name} | {voice} | {role} | yes | {tags} | {DEFAULT_ACOUSTIC} | {note} |"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+", help="Files or directories containing exported doc text/json")
    ap.add_argument("--registry", default="app/src/main/assets/home_drive_character_voice_registry.md")
    ap.add_argument("--output", default="generated/home_drive_voice_profiles/scanned_starter_profiles.md")
    ap.add_argument("--merge", action="store_true", help="Append missing rows to --registry as well as writing --output")
    ap.add_argument("--gateway", default=DEFAULT_GATEWAY)
    ap.add_argument("--voice-limit", type=int, default=80)
    args = ap.parse_args()

    all_candidates: dict[str, Candidate] = {}
    scanned = 0
    for path in iter_input_files(args.inputs):
        doc = load_doc(path)
        scanned += 1
        for speaker_id, candidate in scan_doc(doc).items():
            if speaker_id in all_candidates:
                all_candidates[speaker_id].count += candidate.count
            else:
                all_candidates[speaker_id] = candidate

    registry_path = Path(args.registry)
    registry_text = registry_path.read_text(encoding="utf-8") if registry_path.exists() else ""
    existing = parse_existing_ids(registry_text)
    voices, voice_warning = fetch_voice_catalog(args.gateway, args.voice_limit)
    new_candidates = [c for sid, c in sorted(all_candidates.items()) if sid not in existing]
    rows = [row(candidate, voices) for candidate in new_candidates]

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    body = [
        "# Home Drive Scanned Starter Profiles",
        "",
        f"Scanned docs: {scanned}",
        f"Structured candidates: {len(all_candidates)}",
        f"New rows: {len(rows)}",
        f"Voice catalog warning: {voice_warning}" if voice_warning else "Voice catalog warning: none",
        "",
        "| Character | Aliases | Voice Alias | Narration Role | Always Applies | Match Tags | Acoustic Direction | Notes |",
        "|---|---|---|---|---|---|---|---|",
        *rows,
        "",
    ]
    output.write_text("\n".join(body), encoding="utf-8")

    if args.merge and rows:
        merged = registry_text.rstrip() + "\n" + "\n".join(rows) + "\n"
        registry_path.write_text(merged, encoding="utf-8")

    print(json.dumps({"ok": True, "scannedDocs": scanned, "structuredCandidates": len(all_candidates), "newRows": len(rows), "output": str(output), "merged": bool(args.merge and rows), "voiceCatalogWarning": voice_warning}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
