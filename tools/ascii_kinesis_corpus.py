#!/usr/bin/env python3
"""Build and query a compact, source-backed ASCII Kinesis motion corpus.

The corpus intentionally keeps rendered specimens authoritative. It indexes only
small deterministic observations and explicit authored metadata so agents can
retrieve a few records without loading full ASCII animations into context.
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

SCHEMA = "ascii-kinesis.motion-corpus.v1"
RECORD_SCHEMA = "ascii-kinesis.motion-source-ref.v1"
MANIFEST_SCHEMA = "ascii-kinesis.swarm-manifest.v2"
DEFAULT_SOURCE = Path("experiments/ascii-kinesis")
DEFAULT_OUT = Path("generated/ascii-kinesis-corpus")


class CorpusError(RuntimeError):
    pass


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CorpusError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CorpusError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CorpusError(f"expected JSON object: {path}")
    return value


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _string(value: Any) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _number(value: Any) -> int | float | None:
    if isinstance(value, bool):
        return None
    return value if isinstance(value, (int, float)) else None


def _list_of_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [v for v in value if isinstance(v, str) and v.strip()]


def _explicit_role(manifest: dict[str, Any], motion: dict[str, Any]) -> str | None:
    candidate = manifest.get("candidate")
    if isinstance(candidate, dict):
        role = _string(candidate.get("role"))
        if role:
            return role
    for field in ("candidate_role", "role", "source_role"):
        role = _string(manifest.get(field))
        if role:
            return role
    for field in ("candidate_role", "role", "source_role"):
        role = _string(motion.get(field))
        if role:
            return role
    return None


def _explicit_motion_name(manifest: dict[str, Any], motion: dict[str, Any]) -> str | None:
    for field in ("motion_name", "title", "name"):
        value = _string(motion.get(field))
        if value:
            return value
    for field in ("motion_name", "title"):
        value = _string(manifest.get(field))
        if value:
            return value
    return None


def _fps(manifest: dict[str, Any], motion: dict[str, Any]) -> int | float | None:
    for source in (motion, manifest):
        value = _number(source.get("fps"))
        if value is not None:
            return value
    md = manifest.get("motion_dungeon")
    if isinstance(md, dict):
        value = _number(md.get("fps"))
        if value is not None:
            return value
    compile_block = motion.get("compile")
    if isinstance(compile_block, dict):
        value = _number(compile_block.get("fps"))
        if value is not None:
            return value
    return None


def _key_rows(motion: dict[str, Any]) -> list[dict[str, Any]]:
    for field in ("keys", "keyframes", "semantic_keys", "poses"):
        value = motion.get(field)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]
    return []


def _key_names(rows: Iterable[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for row in rows:
        for field in ("key", "name", "label", "id", "pose"):
            value = _string(row.get(field))
            if value:
                names.append(value)
                break
    return names


def _event_rows(motion: dict[str, Any]) -> list[dict[str, Any]]:
    value = motion.get("events")
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _event_names(rows: Iterable[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for row in rows:
        for field in ("event", "name", "label", "type", "kind"):
            value = _string(row.get(field))
            if value:
                names.append(value)
                break
    return names


def _support_states(rows: Iterable[dict[str, Any]]) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for row in rows:
        support = row.get("support")
        if isinstance(support, str):
            candidates = [support]
        elif isinstance(support, list):
            candidates = [item for item in support if isinstance(item, str)]
        elif isinstance(support, dict):
            candidates = [
                f"{key}:{value}"
                for key, value in sorted(support.items())
                if isinstance(value, (str, int, float, bool))
            ]
        else:
            candidates = []
        for item in candidates:
            if item and item not in seen:
                seen.add(item)
                values.append(item)
    return values


def _duration(rows: list[dict[str, Any]]) -> int | float | None:
    times: list[float] = []
    for row in rows:
        for field in ("t", "time", "time_seconds", "seconds"):
            value = _number(row.get(field))
            if value is not None:
                times.append(float(value))
                break
    if len(times) < 2:
        return None
    return round(max(times) - min(times), 6)


def _explicit_terms(
    manifest: dict[str, Any],
    motion: dict[str, Any],
    key_names: list[str],
    event_names: list[str],
) -> list[str]:
    terms: list[str] = []
    candidates: list[Any] = [
        manifest.get("lane"),
        _explicit_role(manifest, motion),
        _explicit_motion_name(manifest, motion),
        motion.get("source_role"),
        manifest.get("contract_verification"),
    ]
    candidates.extend(key_names)
    candidates.extend(event_names)
    for value in candidates:
        if isinstance(value, str):
            clean = value.strip()
            if clean and clean not in terms:
                terms.append(clean)
    return terms


def _quality_gates(manifest: dict[str, Any]) -> dict[str, str]:
    raw = manifest.get("quality_gates")
    if not isinstance(raw, dict):
        return {}
    result: dict[str, str] = {}
    for key, value in raw.items():
        if isinstance(value, dict):
            status = _string(value.get("status"))
            if status:
                result[str(key)] = status
        elif isinstance(value, str):
            result[str(key)] = value
    return result


def _source_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    raw = manifest.get("source")
    if not isinstance(raw, dict):
        return {}
    keep = (
        "provider",
        "asset_id",
        "title",
        "url",
        "source_timing",
        "authored_timing_provenance",
        "rights_boundary",
    )
    result = {key: raw[key] for key in keep if key in raw}
    exact = raw.get("exact_archive")
    if isinstance(exact, dict):
        result["exact_archive"] = exact
    return result


def _evidence_line(record: dict[str, Any]) -> str:
    pieces = [record["experiment_id"], record["lane"]]
    if record.get("candidate_role"):
        pieces.append(str(record["candidate_role"]))
    if record.get("motion_name"):
        pieces.append(str(record["motion_name"]))
    pieces.append(f"{record['key_count']} keys")
    pieces.append(f"{record['event_count']} events")
    if record.get("fps") is not None:
        pieces.append(f"{record['fps']} fps")
    return " | ".join(pieces)


def _record_for(manifest_path: Path, repo_root: Path) -> dict[str, Any]:
    manifest = _json(manifest_path)
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise CorpusError(
            f"unsupported manifest schema at {manifest_path}: {manifest.get('schema')!r}"
        )
    if manifest.get("format_version") != 2:
        raise CorpusError(f"unsupported format_version at {manifest_path}")
    experiment_id = _string(manifest.get("experiment_id"))
    lane = _string(manifest.get("lane"))
    if not experiment_id or not lane:
        raise CorpusError(f"manifest missing experiment_id/lane: {manifest_path}")
    if manifest_path.parent.name != experiment_id:
        raise CorpusError(
            f"experiment_id/path mismatch: {experiment_id!r} != {manifest_path.parent.name!r}"
        )

    motion_path = manifest_path.parent / "motion.json"
    if not motion_path.exists():
        raise CorpusError(f"V2 specimen missing motion.json: {manifest_path.parent}")
    motion = _json(motion_path)
    rows = _key_rows(motion)
    events = _event_rows(motion)
    key_names = _key_names(rows)
    event_names = _event_names(events)

    rel_dir = manifest_path.parent.relative_to(repo_root).as_posix()
    rel_manifest = manifest_path.relative_to(repo_root).as_posix()
    rel_motion = motion_path.relative_to(repo_root).as_posix()
    files = _list_of_strings(manifest.get("files"))

    receipt_path = manifest_path.parent / "receipt.json"
    receipt_rel = (
        receipt_path.relative_to(repo_root).as_posix() if receipt_path.exists() else None
    )

    artifacts: list[str] = []
    for name in files:
        candidate = manifest_path.parent / name
        if candidate.exists():
            artifacts.append(candidate.relative_to(repo_root).as_posix())
    if not artifacts:
        for candidate in sorted(manifest_path.parent.iterdir()):
            if candidate.is_file() and candidate.name not in {
                "manifest.json",
                "motion.json",
                "receipt.json",
                "build.py",
            }:
                artifacts.append(candidate.relative_to(repo_root).as_posix())

    record: dict[str, Any] = {
        "schema": RECORD_SCHEMA,
        "experiment_id": experiment_id,
        "lane": lane,
        "format_version": 2,
        "candidate_role": _explicit_role(manifest, motion),
        "motion_name": _explicit_motion_name(manifest, motion),
        "fps": _fps(manifest, motion),
        "key_count": len(rows),
        "key_names": key_names,
        "event_count": len(events),
        "event_names": event_names,
        "support_states": _support_states(rows),
        "duration_seconds": _duration(rows),
        "quality_gates": _quality_gates(manifest),
        "contract_verification": _string(manifest.get("contract_verification")),
        "source": _source_summary(manifest),
        "abstraction_terms": _explicit_terms(manifest, motion, key_names, event_names),
        "specimen": {
            "directory": rel_dir,
            "manifest_path": rel_manifest,
            "motion_path": rel_motion,
            "receipt_path": receipt_rel,
            "artifact_paths": artifacts,
            "manifest_sha256": _sha256(manifest_path),
            "motion_sha256": _sha256(motion_path),
        },
        "authority": {
            "specimen_is_authoritative": True,
            "record_is_observation": True,
            "generated_inference_allowed": False,
        },
    }
    record["evidence_line"] = _evidence_line(record)
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
    skipped: list[dict[str, str]] = []
    for manifest_path in sorted(source_root.rglob("manifest.json")):
        try:
            manifest = _json(manifest_path)
        except CorpusError as exc:
            skipped.append(
                {
                    "path": manifest_path.relative_to(repo_root).as_posix(),
                    "reason": str(exc),
                }
            )
            continue
        if manifest.get("schema") != MANIFEST_SCHEMA:
            continue
        try:
            records.append(_record_for(manifest_path, repo_root))
        except CorpusError as exc:
            skipped.append(
                {
                    "path": manifest_path.relative_to(repo_root).as_posix(),
                    "reason": str(exc),
                }
            )
    records.sort(key=lambda row: row["experiment_id"])
    skipped.sort(key=lambda row: row["path"])
    return records, skipped


def _json_line(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _render_summary(
    records: list[dict[str, Any]], skipped: list[dict[str, str]]
) -> dict[str, Any]:
    lanes = Counter(str(row["lane"]) for row in records)
    contract = Counter(
        str(row.get("contract_verification") or "UNSPECIFIED") for row in records
    )
    gate_counts: Counter[str] = Counter()
    for row in records:
        for gate, status in row.get("quality_gates", {}).items():
            gate_counts[f"{gate}:{status}"] += 1
    return {
        "schema": SCHEMA,
        "record_count": len(records),
        "skipped_v2_count": len(skipped),
        "lanes": dict(sorted(lanes.items())),
        "contract_verification": dict(sorted(contract.items())),
        "quality_gate_statuses": dict(sorted(gate_counts.items())),
        "authority_ladder": [
            "raw specimen",
            "deterministic observation record",
            "explicit authored abstraction terms",
            "index/report retrieval surfaces",
        ],
        "context_rule": "Retrieval expands resolution. Context never starts at full specimen resolution.",
    }


def _render_report(
    records: list[dict[str, Any]], skipped: list[dict[str, str]]
) -> str:
    summary = _render_summary(records, skipped)
    lines = [
        "# ASCII Kinesis Motion Corpus",
        "",
        "This is a deterministic retrieval surface over authoritative ASCII Kinesis V2 specimens.",
        "It does not replace, promote, retime, redraw, or reinterpret the underlying animation.",
        "",
        "## Authority",
        "",
        "1. Raw specimen and rendered artifact.",
        "2. Deterministic observation record derived from committed JSON.",
        "3. Explicit authored abstraction terms already present in the specimen metadata.",
        "4. This index/report.",
        "",
        f"Indexed V2 specimens: **{summary['record_count']}**",
        f"Rejected malformed V2 manifests: **{summary['skipped_v2_count']}**",
        "",
        "## Lanes",
        "",
    ]
    for lane, count in summary["lanes"].items():
        lines.append(f"- `{lane}`: {count}")
    lines.extend(
        [
            "",
            "## Compact index",
            "",
            "| Experiment | Lane | Role / motion | Keys | Events | FPS | Source |",
            "| --- | --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for row in records:
        role = row.get("candidate_role") or row.get("motion_name") or ""
        if (
            row.get("candidate_role")
            and row.get("motion_name")
            and row["candidate_role"] != row["motion_name"]
        ):
            role = f"{row['candidate_role']} / {row['motion_name']}"
        role = str(role).replace("|", "\\|")
        source = row["specimen"]["manifest_path"].replace("|", "%7C")
        fps = "" if row.get("fps") is None else str(row["fps"])
        lines.append(
            f"| `{row['experiment_id']}` | `{row['lane']}` | {role} | "
            f"{row['key_count']} | {row['event_count']} | {fps} | `{source}` |"
        )
    if skipped:
        lines.extend(["", "## Fail-closed V2 records", ""])
        for item in skipped:
            lines.append(f"- `{item['path']}`: {item['reason']}")
    lines.extend(
        [
            "",
            "## Query without loading the specimens",
            "",
            "```sh",
            "python3 tools/ascii_kinesis_corpus.py search 'landing debt'",
            "python3 tools/ascii_kinesis_corpus.py show v2-airborne-003-apex-spacing-window",
            "```",
            "",
            "Only use `show` or open the source paths when a compact record is insufficient.",
            "",
        ]
    )
    return "\n".join(lines)


def render_outputs(
    records: list[dict[str, Any]], skipped: list[dict[str, str]]
) -> dict[str, str]:
    refs = "".join(_json_line(row) + "\n" for row in records)
    rejected = "".join(_json_line(row) + "\n" for row in skipped)
    summary = (
        json.dumps(
            _render_summary(records, skipped),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n"
    )
    report = _render_report(records, skipped)
    return {
        "motion_source_refs.jsonl": refs,
        "motion_index_summary.json": summary,
        "motion_index_report.md": report,
        "rejected_v2_records.jsonl": rejected,
    }


def write_outputs(out_dir: Path, outputs: dict[str, str]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, content in outputs.items():
        (out_dir / name).write_text(content, encoding="utf-8")


def load_index(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as exc:
        raise CorpusError(
            f"index not found: {path}; run `python3 tools/ascii_kinesis_corpus.py build`"
        ) from exc
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CorpusError(f"invalid JSONL at {path}:{number}") from exc
        if not isinstance(row, dict) or row.get("schema") != RECORD_SCHEMA:
            raise CorpusError(f"unexpected record at {path}:{number}")
        records.append(row)
    return records


def _haystack(row: dict[str, Any]) -> str:
    fields: list[str] = [
        str(row.get("experiment_id") or ""),
        str(row.get("lane") or ""),
        str(row.get("candidate_role") or ""),
        str(row.get("motion_name") or ""),
        str(row.get("evidence_line") or ""),
        " ".join(str(x) for x in row.get("abstraction_terms", [])),
        " ".join(str(x) for x in row.get("key_names", [])),
        " ".join(str(x) for x in row.get("event_names", [])),
        " ".join(str(x) for x in row.get("support_states", [])),
    ]
    source = row.get("source")
    if isinstance(source, dict):
        fields.extend(
            str(v) for v in source.values() if isinstance(v, (str, int, float))
        )
    return "\n".join(fields).lower()


def search_records(
    records: list[dict[str, Any]], query: str, lane: str | None = None
) -> list[tuple[int, dict[str, Any]]]:
    tokens = [token for token in re.findall(r"[a-z0-9_+-]+", query.lower()) if token]
    phrase = query.strip().lower()
    ranked: list[tuple[int, dict[str, Any]]] = []
    for row in records:
        if lane and row.get("lane") != lane:
            continue
        hay = _haystack(row)
        if tokens and not all(token in hay for token in tokens):
            continue
        score = sum(hay.count(token) for token in tokens)
        if phrase and phrase in hay:
            score += 10
        ranked.append((score, row))
    ranked.sort(key=lambda pair: (-pair[0], pair[1]["experiment_id"]))
    return ranked


def _compact(row: dict[str, Any]) -> str:
    role = row.get("candidate_role") or row.get("motion_name") or "-"
    return (
        f"{row['experiment_id']} | {row['lane']} | {role} | "
        f"{row['key_count']} keys | {row['event_count']} events | "
        f"{row['specimen']['manifest_path']}"
    )


def _repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def _default_index(repo_root: Path) -> Path:
    return repo_root / DEFAULT_OUT / "motion_source_refs.jsonl"


def cmd_build(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    source = Path(args.source_root)
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = repo_root / out_dir
    records, skipped = build_corpus(repo_root, source)
    if skipped and args.fail_on_rejected:
        for item in skipped:
            print(f"REJECT {item['path']}: {item['reason']}", file=sys.stderr)
        return 2
    write_outputs(out_dir, render_outputs(records, skipped))
    print(f"indexed={len(records)} rejected={len(skipped)} out={out_dir}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = repo_root / out_dir
    records, skipped = build_corpus(repo_root, Path(args.source_root))
    expected = render_outputs(records, skipped)
    stale: list[str] = []
    for name, content in expected.items():
        path = out_dir / name
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            stale.append(name)
    if stale:
        print("STALE " + " ".join(stale), file=sys.stderr)
        return 1
    print(f"verified={len(records)} rejected={len(skipped)}")
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    index = Path(args.index) if args.index else _default_index(repo_root)
    if not index.is_absolute():
        index = repo_root / index
    ranked = search_records(load_index(index), args.query, args.lane)
    for score, row in ranked[: args.limit]:
        if args.json:
            print(_json_line({"score": score, **row}))
        else:
            print(_compact(row))
    return 0 if ranked else 1


def cmd_show(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    index = Path(args.index) if args.index else _default_index(repo_root)
    if not index.is_absolute():
        index = repo_root / index
    for row in load_index(index):
        if row["experiment_id"] == args.experiment_id:
            if args.json:
                print(json.dumps(row, indent=2, sort_keys=True, ensure_ascii=False))
            else:
                print(_compact(row))
                print(f"evidence: {row['evidence_line']}")
                print(f"motion: {row['specimen']['motion_path']}")
                print(f"receipt: {row['specimen'].get('receipt_path') or '-'}")
                if row.get("abstraction_terms"):
                    print("terms: " + ", ".join(row["abstraction_terms"]))
            return 0
    print(f"not found: {args.experiment_id}", file=sys.stderr)
    return 1


def parser() -> argparse.ArgumentParser:
    repo_root = _repo_root_from_script()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root", default=str(repo_root))
    sub = p.add_subparsers(dest="command", required=True)

    build = sub.add_parser(
        "build", help="rebuild compact corpus outputs from committed V2 specimens"
    )
    build.add_argument("--source-root", default=str(DEFAULT_SOURCE))
    build.add_argument("--out-dir", default=str(DEFAULT_OUT))
    build.add_argument("--fail-on-rejected", action="store_true")
    build.set_defaults(func=cmd_build)

    verify = sub.add_parser("verify", help="fail if committed corpus outputs are stale")
    verify.add_argument("--source-root", default=str(DEFAULT_SOURCE))
    verify.add_argument("--out-dir", default=str(DEFAULT_OUT))
    verify.set_defaults(func=cmd_verify)

    search = sub.add_parser(
        "search", help="search compact records without opening full specimens"
    )
    search.add_argument("query")
    search.add_argument("--index")
    search.add_argument("--lane")
    search.add_argument("--limit", type=int, default=12)
    search.add_argument("--json", action="store_true")
    search.set_defaults(func=cmd_search)

    show = sub.add_parser(
        "show", help="show one compact record and its specimen pointers"
    )
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
