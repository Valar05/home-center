#!/usr/bin/env python3
"""One-command runtime proof for the ASCII Kinesis compact corpus.

This command is intentionally stricter than ordinary retrieval. It binds evidence
to one clean Git commit, scans the current V2 corpus, runs both the compact-corpus
regression contract and the existing V2 swarm contract, and emits a small JSON
receipt. The receipt proves mechanical retrieval behavior only; it does not claim
artistic acceptance, deployment, or Drew's acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

import ascii_kinesis_corpus as corpus

SCHEMA = "ascii-kinesis.motion-corpus-proof.v1"


def sha_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def run(command: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        command,
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def git(root: Path, *args: str) -> str:
    result = run(["git", "-C", str(root), *args], root)
    if result.returncode != 0:
        raise corpus.CorpusError(
            f"git {' '.join(args)} failed: {result.stderr.strip() or result.stdout.strip()}"
        )
    return result.stdout.strip()


def parse_reported_json(stdout: str) -> dict[str, Any]:
    lines = [line for line in stdout.splitlines() if line.strip()]
    if not lines:
        return {}
    try:
        value = json.loads(lines[-1])
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def check_receipt(command: list[str], result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    reported = parse_reported_json(result.stdout)
    entry_count = None
    entries = reported.get("entries_checked")
    if isinstance(entries, list):
        entry_count = len(entries)
    proves = reported.get("proves")
    return {
        "command": command,
        "exit_code": result.returncode,
        "stdout_bytes": len(result.stdout.encode("utf-8")),
        "stdout_sha256": sha_text(result.stdout),
        "stderr_bytes": len(result.stderr.encode("utf-8")),
        "stderr_sha256": sha_text(result.stderr),
        "reported_schema": reported.get("schema"),
        "reported_ok": reported.get("ok"),
        "reported_entries_checked": entry_count,
        "reported_proves": proves if isinstance(proves, list) else None,
    }


def corpus_sha256(records: list[dict[str, Any]]) -> str:
    payload = "".join(corpus.json_line(row) + "\n" for row in records)
    return sha_text(payload)


def prove(root: Path) -> tuple[int, dict[str, Any]]:
    root = root.resolve()
    git_root = Path(git(root, "rev-parse", "--show-toplevel")).resolve()
    if git_root != root:
        raise corpus.CorpusError(
            f"repo root mismatch: requested {root}, git reports {git_root}"
        )

    head_sha = git(root, "rev-parse", "HEAD")
    branch = git(root, "branch", "--show-current") or "DETACHED"
    dirty_before = git(root, "status", "--porcelain=v1", "--untracked-files=normal")

    records, rejected = corpus.build_corpus(root)
    lane_counts = dict(sorted(Counter(row["lane"] for row in records).items()))

    corpus_test_cmd = [sys.executable, "-B", "tools/test_ascii_kinesis_corpus.py"]
    swarm_test_cmd = [sys.executable, "-B", "tools/test_ascii_kinesis_swarm_contract_v2.py"]
    corpus_test = run(corpus_test_cmd, root)
    swarm_test = run(swarm_test_cmd, root)

    dirty_after = git(root, "status", "--porcelain=v1", "--untracked-files=normal")
    compact_check = check_receipt(corpus_test_cmd, corpus_test)
    swarm_check = check_receipt(swarm_test_cmd, swarm_test)

    blockers: list[str] = []
    if dirty_before:
        blockers.append("WORKTREE_DIRTY_BEFORE_PROOF")
    if dirty_after:
        blockers.append("WORKTREE_DIRTY_AFTER_PROOF")
    if not records:
        blockers.append("EMPTY_CURRENT_CORPUS")
    if rejected:
        blockers.append("REJECTED_V2_SPECIMENS_PRESENT")
    if corpus_test.returncode != 0 or compact_check.get("reported_ok") is not True:
        blockers.append("COMPACT_CORPUS_CONTRACT_FAILED")
    if swarm_test.returncode != 0 or swarm_check.get("reported_ok") is not True:
        blockers.append("V2_SWARM_CONTRACT_FAILED")

    status = "PASS" if not blockers else "FAIL"
    receipt = {
        "schema": SCHEMA,
        "status": status,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository": {
            "root": str(root),
            "head_sha": head_sha,
            "branch": branch,
            "clean_before": not bool(dirty_before),
            "clean_after": not bool(dirty_after),
        },
        "corpus": {
            "record_count": len(records),
            "rejected_v2_count": len(rejected),
            "lane_counts": lane_counts,
            "corpus_sha256": corpus_sha256(records),
            "rejections": rejected,
        },
        "checks": {
            "compact_corpus_contract": compact_check,
            "v2_swarm_contract": swarm_check,
        },
        "runtime": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
        "blockers": blockers,
        "evidence_boundary": {
            "proves": [
                "current committed V2 corpus can be compactly indexed without raw ASCII/video bodies",
                "compact retrieval regression contract passes on this exact clean commit",
                "existing ASCII Kinesis V2 structural swarm contract passes on this exact clean commit",
                "receipt is bound to current corpus hashes and Git HEAD",
            ],
            "does_not_prove": [
                "artistic quality or human visual acceptance",
                "deployment or scheduler health",
                "Drew acceptance",
            ],
        },
    }
    return (0 if status == "PASS" else 1), receipt


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
        help="exact Git repository root; defaults to this script's repository",
    )
    p.add_argument(
        "--receipt",
        help="optional path to write the exact JSON receipt; stdout is always emitted",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        code, receipt = prove(Path(args.repo_root))
    except corpus.CorpusError as exc:
        receipt = {
            "schema": SCHEMA,
            "status": "FAIL",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "blockers": ["PROOF_RUNNER_ERROR"],
            "error": str(exc),
        }
        code = 2

    rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.receipt:
        path = Path(args.receipt)
        if not path.is_absolute():
            path = Path(args.repo_root).resolve() / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
