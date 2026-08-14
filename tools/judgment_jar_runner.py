#!/usr/bin/env python3
"""One-shot, receipt-governed Judgment Jar gate runner.

This module deliberately does not invoke She-Raw, Regnet, or Venice.  It prepares
bounded Jar context, persists a small state record, and ingests externally
produced gate artifacts.  Release is fail-closed until Regnet passes, Venice says
CONTINUE, and every captured context/output receipt has been delivered.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from pathlib import Path
from typing import Any, Callable

TOOLS_DIR = Path(__file__).resolve().parent
ROOT = TOOLS_DIR.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from judgment_jar_common import CONFIG_PATH, DEFAULT_CACHE, RegistryError, read_config, write_atomic
from judgment_jar_receipts import paths as receipt_paths
from judgment_jar_receipt_truth import (
    build as build_receipt,
    capture as capture_receipt,
    fingerprint as receipt_fingerprint,
    validate as validate_receipt,
)
from judgment_jar_registry import ensure_registry, fetch_native_source, resolve_jar

SCHEMA = "home-center.judgment-jar-runner.v1"
STATES = {
    "CONTEXT_RECEIPTED", "OUTPUT_RECEIPTED", "REGNET_PENDING", "VENICE_PENDING",
    "VENICE_CONTINUE_PENDING_RECEIPTS", "RELEASED", "STOP", "BLOCKED",
}
TRUSTED_GATE_SOURCES = {
    "regnet": "judgment-jar-gate-import.regnet-qa",
    "venice": "judgment-jar-gate-import.venice-completion",
}
TRUSTED_AUTHORITY_ROUTES = {
    "regnet": "fixed-durable-source:renee-qa-receipts",
    "venice": "fixed-durable-source:adam-daemon-venice-reviews",
}


class RunnerError(RuntimeError):
    pass


def _sha(text: str) -> str:
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema") != SCHEMA:
        raise RunnerError("invalid Judgment Jar runner state schema")
    return value


def _save(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(path, value)


def _receipt_view(result: dict[str, Any]) -> dict[str, Any]:
    if result.get("ok") is not True:
        raise RunnerError("Judgment Jar receipt capture failed: " + str(result.get("error") or result.get("state")))
    receipt = result.get("receipt") or {}
    receipt_id = str(receipt.get("receiptId") or "")
    if not receipt_id:
        raise RunnerError("Judgment Jar receipt capture returned no receiptId")
    view = {
        "receiptId": receipt_id,
        "state": str(result.get("state") or receipt.get("receiptDeliveryState") or ""),
        "dedupFingerprint": str(receipt.get("dedupFingerprint") or ""),
        "jarId": str((receipt.get("jar") or {}).get("id") or ""),
        "outputKind": str((receipt.get("output") or {}).get("kind") or ""),
    }
    if not all(view[key] for key in ("dedupFingerprint", "jarId", "outputKind")):
        raise RunnerError("Judgment Jar receipt capture returned incomplete identity metadata")
    return view


def deterministic_record(
    registry: dict[str, Any], jar: dict[str, Any], config: dict[str, Any], *,
    operation_key: str, builder: Callable[..., dict[str, Any]] = build_receipt,
    capturer: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]] = capture_receipt,
    fingerprinter: Callable[[dict[str, Any]], str] = receipt_fingerprint, **kwargs: Any,
) -> dict[str, Any]:
    """Build and capture a retry-stable receipt using production truth primitives."""
    key = str(operation_key or "").strip()
    if not key:
        raise RunnerError("deterministic receipt operation key is required")
    receipt = builder(registry, jar, **kwargs)
    receipt["receiptId"] = str(uuid.uuid5(uuid.NAMESPACE_URL, "home-center.judgment-jar-runner:" + key))
    receipt["dedupFingerprint"] = fingerprinter(receipt)
    result = capturer(receipt, config)
    captured = result.get("receipt") or {}
    if (captured.get("receiptId") != receipt["receiptId"]
            or captured.get("dedupFingerprint") != receipt["dedupFingerprint"]):
        raise RunnerError("deterministic receipt capture returned conflicting identity")
    return result


def _capture(
    recorder: Callable[..., dict[str, Any]] | None, registry: dict[str, Any], jar: dict[str, Any],
    config: dict[str, Any], *, operation_key: str, **kwargs: Any,
) -> dict[str, Any]:
    if recorder is not None:
        return recorder(registry, jar, config, **kwargs)
    return deterministic_record(registry, jar, config, operation_key=operation_key, **kwargs)


def _require_sha(value: Any, field: str) -> str:
    text = str(value or "").strip().lower()
    if len(text) != 64 or any(char not in "0123456789abcdef" for char in text):
        raise RunnerError(f"{field} must be a lowercase SHA-256 digest")
    return text


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _prepare_request(request: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """Return the stable caller-controlled prepare request used for replay checks."""
    view = {
        "requestId": str(request.get("requestId") or "").strip(),
        "groupId": str(request.get("groupId") or "").strip(),
        "jarRefs": [str(value).strip() for value in request.get("jarRefs") or [] if str(value).strip()],
        "candidate": str(request.get("candidate") or "").strip(),
        "actor": str(request.get("actor") or "Adam").strip(),
        "offline": bool(request.get("offline", False)),
        "allowStaleNative": bool(request.get("allowStaleNative", False)),
    }
    return view, _sha(_canonical(view))


def _prepare_replay(state: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    validate_state(state)
    view, digest = _prepare_request(request)
    if state.get("prepareRequest") == view and state.get("prepareRequestSha256") == digest:
        return state
    raise RunnerError("conflicting prepare replay for existing state")


def _validate_receipts(state: dict[str, Any]) -> None:
    receipts = list(state.get("contextReceipts") or []) + list(state.get("outputReceipts") or [])
    ids: set[str] = set()
    for receipt in receipts:
        if not isinstance(receipt, dict):
            raise RunnerError("runner state contains an invalid receipt")
        receipt_id = str(receipt.get("receiptId") or "").strip()
        fingerprint = str(receipt.get("dedupFingerprint") or "").strip()
        if not receipt_id or not fingerprint:
            raise RunnerError("runner state receipt is missing receiptId or dedupFingerprint")
        if receipt_id in ids:
            raise RunnerError(f"runner state contains duplicate receiptId: {receipt_id}")
        ids.add(receipt_id)

    jar_ids = state.get("jarIds") or []
    context = state.get("contextReceipts") or []
    if len(context) != len(jar_ids):
        raise RunnerError("context receipt count must match jarIds")
    if [r.get("jarId") for r in context] != jar_ids or any(r.get("outputKind") != "context_packet" for r in context):
        raise RunnerError("context receipt Jar identity or kind mismatch")
    output = state.get("outputReceipts") or []
    created_count = len(jar_ids) if state.get("createdOutputSha256") else 0
    gate_count = len(state.get("gates") or {})
    if len(output) != created_count + gate_count:
        raise RunnerError("output receipt count does not match created output and gates")
    created = output[:created_count]
    if created_count and (
        [r.get("jarId") for r in created] != jar_ids
        or any(r.get("outputKind") != state.get("createdOutputKind") for r in created)
    ):
        raise RunnerError("created-output receipt Jar identity or kind mismatch")
    for receipt in output[created_count:]:
        if receipt.get("outputKind") != "review_verdict":
            raise RunnerError("gate receipt kind mismatch")
    gate_order = [gate for gate in ("regnet", "venice") if gate in (state.get("gates") or {})]
    if [r.get("jarId") for r in output[created_count:]] != [state["gates"][gate].get("jarId") for gate in gate_order]:
        raise RunnerError("gate receipt Jar identity mismatch")


def _delivered_receipts(
    config: dict[str, Any], path_resolver: Callable[[dict[str, Any]], dict[str, Any]],
    validator: Callable[[dict[str, Any], dict[str, Any]], None] = validate_receipt,
) -> list[dict[str, Any]]:
    delivered_root = Path(path_resolver(config)["delivered"])
    verified: list[dict[str, Any]] = []
    if not delivered_root.exists():
        return verified
    for path in sorted(delivered_root.rglob("*.json")):
        try:
            receipt = _receipt_document(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if not receipt:
            continue
        try:
            validator(receipt, config)
        except Exception:
            continue
        if str(receipt.get("receiptDeliveryState") or "").upper() != "DELIVERED":
            continue
        if str(receipt.get("homeCenterDeliveryState") or "").upper() != "DELIVERED":
            continue
        if (receipt.get("homeCenter") or {}).get("readbackVerified") is not True:
            continue
        verified.append(receipt)
    return verified


def validate_state(state: dict[str, Any]) -> None:
    if state.get("schema") != SCHEMA:
        raise RunnerError("invalid Judgment Jar runner state schema")
    if str(state.get("state") or "") not in STATES:
        raise RunnerError("invalid Judgment Jar runner state transition value")
    candidate = str(state.get("candidate") or "")
    context = str(state.get("contextPacket") or "")
    candidate_digest = _require_sha(state.get("candidateSha256"), "candidateSha256")
    context_digest = _require_sha(state.get("contextPacketSha256"), "contextPacketSha256")
    if candidate_digest != _sha(candidate):
        raise RunnerError("candidateSha256 does not match candidate")
    if context_digest != _sha(context):
        raise RunnerError("contextPacketSha256 does not match contextPacket")
    if not str(state.get("requestId") or "").strip():
        raise RunnerError("runner state requestId is missing")
    if not str(state.get("groupId") or "").strip():
        raise RunnerError("runner state groupId is missing")
    if not str(state.get("registryDigest") or "").strip():
        raise RunnerError("runner state registryDigest is missing")
    jar_ids = state.get("jarIds")
    if not isinstance(jar_ids, list) or not jar_ids or len(jar_ids) != len(set(jar_ids)):
        raise RunnerError("runner state jarIds must be a non-empty unique list")
    native_sources = state.get("nativeSources")
    if not isinstance(native_sources, list) or [str(v.get("jarId") or "") for v in native_sources] != jar_ids:
        raise RunnerError("runner state nativeSources must cover jarIds in order")
    for source in native_sources:
        _require_sha(source.get("sourceSha256"), "native sourceSha256")
    prepare_view = state.get("prepareRequest")
    if not isinstance(prepare_view, dict) or _sha(_canonical(prepare_view)) != _require_sha(
        state.get("prepareRequestSha256"), "prepareRequestSha256"
    ):
        raise RunnerError("prepare request digest mismatch")
    gates = state.get("gates") or {}
    if set(gates) - {"regnet", "venice"} or ("venice" in gates and "regnet" not in gates):
        raise RunnerError("gate structure is incoherent")
    state_name = state.get("state")
    if state_name == "CONTEXT_RECEIPTED" and (state.get("createdOutputSha256") or gates):
        raise RunnerError("CONTEXT_RECEIPTED state contains downstream material")
    if state_name != "CONTEXT_RECEIPTED":
        created_digest = _require_sha(state.get("createdOutputSha256"), "createdOutputSha256")
        if created_digest != _sha(str(state.get("createdOutput") or "")):
            raise RunnerError("createdOutputSha256 does not match createdOutput")
        if str(state.get("createdOutputKind") or "") not in {"answer", "artifact"}:
            raise RunnerError("createdOutputKind must be answer or artifact")
    if state_name in {"OUTPUT_RECEIPTED", "REGNET_PENDING"} and gates:
        raise RunnerError("pre-Regnet state contains gate material")
    if state_name == "VENICE_PENDING" and gates.get("regnet", {}).get("verdict") != "PASS":
        raise RunnerError("VENICE_PENDING requires Regnet PASS")
    if state_name in {"VENICE_CONTINUE_PENDING_RECEIPTS", "RELEASED"} and (
        gates.get("regnet", {}).get("verdict") != "PASS" or gates.get("venice", {}).get("verdict") != "CONTINUE"
    ):
        raise RunnerError("release state gate coherence failed")
    _validate_receipts(state)


def _validate_artifact_binding(state: dict[str, Any], artifact: dict[str, Any]) -> None:
    bindings = {
        "candidateSha256": state.get("candidateSha256"),
        "contextPacketSha256": state.get("contextPacketSha256"),
        "groupId": state.get("groupId"),
        "registryDigest": state.get("registryDigest"),
        "nativeSourceDigests": [source["sourceSha256"] for source in state.get("nativeSources") or []],
        "createdOutputSha256": state.get("createdOutputSha256"),
    }
    for field, expected in bindings.items():
        actual = artifact.get(field)
        if actual is None or actual == "":
            raise RunnerError(f"artifact {field} is required")
        if str(actual) != str(expected):
            raise RunnerError(f"artifact {field} does not match runner state")
    artifact_jars = artifact.get("jarIds")
    if not isinstance(artifact_jars, list) or [str(x) for x in artifact_jars] != state.get("jarIds"):
        raise RunnerError("artifact jarIds does not match runner state")


def _native_packet(jars: list[dict[str, Any]], config: dict[str, Any], cache: Path,
                   *, offline: bool, allow_stale: bool,
                   native_fetcher: Callable[..., dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    chunks: list[str] = []
    sources: list[dict[str, Any]] = []
    for jar in jars:
        status = str(jar.get("status") or "").lower()
        if status not in {"active", "mature"}:
            raise RunnerError(f"Judgment Jar {jar.get('id')} is not executable ({status or 'unknown'})")
        source = native_fetcher(jar, config, cache, refresh=not offline, offline=offline)
        if source.get("ok") is not True or str(source.get("jarId") or "") != str(jar.get("id") or ""):
            raise RunnerError(f"native source identity failed for {jar.get('id')}")
        source_state = str(source.get("state") or "unknown")
        if source_state == "stale" and not allow_stale:
            raise RunnerError(f"native source for {jar.get('id')} is stale")
        if isinstance(source.get("content"), str):
            content = source["content"]
        elif isinstance(source.get("sheet"), dict):
            content = json.dumps(source["sheet"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        else:
            raise RunnerError(f"native source payload missing for {jar.get('id')}")
        if not content.strip():
            raise RunnerError(f"native source for {jar.get('id')} was empty")
        digest = _require_sha(source.get("sourceSha256"), "native sourceSha256")
        if digest != _sha(content):
            raise RunnerError(f"native source digest mismatch for {jar.get('id')}")
        sources.append({
            "jarId": str(jar["id"]), "sourceSha256": digest, "state": source_state,
            **{k: source[k] for k in ("sourceFileId", "sourcePath", "sourceType") if source.get(k)},
        })
        chunks.append(f"JUDGMENT JAR: {jar['id']}\nNATIVE SOURCE SHA256: {digest}\n\n{content.rstrip()}")
    return "\n\n".join(chunks).rstrip() + "\n", sources


def prepare(
    request: dict[str, Any], *, root: Path = ROOT, cache: Path = DEFAULT_CACHE,
    config_path: Path = CONFIG_PATH,
    ensure: Callable[..., tuple[dict[str, Any], dict[str, Any]]] = ensure_registry,
    recorder: Callable[..., dict[str, Any]] | None = None,
    native_fetcher: Callable[..., dict[str, Any]] = fetch_native_source,
) -> dict[str, Any]:
    prepare_request, prepare_digest = _prepare_request(request)
    request_id = str(request.get("requestId") or "").strip()
    if not request_id:
        raise RunnerError("requestId is required")
    refs = [str(x).strip() for x in request.get("jarRefs") or [] if str(x).strip()]
    if not refs:
        raise RunnerError("jarRefs must contain at least one explicit Judgment Jar id or alias")
    if len(refs) > 8:
        raise RunnerError("jarRefs exceeds the bounded maximum of 8")
    candidate = str(request.get("candidate") or "").strip()
    if not candidate:
        raise RunnerError("candidate is required")
    config = read_config(config_path)
    limit = int((config.get("runtime") or {}).get("maxPhonePromptCharacters") or 18000)
    offline = bool(request.get("offline", False))
    registry, sync = ensure(root, cache, offline=offline, config_path=config_path)
    jars, missing, seen = [], [], set()
    for ref in refs:
        jar = resolve_jar(registry, ref)
        if jar is None:
            missing.append(ref)
        elif jar.get("id") not in seen:
            seen.add(jar.get("id")); jars.append(jar)
    if missing:
        raise RunnerError("unknown Judgment Jar(s): " + ", ".join(missing))
    packet, native_sources = _native_packet(
        jars, config, cache, offline=offline,
        allow_stale=bool(request.get("allowStaleNative", False)), native_fetcher=native_fetcher,
    )
    if not packet.strip() or len(packet) > limit:
        raise RunnerError(f"bounded context invalid ({len(packet)} > {limit})")
    # The stable fallback group and per-Jar request IDs make capture retryable:
    # production receipt capture deduplicates identical requests, so a crash
    # after Jar N can safely replay Jars 1..N without creating new receipts.
    group_id = str(request.get("groupId") or uuid.uuid5(uuid.NAMESPACE_URL, f"judgment-jar-prepare:{prepare_digest}"))
    receipts = []
    for jar in jars:
        result = _capture(recorder, registry, jar, config, operation_key=f"prepare:{prepare_digest}:{jar['id']}",
            output_kind="context_packet", output_text=packet,
            summary=f"Loaded Judgment Jar context: {jar.get('title') or jar.get('id')}",
            actor=str(request.get("actor") or "Adam"),
            intent="prepare bounded Judgment Jar candidate context", surface="jar",
            decision_action="included Jar in compiled candidate context",
            input_text=candidate, request_id=f"{request_id}:prepare:{jar['id']}", group_id=group_id,
            references=[str(v) for v in (jar.get("sourcePath"), jar.get("sourceUrl"), jar.get("sourceFileId")) if v],
            source="judgment-jar-runner.prepare",
        )
        receipts.append(_receipt_view(result))
    state = {
        "schema": SCHEMA, "state": "CONTEXT_RECEIPTED", "releaseAllowed": False,
        "requestId": request_id, "groupId": group_id,
        "prepareRequest": prepare_request, "prepareRequestSha256": prepare_digest,
        "candidate": candidate, "candidateSha256": _sha(candidate),
        "jarIds": [str(jar["id"]) for jar in jars],
        "contextPacket": packet, "contextPacketSha256": _sha(packet),
        "registryDigest": str(registry.get("registryDigest") or ""),
        "registryState": str((sync or {}).get("state") or (registry.get("homeCenter") or {}).get("state") or "unknown"),
        "nativeSources": native_sources,
        "contextReceipts": receipts, "outputReceipts": [], "gates": {},
    }
    validate_state(state)
    return state


def record_output(
    state: dict[str, Any], request: dict[str, Any], *, config_path: Path = CONFIG_PATH,
    root: Path = ROOT, cache: Path = DEFAULT_CACHE,
    ensure: Callable[..., tuple[dict[str, Any], dict[str, Any]]] = ensure_registry,
    recorder: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    validate_state(state)
    output_text = str(request.get("createdOutput") or "")
    output_kind = str(request.get("outputKind") or "").strip().lower()
    request_id = str(request.get("requestId") or "").strip()
    if not output_text.strip() or output_kind not in {"answer", "artifact"} or not request_id:
        raise RunnerError("record-output requires requestId, createdOutput, and outputKind answer or artifact")
    digest = _sha(output_text)
    if state.get("createdOutputSha256"):
        if state.get("createdOutputSha256") == digest and state.get("createdOutputKind") == output_kind:
            return state
        raise RunnerError("divergent replay for created output")
    if state.get("state") != "CONTEXT_RECEIPTED":
        raise RunnerError(f"illegal record-output transition from {state.get('state')}")
    config = read_config(config_path)
    registry, _ = ensure(root, cache, offline=True, config_path=config_path)
    if str(registry.get("registryDigest") or "") != str(state.get("registryDigest") or ""):
        raise RunnerError("Judgment Jar registry drift detected")
    captured: list[dict[str, Any]] = []
    for jar_id in state["jarIds"]:
        jar = resolve_jar(registry, jar_id)
        if jar is None or str(jar.get("id") or "") != jar_id:
            raise RunnerError(f"created-output Judgment Jar no longer resolves: {jar_id}")
        captured.append(_receipt_view(_capture(
            recorder, registry, jar, config,
            operation_key=f"record-output:{state['groupId']}:{jar_id}:{output_kind}:{digest}",
            output_kind=output_kind, output_text=output_text,
            summary="Captured candidate output for gated Judgment Jar review", actor=str(request.get("actor") or "Adam"),
            intent="capture created output before Regnet QA", surface="jar",
            decision_action="submitted output to Judgment Jar gate chain",
            input_text=str(state.get("candidate") or ""),
            request_id=f"{state['requestId']}:output:{jar_id}:{digest}",
            group_id=str(state["groupId"]), references=[], source="judgment-jar-runner.record-output",
            metadata={"createdOutputSha256": digest, "jarCoverage": state["jarIds"]},
        )))
    updated = json.loads(json.dumps(state))
    updated["createdOutput"] = output_text
    updated["createdOutputSha256"] = digest
    updated["createdOutputKind"] = output_kind
    updated["outputReceipts"] = captured
    updated["state"] = "REGNET_PENDING"
    validate_state(updated)
    return updated


def _artifact(request: dict[str, Any], reviewer: str, allowed: set[str]) -> dict[str, Any]:
    artifact = request.get("artifact")
    if not isinstance(artifact, dict):
        raise RunnerError("artifact object is required")
    if str(artifact.get("reviewer") or "").strip().casefold() != reviewer.casefold():
        raise RunnerError(f"artifact reviewer must be {reviewer}")
    verdict = str(artifact.get("verdict") or "").strip().upper()
    if verdict not in allowed:
        raise RunnerError(f"unsupported {reviewer} verdict: {verdict or '<empty>'}")
    source = str(artifact.get("source") or "").strip()
    if not source:
        raise RunnerError("artifact source is required")
    claimed = _require_sha(artifact.get("sha256"), "artifact sha256")
    artifact_without_sha = dict(artifact); artifact_without_sha.pop("sha256", None)
    canonical_core = _canonical(artifact_without_sha)
    digest = _sha(canonical_core)
    if claimed != digest:
        raise RunnerError("artifact sha256 mismatch")
    authority = request.get("authorityReceipt")
    if not isinstance(authority, dict):
        raise RunnerError("request authorityReceipt object is required")
    source_receipt_id = str(authority.get("receiptId") or "").strip()
    source_receipt_fingerprint = str(authority.get("dedupFingerprint") or "").strip()
    if not source_receipt_id or not source_receipt_fingerprint:
        raise RunnerError("authorityReceipt receiptId and dedupFingerprint are required")
    return {"reviewer": reviewer, "verdict": verdict, "source": source, "sha256": digest,
            "sourceReceiptId": source_receipt_id, "sourceReceiptFingerprint": source_receipt_fingerprint,
            "artifact": artifact, "canonicalCore": canonical_core}


def _verify_gate_source(state: dict[str, Any], item: dict[str, Any], gate: str, expected_jar_id: str,
                        config: dict[str, Any], path_resolver: Callable[[dict[str, Any]], dict[str, Any]],
                        validator: Callable[[dict[str, Any], dict[str, Any]], None]) -> None:
    for receipt in _delivered_receipts(config, path_resolver, validator):
        if str(receipt.get("receiptId") or "") != item["sourceReceiptId"]:
            continue
        if str(receipt.get("dedupFingerprint") or "") != item["sourceReceiptFingerprint"]:
            continue
        if str(receipt.get("actor") or "").casefold() != item["reviewer"].casefold():
            raise RunnerError(f"{gate} source receipt actor mismatch")
        output = receipt.get("output") or {}
        invocation = receipt.get("invocation") or {}
        jar = receipt.get("jar") or {}
        if output.get("kind") != "review_verdict" or output.get("sha256") != item["sha256"]:
            raise RunnerError(f"{gate} source receipt output mismatch")
        if str(invocation.get("groupId") or "") != str(state.get("groupId") or ""):
            raise RunnerError(f"{gate} source receipt group mismatch")
        if str(jar.get("id") or "") != expected_jar_id:
            raise RunnerError(f"{gate} source receipt Jar mismatch")
        if str(jar.get("registryDigest") or "") != str(state.get("registryDigest") or ""):
            raise RunnerError(f"{gate} source receipt registry mismatch")
        if invocation.get("source") != TRUSTED_GATE_SOURCES[gate]:
            raise RunnerError(f"{gate} source receipt invocation source mismatch")
        if (receipt.get("metadata") or {}).get("authorityRoute") != TRUSTED_AUTHORITY_ROUTES[gate]:
            raise RunnerError(f"{gate} source receipt authority route mismatch")
        return
    raise RunnerError(f"verified delivered {gate} source receipt was not found")


def ingest_gate(
    state: dict[str, Any], request: dict[str, Any], *, config_path: Path = CONFIG_PATH,
    root: Path = ROOT, cache: Path = DEFAULT_CACHE,
    ensure: Callable[..., tuple[dict[str, Any], dict[str, Any]]] = ensure_registry,
    recorder: Callable[..., dict[str, Any]] | None = None,
    path_resolver: Callable[[dict[str, Any]], dict[str, Any]] = receipt_paths,
    receipt_validator: Callable[[dict[str, Any], dict[str, Any]], None] = validate_receipt,
) -> dict[str, Any]:
    validate_state(state)
    request_id = str(request.get("requestId") or "").strip()
    if not request_id:
        raise RunnerError("gate requestId is required")
    gate = str(request.get("gate") or "").strip().lower()
    if gate not in {"regnet", "venice"}:
        raise RunnerError("gate must be regnet or venice")
    item = _artifact(request, "Regnet QA" if gate == "regnet" else "Venice", {"PASS", "FAIL"} if gate == "regnet" else {"CONTINUE", "STOP"})
    _validate_artifact_binding(state, item["artifact"])
    existing = (state.get("gates") or {}).get(gate)
    if existing is not None:
        authority = existing.get("authorityReceipt") or {}
        if (all(existing.get(key) == item[key] for key in ("reviewer", "verdict", "source", "sha256"))
                and authority.get("receiptId") == item["sourceReceiptId"]
                and authority.get("dedupFingerprint") == item["sourceReceiptFingerprint"]):
            return state
        raise RunnerError(f"divergent replay for {gate} gate")
    expected_state = "REGNET_PENDING" if gate == "regnet" else "VENICE_PENDING"
    if state.get("state") != expected_state:
        raise RunnerError(f"illegal {gate} gate transition from {state.get('state')}")
    if gate == "venice" and (state.get("gates") or {}).get("regnet", {}).get("verdict") != "PASS":
        raise RunnerError("Venice artifact cannot be ingested before Regnet PASS")
    config = read_config(config_path)
    registry, _ = ensure(root, cache, offline=True, config_path=config_path)
    if str(registry.get("registryDigest") or "") != str(state.get("registryDigest") or ""):
        raise RunnerError("Judgment Jar registry drift detected")
    jar = resolve_jar(registry, gate)
    if jar is None:
        raise RunnerError(f"{gate} gate Judgment Jar no longer resolves")
    _verify_gate_source(state, item, gate, str(jar["id"]), config, path_resolver, receipt_validator)
    result = _capture(
        recorder, registry, jar, config,
        operation_key=f"ingest-gate:{state['groupId']}:{gate}:{item['sha256']}",
        output_kind="review_verdict", output_text=item["canonicalCore"],
        summary=f"{item['reviewer']} returned {item['verdict']}", actor=item["reviewer"],
        intent="review bounded Judgment Jar candidate", surface="vlad",
        decision_action=item["verdict"], input_text=str(state.get("candidate") or ""),
        request_id=f"{state['requestId']}:gate:{gate}:{item['sha256']}", group_id=str(state["groupId"]),
        references=[item["source"]], source="judgment-jar-runner.ingest-gate",
        metadata={"artifactSha256": item["sha256"], "gate": gate},
    )
    receipt = _receipt_view(result)
    updated = json.loads(json.dumps(state))
    updated.setdefault("gates", {})[gate] = {
        **{k: item[k] for k in ("reviewer", "verdict", "source", "sha256")},
        "jarId": str(jar["id"]),
        "authorityReceipt": {"receiptId": item["sourceReceiptId"], "dedupFingerprint": item["sourceReceiptFingerprint"]},
    }
    updated.setdefault("outputReceipts", []).append(receipt)
    _validate_receipts(updated)
    if gate == "regnet":
        updated["state"] = "VENICE_PENDING" if item["verdict"] == "PASS" else "STOP"
    else:
        updated["state"] = "VENICE_CONTINUE_PENDING_RECEIPTS" if item["verdict"] == "CONTINUE" else "STOP"
    updated["releaseAllowed"] = release_allowed(updated)
    validate_state(updated)
    return updated


def _receipt_document(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    nested = value.get("receipt")
    return nested if isinstance(nested, dict) else value


def _release_conditions(state: dict[str, Any]) -> bool:
    gates = state.get("gates") or {}
    receipts = list(state.get("contextReceipts") or []) + list(state.get("outputReceipts") or [])
    delivered = bool(receipts) and all(str(r.get("state") or "").upper() == "DELIVERED" for r in receipts)
    return gates.get("regnet", {}).get("verdict") == "PASS" and gates.get("venice", {}).get("verdict") == "CONTINUE" and delivered


def reconcile(
    state: dict[str, Any], *, config_path: Path = CONFIG_PATH,
    path_resolver: Callable[[dict[str, Any]], dict[str, Any]] = receipt_paths,
    receipt_validator: Callable[[dict[str, Any], dict[str, Any]], None] = validate_receipt,
) -> dict[str, Any]:
    """Reconcile receipt views against verified files from the delivered spool."""
    validate_state(state)
    config = read_config(config_path)
    verified = {(str(r.get("receiptId") or ""), str(r.get("dedupFingerprint") or ""))
                for r in _delivered_receipts(config, path_resolver, receipt_validator)}
    updated = json.loads(json.dumps(state))
    for receipt in list(updated.get("contextReceipts") or []) + list(updated.get("outputReceipts") or []):
        receipt["state"] = "PENDING_HOME_CENTER"
        key = (str(receipt.get("receiptId") or ""), str(receipt.get("dedupFingerprint") or ""))
        if key in verified:
            receipt["state"] = "DELIVERED"
    gates = updated.get("gates") or {}
    if gates.get("regnet", {}).get("verdict") == "PASS" and gates.get("venice", {}).get("verdict") == "CONTINUE":
        updated["state"] = "RELEASED" if _release_conditions(updated) else "VENICE_CONTINUE_PENDING_RECEIPTS"
    updated["releaseAllowed"] = release_allowed(updated)
    validate_state(updated)
    return updated


def release_allowed(state: dict[str, Any]) -> bool:
    return state.get("state") == "RELEASED" and _release_conditions(state)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=("prepare", "record-output", "ingest-gate", "reconcile", "status"))
    ap.add_argument("--state", required=True, type=Path)
    args = ap.parse_args(argv)
    try:
        request = json.loads(sys.stdin.read() or "{}")
        if args.action == "prepare":
            value = _prepare_replay(_read(args.state), request) if args.state.exists() else prepare(request)
            _save(args.state, value)
        else:
            value = _read(args.state)
            if args.action == "record-output":
                value = record_output(value, request); _save(args.state, value)
            elif args.action == "ingest-gate":
                value = ingest_gate(value, request); _save(args.state, value)
            elif args.action in {"reconcile", "status"}:
                value = reconcile(value); _save(args.state, value)
        print(json.dumps(value, ensure_ascii=False, sort_keys=True))
        return 0
    except (RunnerError, RegistryError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "state": "BLOCKED", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
