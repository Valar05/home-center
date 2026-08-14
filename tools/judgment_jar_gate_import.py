#!/usr/bin/env python3
"""Import a durable Regnet-QA or Venice record as Runner gate authority.

This is deliberately a narrow bridge.  It does not run either reviewer and it
does not accept an arbitrary JSON document as authority.  A Regnet record must
be a receipt emitted under RENEE_QA_HOME/receipts; a Venice record must be an
exact line of HC_STATE_DIR/adam-daemon/venice-reviews.jsonl.

The review's native text field must contain a canonical JSON binding envelope.
That makes the durable reviewer record itself, rather than importer arguments,
bind the judgment to the Runner candidate and all of its authority inputs.
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Callable

import judgment_jar_runner as runner
from judgment_jar_common import CONFIG_PATH, DEFAULT_CACHE, read_config
from judgment_jar_receipts import build as build_receipt
from judgment_jar_receipts import capture as capture_receipt
from judgment_jar_receipts import fingerprint as receipt_fingerprint
from judgment_jar_registry import ensure_registry, resolve_jar

SCHEMA = "home-center.judgment-jar-gate-import.v1"
BINDING_SCHEMA = "home-center.judgment-jar-runner-gate-binding.v1"
REVIEW_REQUEST_SCHEMA = "home-center.judgment-jar-runner-review-request.v1"
NAMESPACE = uuid.UUID("6cf7a14e-41bb-5bc6-a188-d7d00bcd305d")
MAX_SOURCE_BYTES = 2_000_000
MAX_SOURCE_LINES = 100_000
MAX_SOURCE_LINE_BYTES = 256_000


class ImportError(RuntimeError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha_text(value: str) -> str:
    return _sha_bytes(value.encode("utf-8"))


def _regnet_canonical(value: Any) -> str:
    """Match tools/renee.py digest() exactly (not this module's UTF-8 JSON)."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _default_roots() -> dict[str, Path]:
    state = Path(os.path.expanduser(os.environ.get("HC_STATE_DIR", "~/.local/state/home-center")))
    regnet = Path(os.path.expanduser(os.environ.get("RENEE_QA_HOME", "~/.home-center/renee-qa")))
    return {"regnet": regnet / "receipts", "venice": state / "adam-daemon"}


def _authorized_source(gate: str, source: Path, roots: dict[str, Path]) -> Path:
    try:
        resolved = source.expanduser().resolve(strict=True)
        root = roots[gate].expanduser().resolve(strict=True)
    except (KeyError, OSError) as exc:
        raise ImportError(f"durable {gate} source or its fixed authority root is unavailable: {exc}") from exc
    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise ImportError(f"{gate} source is outside its fixed durable authority root") from exc
    if not resolved.is_file():
        raise ImportError("durable source is not a regular file")
    if gate == "regnet":
        if len(relative.parts) != 1 or resolved.suffix != ".json":
            raise ImportError("Regnet source must be a direct JSON receipt under RENEE_QA_HOME/receipts")
    elif relative.as_posix() != "venice-reviews.jsonl":
        raise ImportError("Venice source must be HC_STATE_DIR/adam-daemon/venice-reviews.jsonl")
    return resolved


def _read_exact_record(path: Path, line: int, gate: str) -> tuple[dict[str, Any], str]:
    if line < 1 or line > MAX_SOURCE_LINES:
        raise ImportError(f"source line must be between 1 and {MAX_SOURCE_LINES}")
    if gate == "regnet":
        if line != 1:
            raise ImportError("Regnet receipt is one JSON file record and must be selected as line 1")
        with path.open("rb") as stream:
            selected = stream.read(MAX_SOURCE_BYTES + 1)
        if len(selected) > MAX_SOURCE_BYTES:
            raise ImportError(f"durable Regnet source exceeds {MAX_SOURCE_BYTES} bytes")
    else:
        selected = b""
        with path.open("rb") as stream:
            for current in range(1, line + 1):
                row = stream.readline(MAX_SOURCE_LINE_BYTES + 2)
                if not row:
                    raise ImportError("selected durable source line does not exist")
                content = row.rstrip(b"\r\n")
                if len(content) > MAX_SOURCE_LINE_BYTES or (
                    not row.endswith((b"\n", b"\r")) and len(row) > MAX_SOURCE_LINE_BYTES
                ):
                    raise ImportError(f"durable source line exceeds {MAX_SOURCE_LINE_BYTES} bytes")
                if current == line:
                    selected = content
                    break
    if not selected.strip():
        raise ImportError("selected durable source record is blank")
    try:
        record = json.loads(selected.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ImportError("selected durable source line is not a UTF-8 JSON object") from exc
    if not isinstance(record, dict):
        raise ImportError("selected durable source record must be an object")
    return record, _sha_bytes(selected)


def _regnet_record(record: dict[str, Any], source: Path, review_request: str) -> tuple[str, str]:
    if record.get("schema") != "home-center.regnet-qa.review.v1":
        raise ImportError("invalid Regnet QA durable record schema")
    if record.get("reviewer") != "Regnet QA" or record.get("provenance") != "SYNTHETIC_REGNET":
        raise ImportError("Regnet QA record must preserve reviewer Regnet QA and SYNTHETIC_REGNET provenance")
    verdict = str(record.get("verdict") or "").upper()
    if verdict not in {"PASS", "REVISE_REQUIRED"}:
        raise ImportError("unsupported Regnet QA verdict")
    claimed = str(record.get("receipt_id") or "")
    if source.name != f"{claimed}.json":
        raise ImportError("Regnet QA receipt filename does not match receipt_id")
    if "receipt_path" in record:
        raise ImportError("Regnet durable receipt unexpectedly contains the non-durable receipt_path field")
    payload = dict(record)
    payload.pop("receipt_id", None)
    expected = "rqa-" + _sha_text(_regnet_canonical(payload))[:20]
    if claimed != expected:
        raise ImportError("Regnet QA receipt_id digest mismatch")
    if record.get("claim") != review_request:
        raise ImportError("Regnet QA durable claim is not the exact full runner review request")
    # Preserve the producer's repair-loop result.  It is not a terminal FAIL.
    return verdict, verdict


def _venice_record(
    record: dict[str, Any], review_request: str, expected_binding: dict[str, Any]
) -> tuple[str, str]:
    if record.get("schema") != "adam-venice-stop-review-v1":
        raise ImportError("invalid Venice durable completion-review schema")
    verdict = str(record.get("verdict") or "").upper()
    directive = str(record.get("directive") or "").upper()
    if verdict not in {"PASS", "FAIL"}:
        raise ImportError("unsupported Venice source verdict")
    if directive not in {"STOP_ALLOWED", "CONTINUE_REQUIRED", "HALT_REQUIRED"}:
        raise ImportError("unsupported Venice source directive")
    allowed = verdict == "PASS" and directive == "STOP_ALLOWED"
    repair = verdict == "FAIL" and directive == "CONTINUE_REQUIRED"
    halted = verdict == "FAIL" and directive == "HALT_REQUIRED"
    if not (allowed or repair or halted):
        raise ImportError("Venice source verdict/directive combination is incoherent")
    if bool(record.get("stopPermissionGranted")) != allowed:
        raise ImportError("Venice verdict/directive/stopPermissionGranted are inconsistent")
    if allowed and record.get("externalReviewGateSatisfied") is not True:
        raise ImportError("Venice STOP_ALLOWED lacks its external-review gate evidence")
    expected_sha = _sha_text(review_request)
    if record.get("taskSha256") != expected_sha:
        raise ImportError("Venice taskSha256 does not match the exact full runner review request")
    if record.get("task") != review_request[:4000]:
        raise ImportError("Venice persisted task is not the defined prefix of the full runner review request")
    proposal = record.get("proposal")
    if not isinstance(proposal, dict):
        raise ImportError("Venice durable review lacks its proposed terminal action")
    proposal_binding = proposal.get("judgmentJarRunner")
    expected_proposal_binding = {
        "binding": expected_binding,
        "reviewRequestSha256": expected_sha,
    }
    if proposal_binding != expected_proposal_binding:
        raise ImportError("Venice proposed terminal action is not bound to the runner review request")
    # Runner CONTINUE means continue through its release transition.  Venice's
    # native STOP_ALLOWED is the corresponding successful terminal judgment.
    if allowed:
        mapped = "CONTINUE"
    elif repair:
        mapped = "CONTINUE_REQUIRED"
    else:
        mapped = "STOP"
    return mapped, f"{verdict}/{directive}"


def binding_for_state(state: dict[str, Any], gate: str) -> dict[str, Any]:
    """Return the exact envelope a reviewer invocation must durably review."""
    runner.validate_state(state)
    return {
        "candidateSha256": state["candidateSha256"],
        "contextPacketSha256": state["contextPacketSha256"],
        "createdOutputSha256": state["createdOutputSha256"],
        "gate": gate,
        "groupId": state["groupId"],
        "jarIds": state["jarIds"],
        "nativeSourceDigests": [item["sourceSha256"] for item in state["nativeSources"]],
        "registryDigest": state["registryDigest"],
        "schema": BINDING_SCHEMA,
    }


def review_request_for_state(state: dict[str, Any], gate: str) -> str:
    """Canonical full-content request that must have been given to the reviewer.

    Digests are included as bindings, never as substitutes for the material to
    review.  The exact candidate, created output, and compiled controlling Jar
    context are all present alongside their identities.
    """
    runner.validate_state(state)
    if gate not in {"regnet", "venice"}:
        raise ImportError("gate must be regnet or venice")
    native_sources = [
        {
            "jarId": str(item.get("jarId") or ""),
            "sourceSha256": str(item.get("sourceSha256") or ""),
            **{key: item[key] for key in ("sourceFileId", "sourcePath", "sourceType") if item.get(key)},
        }
        for item in state.get("nativeSources") or []
    ]
    request = {
        "binding": binding_for_state(state, gate),
        "candidate": str(state.get("candidate") or ""),
        "contextPacket": str(state.get("contextPacket") or ""),
        "createdOutput": str(state.get("createdOutput") or ""),
        "createdOutputKind": str(state.get("createdOutputKind") or ""),
        "gate": gate,
        "jarIds": [str(value) for value in state.get("jarIds") or []],
        "nativeSources": native_sources,
        "schema": REVIEW_REQUEST_SCHEMA,
    }
    return _canonical(request)


def venice_proposal_binding_for_state(state: dict[str, Any]) -> dict[str, Any]:
    """Binding the proposed terminal action must carry into Venice review."""
    request = review_request_for_state(state, "venice")
    return {
        "binding": binding_for_state(state, "venice"),
        "reviewRequestSha256": _sha_text(request),
    }


def _capture(capturer: Callable[..., Any], receipt: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Call only an understood production capture(receipt, config) contract."""
    try:
        signature = inspect.signature(capturer)
        signature.bind(receipt, config)
    except (TypeError, ValueError) as exc:
        raise ImportError("production judgment_jar_receipts.capture(receipt, config) API is unavailable") from exc
    result = capturer(receipt, config)
    if not isinstance(result, dict):
        raise ImportError("production receipt capture returned a non-object")
    if result.get("ok") is False:
        raise ImportError("production receipt capture failed: " + str(result.get("error") or result.get("state")))
    captured = result.get("receipt") if isinstance(result.get("receipt"), dict) else result
    if captured.get("receiptId") != receipt.get("receiptId"):
        raise ImportError("production receipt capture changed deterministic receipt identity")
    if captured.get("dedupFingerprint") != receipt.get("dedupFingerprint"):
        raise ImportError("production receipt capture changed receipt fingerprint")
    return captured


def import_gate(
    state_path: Path, gate: str, source_path: Path, source_line: int, *,
    roots: dict[str, Path] | None = None, config_path: Path = CONFIG_PATH,
    root: Path = runner.ROOT, cache: Path = DEFAULT_CACHE,
    ensure: Callable[..., tuple[dict[str, Any], dict[str, Any]]] = ensure_registry,
    resolver: Callable[[dict[str, Any], str], dict[str, Any] | None] = resolve_jar,
    builder: Callable[..., dict[str, Any]] = build_receipt,
    capturer: Callable[..., Any] = capture_receipt,
    fingerprinter: Callable[[dict[str, Any]], str] = receipt_fingerprint,
) -> dict[str, Any]:
    gate = str(gate).strip().lower()
    if gate not in {"regnet", "venice"}:
        raise ImportError("gate must be regnet or venice")
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ImportError(f"runner state is unavailable or invalid: {exc}") from exc
    runner.validate_state(state)
    expected_state = "REGNET_PENDING" if gate == "regnet" else "VENICE_PENDING"
    if state.get("state") != expected_state:
        raise ImportError(f"runner state is not ready for {gate}: {state.get('state')}")

    source = _authorized_source(gate, source_path, roots or _default_roots())
    record, source_sha = _read_exact_record(source, source_line, gate)
    review_request = review_request_for_state(state, gate)
    binding = binding_for_state(state, gate)
    mapped, source_judgment = (
        _regnet_record(record, source, review_request)
        if gate == "regnet" else _venice_record(record, review_request, binding)
    )

    config = read_config(config_path)
    registry, _ = ensure(root, cache, offline=True, config_path=config_path)
    if str(registry.get("registryDigest") or "") != str(state.get("registryDigest") or ""):
        raise ImportError("Judgment Jar registry drift detected")
    jar = resolver(registry, gate)
    if not isinstance(jar, dict) or not str(jar.get("id") or ""):
        raise ImportError(f"expected {gate} gate Judgment Jar does not resolve")

    locator = f"{source}#line={source_line}&sha256={source_sha}"
    reviewers = getattr(runner, "TRUSTED_GATE_REVIEWERS", {"regnet": "Regnet QA", "venice": "Venice"})
    source_result = {
        "gate": gate,
        "mappedResult": mapped,
        "reviewer": reviewers[gate],
        "sourceDirective": str(record.get("directive") or "") if gate == "venice" else "",
        "sourceRecordSchema": record["schema"],
        "sourceRecordSha256": source_sha,
        "sourceVerdict": str(record.get("verdict") or ""),
    }
    if gate == "regnet":
        source_result["sourceProvenance"] = "SYNTHETIC_REGNET"
    elif record.get("reviewerMode") is not None:
        source_result["sourceReviewerMode"] = record["reviewerMode"]

    repair_required = mapped in {"REVISE_REQUIRED", "CONTINUE_REQUIRED"}
    advance_allowed = mapped in {"PASS", "CONTINUE"}
    transition_allowed = not repair_required
    artifact_core = {
        **{key: binding[key] for key in (
            "candidateSha256", "contextPacketSha256", "createdOutputSha256", "groupId",
            "jarIds", "nativeSourceDigests", "registryDigest",
        )},
        "reviewer": reviewers[gate],
        "verdict": mapped,
        "source": locator,
        "sourceRecordSchema": record["schema"],
        "sourceRecordSha256": source_sha,
    }
    if gate == "regnet":
        artifact_core["sourceProvenance"] = "SYNTHETIC_REGNET"
    elif record.get("reviewerMode") is not None:
        artifact_core["sourceReviewerMode"] = record["reviewerMode"]
    artifact = {**artifact_core, "sha256": _sha_text(_canonical(artifact_core))} if transition_allowed else None
    receipt_text = _canonical(artifact_core if artifact is not None else source_result)
    receipt_text_sha = _sha_text(receipt_text)

    receipt_id = str(uuid.uuid5(NAMESPACE, _canonical({
        "gate": gate, "jarId": jar["id"], "receiptOutputSha256": receipt_text_sha,
        "registryDigest": state["registryDigest"], "sourceLine": source_line, "sourceSha256": source_sha,
    })))
    metadata = {
        "authorityRoute": runner.TRUSTED_AUTHORITY_ROUTES[gate],
        "gate": gate,
        "sourceSchema": record["schema"],
        "sourceLine": source_line,
        "sourceSha256": source_sha,
        "verdict": str(record.get("verdict") or ""),
        "directive": str(record.get("directive") or "") if gate == "venice" else "",
    }
    if gate == "regnet":
        metadata["provenance"] = "SYNTHETIC_REGNET"
    elif record.get("reviewerMode") is not None:
        metadata["reviewerMode"] = record["reviewerMode"]
    receipt = builder(
        registry, jar, output_kind="review_verdict", output_text=receipt_text,
        summary=f"Imported durable {gate} judgment: {source_judgment}",
        actor=reviewers[gate],
        intent=("authorize a bound Judgment Jar runner gate" if transition_allowed
                else "audit a bound non-advancing Judgment Jar review result"),
        surface="vlad", decision_action=mapped, input_text=str(state.get("candidate") or ""),
        request_id=receipt_id, group_id=str(state["groupId"]), references=[locator],
        source=runner.TRUSTED_GATE_SOURCES[gate], metadata=metadata,
    )
    if not isinstance(receipt, dict):
        raise ImportError("production receipt builder returned a non-object")
    receipt["receiptId"] = receipt_id
    receipt["dedupFingerprint"] = fingerprinter(receipt)
    captured = _capture(capturer, receipt, config)
    authority = {"receiptId": receipt_id, "dedupFingerprint": str(captured.get("dedupFingerprint") or "")}
    if not authority["dedupFingerprint"]:
        raise ImportError("captured authority receipt has no fingerprint")
    result = {
        "schema": SCHEMA, "gate": gate,
        "advanceAllowed": advance_allowed,
        "repairRequired": repair_required,
        "transitionAllowed": transition_allowed,
        "runnerStateBefore": expected_state,
        "runnerStateAfterImport": expected_state,
        "sourceResult": source_result,
        "auditReceipt": {**authority, "outputKind": "review_verdict", "decisionAction": mapped},
        "ingestRequest": None,
        "sourceRecord": {"path": str(source), "line": source_line, "sha256": source_sha},
    }
    if transition_allowed:
        ingest_request = {
            "gate": gate, "requestId": receipt_id,
            "artifact": artifact, "authorityReceipt": authority,
        }
        result.update({
            "requestId": receipt_id, "artifact": artifact,
            "authorityReceipt": authority, "ingestRequest": ingest_request,
        })
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--gate", required=True, choices=("regnet", "venice"))
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--line", required=True, type=int)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(import_gate(args.state, args.gate, args.source, args.line), ensure_ascii=False, sort_keys=True))
        return 0
    except (ImportError, runner.RunnerError, OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "state": "BLOCKED", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
