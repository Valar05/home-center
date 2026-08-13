#!/usr/bin/env python3
"""Receipt-enforced CLI envelope for the canonical Venice review organ."""
from __future__ import annotations

import contextlib
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import judgment_jar_receipts as usage  # noqa: E402
import venice_review  # noqa: E402
from judgment_jar_common import CONFIG_PATH, DEFAULT_CACHE, read_config  # noqa: E402
from judgment_jar_registry import ensure_registry, resolve_jar  # noqa: E402

REVIEW_JAR = "venice-review-gate"


def argument_value(args: list[str], name: str) -> str | None:
    try:
        index = args.index(name)
    except ValueError:
        return None
    return args[index + 1] if index + 1 < len(args) else None


def write_json(path_value: str | None, value: dict) -> None:
    if not path_value:
        return
    path = Path(path_value).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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
        print(json.dumps({
            "schema": "venice-review-judgment-jar-receipt-error.v1",
            "error": f"invalid_review_json:{exc}",
        }, sort_keys=True))
        return 2

    receipt_path = argument_value(args, "--receipt")
    try:
        config = read_config(CONFIG_PATH)
        registry, _ = ensure_registry(ROOT, DEFAULT_CACHE, config_path=CONFIG_PATH)
        jar = resolve_jar(registry, REVIEW_JAR)
        if jar is None:
            raise RuntimeError(f"canonical Venice Judgment Jar does not resolve: {REVIEW_JAR}")
        result = usage.record_usage(
            registry,
            config,
            jar,
            output_kind="review_verdict",
            output_summary=f"Canonical Venice review produced {review.get('directive') or 'UNKNOWN'}.",
            source="venice.review.cli",
            cache=DEFAULT_CACHE,
            status="allowed" if review.get("stopPermissionGranted") else "blocked",
            input_text=json.dumps({
                "repo": review.get("repo"),
                "base": review.get("base"),
                "head": review.get("head"),
                "acceptance": argument_value(args, "--acceptance") or "",
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
        review["jarUsageReceiptId"] = result["receipt"]["receiptId"]
        review["jarUsageOutputKind"] = result["receipt"]["output"]["kind"]
        review["jarUsageHomeCenterState"] = result["homeCenter"]["state"]
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

    write_json(receipt_path, review)
    print(json.dumps(review, ensure_ascii=False, indent=2, sort_keys=True))
    return original_code


if __name__ == "__main__":
    raise SystemExit(main())
