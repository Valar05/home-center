#!/usr/bin/env python3
"""Compact, source-backed retrieval for the ASCII Kinesis V2 specimen corpus.

Raw/rendered specimens remain authoritative. This tool indexes only deterministic
facts and semantic strings already authored in committed manifest/motion JSON.
It never loads raw ASCII/video bodies into the compact index.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

CORPUS_SCHEMA = "ascii-kinesis.motion-corpus.v1"
RECORD_SCHEMA = "ascii-kinesis.motion-source-ref.v1"
MANIFEST_SCHEMA = "ascii-kinesis.swarm-manifest.v2"
DEFAULT_SOURCE = Path("experiments/ascii-kinesis")
DEFAULT_OUT = Path("generated/ascii-kinesis-corpus")


class CorpusError(RuntimeError):
    pass


def read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CorpusError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CorpusError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CorpusError(f"expected JSON object: {path}")
    return value


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def number(value: Any) -> int | float | None:
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def uniq(values: Iterable[str | None]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out


def first_text(*values: Any) -> str | None:
    for value in values:
        found = text(value)
        if found:
            return found
    return None


def rows(motion: dict[str, Any]) -> list[dict[str, Any]]:
    for field in ("keys", "keyframes", "semantic_keys", "poses"):
        value = motion.get(field)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def events(motion: dict[str, Any]) -> list[dict[str, Any]]:
    value = motion.get("events")
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def row_strings(items: Iterable[dict[str, Any]], fields: tuple[str, ...]) -> list[str]:
    found: list[str] = []
    for item in items:
        found.append(first_text(*(item.get(field) for field in fields)))
    return uniq(found)


def support_states(key_rows: Iterable[dict[str, Any]]) -> list[str]:
    found: list[str] = []
    for row in key_rows:
        direct = row.get("support")
        if isinstance(direct, str):
            found.append(f"support:{direct}")
        elif isinstance(direct, list):
            found.extend(f"support:{v}" for v in direct if isinstance(v, str))
        elif isinstance(direct, dict):
            found.extend(
                f"support.{k}:{v}"
                for k, v in sorted(direct.items())
                if isinstance(v, (str, int, float, bool))
            )
        # Modern V2 multi-body rigs often put support under actor blocks A/B.
        for key, value in sorted(row.items()):
            if not isinstance(value, dict):
                continue
            nested = value.get("support")
            if isinstance(nested, str) and nested:
                found.append(f"{key}:{nested}")
    return uniq(found)


def contact_points(key_rows: Iterable[dict[str, Any]]) -> list[str]:
    found: list[str] = []
    for row in key_rows:
        value = row.get("contact_points")
        if isinstance(value, str):
            found.append(value)
        elif isinstance(value, list):
            found.extend(str(item) for item in value if isinstance(item, str))
    return uniq(found)


def duration_seconds(
    key_rows: list[dict[str, Any]], motion: dict[str, Any]
) -> int | float | None:
    compile_block = motion.get("compile")
    if isinstance(compile_block, dict):
        duration = number(compile_block.get("duration_seconds"))
        if duration is not None:
            return duration
    times: list[float] = []
    for row in key_rows:
        for field in ("t", "time", "time_seconds", "seconds"):
            value = number(row.get(field))
            if value is not None:
                times.append(float(value))
                break
    return round(max(times) - min(times), 6) if len(times) >= 2 else None


def fps(manifest: dict[str, Any], motion: dict[str, Any]) -> int | float | None:
    for block in (
        motion,
        motion.get("compile"),
        manifest,
        manifest.get("motion_dungeon"),
    ):
        if isinstance(block, dict):
            value = number(block.get("fps"))
            if value is not None:
                return value
    timing_policy = motion.get("timing_policy")
    if isinstance(timing_policy, dict):
        value = number(timing_policy.get("nominal_fps"))
        if value is not None:
            return value
    return None


def candidate_role(manifest: dict[str, Any], motion: dict[str, Any]) -> str | None:
    candidate = manifest.get("candidate")
    return first_text(
        candidate.get("role") if isinstance(candidate, dict) else None,
        manifest.get("candidate_role"),
        manifest.get("role"),
        motion.get("candidate_role"),
        motion.get("role"),
        motion.get("source_role"),
    )


def motion_name(manifest: dict[str, Any], motion: dict[str, Any]) -> str | None:
    return first_text(
        motion.get("motion_name"),
        motion.get("title"),
        motion.get("name"),
        manifest.get("motion_name"),
        manifest.get("title"),
    )


def quality_gates(manifest: dict[str, Any]) -> dict[str, str]:
    raw = manifest.get("quality_gates")
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for name, value in raw.items():
        status = text(value.get("status")) if isinstance(value, dict) else text(value)
        if status:
            out[str(name)] = status
    return out


def source_summary(manifest: dict[str, Any], motion: dict[str, Any]) -> dict[str, Any]:
    raw = manifest.get("source")
    if not isinstance(raw, dict):
        raw = motion.get("source")
    if not isinstance(raw, dict):
        return {}
    keep = (
        "provider",
        "site",
        "asset_id",
        "title",
        "identity",
        "url",
        "source_timing",
        "source_authentic_timing",
        "timing_authority",
        "authored_timing_provenance",
        "rights_boundary",
        "rights_note",
        "evidence_document_id",
        "evidence_title",
        "raw_sha256",
    )
    out = {key: raw[key] for key in keep if key in raw}
    for field in ("source_roles", "exact_archive", "rights_firewall"):
        if field in raw:
            out[field] = raw[field]
    return out


def artifact_paths(
    manifest_path: Path, manifest: dict[str, Any], repo_root: Path
) -> list[str]:
    ignored = {"manifest.json", "motion.json", "receipt.json", "build.py"}
    names = manifest.get("files")
    candidates: list[Path]
    if isinstance(names, list):
        candidates = [
            manifest_path.parent / name for name in names if isinstance(name, str)
        ]
    else:
        candidates = sorted(p for p in manifest_path.parent.iterdir() if p.is_file())
    return [
        p.relative_to(repo_root).as_posix()
        for p in candidates
        if p.exists() and p.is_file() and p.name not in ignored
    ]


def authored_terms(
    manifest: dict[str, Any],
    motion: dict[str, Any],
    key_rows: list[dict[str, Any]],
    event_rows: list[dict[str, Any]],
) -> dict[str, list[str]]:
    return {
        "primitive": uniq(
            [
                text(motion.get("primitive")),
                text(manifest.get("primitive")),
                candidate_role(manifest, motion),
                motion_name(manifest, motion),
                text(motion.get("source_role")),
            ]
        ),
        "key_ids": row_strings(key_rows, ("key_id", "id", "key")),
        "key_names": row_strings(key_rows, ("name", "label", "pose", "key")),
        "causal_roles": row_strings(key_rows, ("causal_role",)),
        "contact_states": row_strings(key_rows, ("contact_state",)),
        "contact_points": contact_points(key_rows),
        "support_contacts": row_strings(key_rows, ("support_contact",)),
        "support_states": support_states(key_rows),
        "root_owners": row_strings(key_rows, ("root_owner",)),
        "root_velocity_classes": row_strings(key_rows, ("root_velocity_class",)),
        "actuator_states": row_strings(key_rows, ("actuator_state",)),
        "authority_states": row_strings(key_rows, ("authority",)),
        "timing_classes": row_strings(key_rows, ("timing_class", "timing")),
        "timing_provenance": row_strings(
            key_rows, ("timing_provenance", "provenance")
        ),
        "force_labels": row_strings(key_rows, ("force",)),
        "event_names": row_strings(
            event_rows, ("event", "name", "label", "type", "kind")
        ),
    }


def record_for(manifest_path: Path, repo_root: Path) -> dict[str, Any]:
    manifest = read_object(manifest_path)
    if manifest.get("schema") != MANIFEST_SCHEMA or manifest.get("format_version") != 2:
        raise CorpusError(f"unsupported V2 manifest contract: {manifest_path}")

    experiment_id = text(manifest.get("experiment_id"))
    lane = text(manifest.get("lane"))
    if not experiment_id or not lane:
        raise CorpusError(f"manifest missing experiment_id/lane: {manifest_path}")
    if manifest_path.parent.name != experiment_id:
        raise CorpusError(
            f"experiment_id/path mismatch: {experiment_id!r} != {manifest_path.parent.name!r}"
        )

    motion_path = manifest_path.parent / "motion.json"
    motion = read_object(motion_path)
    key_rows = rows(motion)
    if not key_rows:
        raise CorpusError(f"V2 specimen has no keys/poses: {motion_path}")
    event_rows = events(motion)
    terms = authored_terms(manifest, motion, key_rows, event_rows)

    receipt = manifest_path.parent / "receipt.json"
    specimen = {
        "directory": manifest_path.parent.relative_to(repo_root).as_posix(),
        "manifest_path": manifest_path.relative_to(repo_root).as_posix(),
        "motion_path": motion_path.relative_to(repo_root).as_posix(),
        "receipt_path": (
            receipt.relative_to(repo_root).as_posix() if receipt.exists() else None
        ),
        "artifact_paths": artifact_paths(manifest_path, manifest, repo_root),
        "manifest_sha256": sha256(manifest_path),
        "motion_sha256": sha256(motion_path),
    }

    record: dict[str, Any] = {
        "schema": RECORD_SCHEMA,
        "experiment_id": experiment_id,
        "lane": lane,
        "format_version": 2,
        "candidate_role": candidate_role(manifest, motion),
        "motion_name": motion_name(manifest, motion),
        "fps": fps(manifest, motion),
        "duration_seconds": duration_seconds(key_rows, motion),
        "key_count": len(key_rows),
        "event_count": len(event_rows),
        "authored_terms": terms,
        "quality_gates": quality_gates(manifest),
        "contract_verification": text(manifest.get("contract_verification")),
        "source": source_summary(manifest, motion),
        "specimen": specimen,
        "authority": {
            "specimen_is_authoritative": True,
            "record_is_deterministic_observation": True,
            "generated_inference_allowed": False,
        },
    }
    primitive = terms["primitive"][0] if terms["primitive"] else None
    role = primitive or record["candidate_role"] or record["motion_name"] or "-"
    record["evidence_line"] = (
        f"{experiment_id} | {lane} | {role} | {len(key_rows)} keys | "
        f"{len(event_rows)} events"
        + (f" | {record['fps']} fps" if record["fps"] is not None else "")
    )
    return record


def build_corpus(
    repo_root: Path, source_rel: Path = DEFAULT_SOURCE
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    repo_root = repo_root.resolve()
    source_root = (repo_root / source_rel).resolve()
    if not source_root.exists():
        raise CorpusError(f"source root does not exist: {source_root}")
    try:
        source_root.relative_to(repo_root)
    except ValueError as exc:
        raise CorpusError("source root must stay inside repo root") from exc

    records: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    for manifest_path in sorted(source_root.rglob("manifest.json")):
        try:
            manifest = read_object(manifest_path)
        except CorpusError as exc:
            rejected.append(
                {
                    "path": manifest_path.relative_to(repo_root).as_posix(),
                    "reason": str(exc),
                }
            )
            continue
        if manifest.get("schema") != MANIFEST_SCHEMA:
            continue
        try:
            records.append(record_for(manifest_path, repo_root))
        except CorpusError as exc:
            rejected.append(
                {
                    "path": manifest_path.relative_to(repo_root).as_posix(),
                    "reason": str(exc),
                }
            )
    records.sort(key=lambda row: row["experiment_id"])
    rejected.sort(key=lambda row: row["path"])
    return records, rejected


def summary(
    records: list[dict[str, Any]], rejected: list[dict[str, str]]
) -> dict[str, Any]:
    gates: Counter[str] = Counter()
    for row in records:
        for gate, status in row["quality_gates"].items():
            gates[f"{gate}:{status}"] += 1
    return {
        "schema": CORPUS_SCHEMA,
        "record_count": len(records),
        "rejected_v2_count": len(rejected),
        "lanes": dict(sorted(Counter(row["lane"] for row in records).items())),
        "quality_gate_statuses": dict(sorted(gates.items())),
        "authority_ladder": [
            "raw specimen",
            "deterministic observation record",
            "explicit authored semantic terms",
            "index/report retrieval surfaces",
        ],
        "context_rule": (
            "Retrieval expands resolution. Context never starts at full specimen resolution."
        ),
    }


def json_line(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def report(records: list[dict[str, Any]], rejected: list[dict[str, str]]) -> str:
    info = summary(records, rejected)
    lines = [
        "# ASCII Kinesis Motion Corpus",
        "",
        "Deterministic retrieval surface over authoritative ASCII Kinesis V2 specimens.",
        "This report does not promote, retime, redraw, or replace the underlying motion.",
        "",
        f"Indexed V2 specimens: **{info['record_count']}**",
        f"Rejected malformed V2 specimens: **{info['rejected_v2_count']}**",
        "",
        "## Lanes",
        "",
    ]
    lines.extend(f"- `{lane}`: {count}" for lane, count in info["lanes"].items())
    lines.extend(
        [
            "",
            "## Compact index",
            "",
            "| Experiment | Lane | Primitive / role | Keys | Events | FPS | Source |",
            "| --- | --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for row in records:
        primitive = (row["authored_terms"].get("primitive") or [""])[0]
        role = primitive or row.get("candidate_role") or row.get("motion_name") or ""
        role = str(role).replace("|", "\\|")
        fps_value = "" if row.get("fps") is None else str(row["fps"])
        lines.append(
            f"| `{row['experiment_id']}` | `{row['lane']}` | {role} | "
            f"{row['key_count']} | {row['event_count']} | {fps_value} | "
            f"`{row['specimen']['manifest_path']}` |"
        )
    if rejected:
        lines.extend(["", "## Fail-closed V2 specimens", ""])
        lines.extend(f"- `{row['path']}`: {row['reason']}" for row in rejected)
    lines.extend(
        [
            "",
            "## Retrieval",
            "",
            "```sh",
            "python3 tools/ascii_kinesis_corpus.py search 'landing debt'",
            "python3 tools/ascii_kinesis_corpus.py show v2-airborne-003-apex-spacing-window",
            "```",
            "",
            "Open raw specimen files only when the compact record is insufficient.",
            "",
        ]
    )
    return "\n".join(lines)


def render_outputs(
    records: list[dict[str, Any]], rejected: list[dict[str, str]]
) -> dict[str, str]:
    return {
        "motion_source_refs.jsonl": "".join(json_line(row) + "\n" for row in records),
        "motion_index_summary.json": json.dumps(
            summary(records, rejected), indent=2, sort_keys=True, ensure_ascii=False
        )
        + "\n",
        "motion_index_report.md": report(records, rejected),
        "rejected_v2_records.jsonl": "".join(
            json_line(row) + "\n" for row in rejected
        ),
    }


def write_outputs(out_dir: Path, outputs: dict[str, str]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, content in outputs.items():
        (out_dir / name).write_text(content, encoding="utf-8")


def load_index(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as exc:
        raise CorpusError(f"index not found: {path}") from exc
    out: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CorpusError(f"invalid JSONL at {path}:{line_number}") from exc
        if not isinstance(row, dict) or row.get("schema") != RECORD_SCHEMA:
            raise CorpusError(f"unexpected record at {path}:{line_number}")
        out.append(row)
    return out


def query_records(repo_root: Path, index_arg: str | None) -> list[dict[str, Any]]:
    """Read current specimens by default; use a persisted snapshot only explicitly."""
    if index_arg:
        index = Path(index_arg)
        if not index.is_absolute():
            index = repo_root / index
        return load_index(index)
    records, _ = build_corpus(repo_root)
    return records


def haystack(row: dict[str, Any]) -> str:
    values: list[str] = [
        str(row.get("experiment_id") or ""),
        str(row.get("lane") or ""),
        str(row.get("candidate_role") or ""),
        str(row.get("motion_name") or ""),
        str(row.get("evidence_line") or ""),
    ]
    for group in row.get("authored_terms", {}).values():
        if isinstance(group, list):
            values.extend(str(item) for item in group)
    for value in row.get("source", {}).values():
        if isinstance(value, (str, int, float, bool)):
            values.append(str(value))
    return "\n".join(values).lower()


def search_records(
    records: list[dict[str, Any]], query: str, lane: str | None = None
) -> list[tuple[int, dict[str, Any]]]:
    tokens = re.findall(r"[a-z0-9_+-]+", query.lower())
    phrase = query.strip().lower()
    ranked: list[tuple[int, dict[str, Any]]] = []
    for row in records:
        if lane and row.get("lane") != lane:
            continue
        blob = haystack(row)
        if tokens and not all(token in blob for token in tokens):
            continue
        score = sum(blob.count(token) for token in tokens) + (
            10 if phrase in blob else 0
        )
        ranked.append((score, row))
    return sorted(ranked, key=lambda pair: (-pair[0], pair[1]["experiment_id"]))


def compact(row: dict[str, Any]) -> str:
    primitive = (row.get("authored_terms", {}).get("primitive") or ["-"])[0]
    return (
        f"{row['experiment_id']} | {row['lane']} | {primitive} | "
        f"{row['key_count']} keys | {row['event_count']} events | "
        f"{row['specimen']['manifest_path']}"
    )


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def cmd_build(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    records, rejected = build_corpus(repo_root, Path(args.source_root))
    if rejected and args.fail_on_rejected:
        for item in rejected:
            print(f"REJECT {item['path']}: {item['reason']}", file=sys.stderr)
        return 2
    out = Path(args.out_dir)
    if not out.is_absolute():
        out = repo_root / out
    write_outputs(out, render_outputs(records, rejected))
    print(f"indexed={len(records)} rejected={len(rejected)} out={out}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    records, rejected = build_corpus(repo_root, Path(args.source_root))
    out = Path(args.out_dir)
    if not out.is_absolute():
        out = repo_root / out
    expected = render_outputs(records, rejected)
    stale = [
        name
        for name, content in expected.items()
        if not (out / name).exists()
        or (out / name).read_text(encoding="utf-8") != content
    ]
    if stale:
        print("STALE " + " ".join(stale), file=sys.stderr)
        return 1
    print(f"verified={len(records)} rejected={len(rejected)}")
    return 0


def cmd_inventory(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    records, rejected = build_corpus(repo_root, Path(args.source_root))
    print(json.dumps(summary(records, rejected), indent=2, sort_keys=True))
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    ranked = search_records(query_records(repo_root, args.index), args.query, args.lane)
    for score, row in ranked[: args.limit]:
        print(json_line({"score": score, **row}) if args.json else compact(row))
    return 0 if ranked else 1


def cmd_show(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    for row in query_records(repo_root, args.index):
        if row["experiment_id"] != args.experiment_id:
            continue
        if args.json:
            print(json.dumps(row, indent=2, sort_keys=True, ensure_ascii=False))
        else:
            print(compact(row))
            print(f"evidence: {row['evidence_line']}")
            print(f"motion: {row['specimen']['motion_path']}")
            print(f"receipt: {row['specimen'].get('receipt_path') or '-'}")
            terms = row.get("authored_terms", {})
            for key in (
                "key_names",
                "causal_roles",
                "contact_states",
                "contact_points",
                "support_contacts",
                "support_states",
                "root_owners",
                "root_velocity_classes",
                "actuator_states",
                "timing_classes",
            ):
                if terms.get(key):
                    print(f"{key}: " + ", ".join(terms[key]))
        return 0
    print(f"not found: {args.experiment_id}", file=sys.stderr)
    return 1


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root", default=str(repo_root_from_script()))
    sub = p.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build")
    build.add_argument("--source-root", default=str(DEFAULT_SOURCE))
    build.add_argument("--out-dir", default=str(DEFAULT_OUT))
    build.add_argument("--fail-on-rejected", action="store_true")
    build.set_defaults(func=cmd_build)

    verify = sub.add_parser("verify")
    verify.add_argument("--source-root", default=str(DEFAULT_SOURCE))
    verify.add_argument("--out-dir", default=str(DEFAULT_OUT))
    verify.set_defaults(func=cmd_verify)

    inventory = sub.add_parser("inventory")
    inventory.add_argument("--source-root", default=str(DEFAULT_SOURCE))
    inventory.set_defaults(func=cmd_inventory)

    search = sub.add_parser("search")
    search.add_argument("query")
    search.add_argument("--index")
    search.add_argument("--lane")
    search.add_argument("--limit", type=int, default=12)
    search.add_argument("--json", action="store_true")
    search.set_defaults(func=cmd_search)

    show = sub.add_parser("show")
    show.add_argument("experiment_id")
    show.add_argument("--index")
    show.add_argument("--json", action="store_true")
    show.set_defaults(func=cmd_show)
    return p


def main(argv: list[str] | None = None) -> int:
    try:
        args = parser().parse_args(argv)
        return int(args.func(args))
    except CorpusError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
