#!/usr/bin/env python3
"""Receipt-enforced CLI wrapper for the canonical Venice review organ."""
from __future__ import annotations

import contextlib
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import judgement_jar_runtime as jar_runtime
import venice_review

REVIEW_JAR = ".continue/rules/70-judgement-jar-venice-review-gate.md"


def _argument_value(args: list[str], name: str) -> str | None:
    try:
        index = args.index(name)
    except ValueError:
        return None
    return args[index + 1] if index + 1 < len(args) else None


def _write_receipt_file(path_value: str | None, payload: dict) -> None:
    if not path_value:
        return
    path = Path(path_value).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(path)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        original_code = int(venice_review.main(args))
    raw = output.getvalue().strip()
    try:
        review = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(raw)
        print(json.dumps({"schema": "venice-review-jar-receipt-error.v1", "error": f"invalid_review_json:{exc}"}, sort_keys=True))
        return 2

    receipt_path = _argument_value(args, "--receipt")
    try:
        usage = jar_runtime.record_usage(
            REVIEW_JAR,
            output_kind="review_verdict",
            output_summary=f"Canonical Venice review produced {review.get('directive') or 'UNKNOWN'}.",
            source="venice.review.cli",
            status="allowed" if review.get("stopPermissionGranted") else "blocked",
            input_text=json.dumps({
                "repo": review.get("repo"),
                "base": review.get("base"),
                "head": review.get("head"),
                "acceptance": _argument_value(args, "--acceptance") or "",
            }, ensure_ascii=False, sort_keys=True),
            output_text=raw,
            request_id=str(review.get("fullDiffSha256") or review.get("reviewPromptDiffSha256") or ""),
            output_refs=[value for value in (receipt_path, review.get("durableMemoryPath")) if value],
            metadata={
                "verdict": review.get("verdict"),
                "directive": review.get("directive"),
                "reviewer": review.get("reviewer"),
                "reviewerMode": review.get("reviewerMode"),
                "deterministicOnly": "--deterministic-only" in args,
            },
        )
        review["jarUsageReceiptId"] = usage["receipt"]["receiptId"]
        review["jarUsageOutputKind"] = usage["receipt"]["output"]["kind"]
        review["jarUsageHomeCenterState"] = usage["homeCenter"]["state"]
    except Exception as exc:
        review.update({
            "verdict": "FAIL",
            "directive": "HALT_REQUIRED",
            "stopPermissionGranted": False,
            "continuationRequired": False,
            "haltRequired": True,
            "veniceReviewGateSatisfied": False,
            "externalReviewGateSatisfied": False,
            "jarUsageReceiptError": f"{type(exc).__name__}: {exc}",
        })
        review.setdefault("findings", []).append("judgment_jar_usage_receipt_capture_failed")
        original_code = 2

    _write_receipt_file(receipt_path, review)
    print(json.dumps(review, ensure_ascii=False, indent=2, sort_keys=True))
    return original_code


if __name__ == "__main__":
    raise SystemExit(main())
