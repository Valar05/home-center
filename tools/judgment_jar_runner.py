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
from judgment_jar_receipt_truth import record as record_receipt
from judgment_jar_registry import ensure_registry, prompt_text, resolve_jar

SCHEMA = "home-center.judgment-jar-runner.v1"
STATES = {
    "CONTEXT_RECEIPTED", "REGNET_PENDING", "VENICE_PENDING", "CONTINUE", "STOP", "BLOCKED",
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
    return {
        "receiptId": receipt_id,
        "state": str(result.get("state") or receipt.get("receiptDeliveryState") or ""),
        "dedupFingerprint": str(receipt.get("dedupFingerprint") or ""),
    }


def prepare(
    request: dict[str, Any], *, root: Path = ROOT, cache: Path = DEFAULT_CACHE,
    config_path: Path = CONFIG_PATH,
    ensure: Callable[..., tuple[dict[str, Any], dict[str, Any]]] = ensure_registry,
    recorder: Callable[..., dict[str, Any]] = record_receipt,
) -> dict[str, Any]:
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
    registry, sync = ensure(root, cache, offline=bool(request.get("offline", True)), config_path=config_path)
    jars, missing, seen = [], [], set()
    for ref in refs:
        jar = resolve_jar(registry, ref)
        if jar is None:
            missing.append(ref)
        elif jar.get("id") not in seen:
            seen.add(jar.get("id")); jars.append(jar)
    if missing:
        raise RunnerError("unknown Judgment Jar(s): " + ", ".join(missing))
    packet = prompt_text(registry, [str(jar["id"]) for jar in jars], False)
    if not packet.strip() or len(packet) > limit:
        raise RunnerError(f"bounded context invalid ({len(packet)} > {limit})")
    group_id = str(request.get("groupId") or uuid.uuid4())
    request_id = str(request.get("requestId") or uuid.uuid4())
    receipts = []
    for jar in jars:
        result = recorder(
            registry, jar, config,
            output_kind="context_packet", output_text=packet,
            summary=f"Loaded Judgment Jar context: {jar.get('title') or jar.get('id')}",
            actor=str(request.get("actor") or "Adam"),
            intent="prepare bounded Judgment Jar candidate context", surface="jar",
            decision_action="included Jar in compiled candidate context",
            input_text=candidate, request_id=request_id, group_id=group_id,
            references=[str(v) for v in (jar.get("sourcePath"), jar.get("sourceUrl"), jar.get("sourceFileId")) if v],
            source="judgment-jar-runner.prepare",
        )
        receipts.append(_receipt_view(result))
    state = {
        "schema": SCHEMA, "state": "REGNET_PENDING", "releaseAllowed": False,
        "requestId": request_id, "groupId": group_id,
        "candidate": candidate, "candidateSha256": _sha(candidate),
        "jarIds": [str(jar["id"]) for jar in jars],
        "contextPacket": packet, "contextPacketSha256": _sha(packet),
        "registryDigest": str(registry.get("registryDigest") or ""),
        "registryState": str((sync or {}).get("state") or (registry.get("homeCenter") or {}).get("state") or "unknown"),
        "contextReceipts": receipts, "outputReceipts": [], "gates": {},
    }
    return state


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
    canonical = json.dumps(artifact, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    claimed = str(artifact.get("sha256") or "").strip().lower()
    artifact_without_sha = dict(artifact); artifact_without_sha.pop("sha256", None)
    digest = _sha(json.dumps(artifact_without_sha, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    if claimed and claimed != digest:
        raise RunnerError("artifact sha256 mismatch")
    return {"reviewer": reviewer, "verdict": verdict, "source": source, "sha256": digest, "artifact": artifact, "canonical": canonical}


def ingest_gate(
    state: dict[str, Any], request: dict[str, Any], *, config_path: Path = CONFIG_PATH,
    root: Path = ROOT, cache: Path = DEFAULT_CACHE,
    ensure: Callable[..., tuple[dict[str, Any], dict[str, Any]]] = ensure_registry,
    recorder: Callable[..., dict[str, Any]] = record_receipt,
) -> dict[str, Any]:
    gate = str(request.get("gate") or "").strip().lower()
    if gate not in {"regnet", "venice"}:
        raise RunnerError("gate must be regnet or venice")
    if gate == "venice" and (state.get("gates") or {}).get("regnet", {}).get("verdict") != "PASS":
        raise RunnerError("Venice artifact cannot be ingested before Regnet PASS")
    item = _artifact(request, "Regnet" if gate == "regnet" else "Venice", {"PASS", "FAIL"} if gate == "regnet" else {"CONTINUE", "STOP"})
    config = read_config(config_path)
    registry, _ = ensure(root, cache, offline=True, config_path=config_path)
    jar = resolve_jar(registry, str((state.get("jarIds") or [""])[0]))
    if jar is None:
        raise RunnerError("state primary Judgment Jar no longer resolves")
    result = recorder(
        registry, jar, config, output_kind="review_verdict", output_text=item["canonical"],
        summary=f"{item['reviewer']} returned {item['verdict']}", actor=item["reviewer"],
        intent="review bounded Judgment Jar candidate", surface="vlad",
        decision_action=item["verdict"], input_text=str(state.get("candidate") or ""),
        request_id=str(request.get("requestId") or uuid.uuid4()), group_id=str(state["groupId"]),
        references=[item["source"]], source="judgment-jar-runner.ingest-gate",
        metadata={"artifactSha256": item["sha256"], "gate": gate},
    )
    receipt = _receipt_view(result)
    updated = json.loads(json.dumps(state))
    updated.setdefault("gates", {})[gate] = {k: item[k] for k in ("reviewer", "verdict", "source", "sha256")}
    updated.setdefault("outputReceipts", []).append(receipt)
    if gate == "regnet":
        updated["state"] = "VENICE_PENDING" if item["verdict"] == "PASS" else "STOP"
    else:
        updated["state"] = item["verdict"]
    updated["releaseAllowed"] = release_allowed(updated)
    return updated


def release_allowed(state: dict[str, Any]) -> bool:
    gates = state.get("gates") or {}
    receipts = list(state.get("contextReceipts") or []) + list(state.get("outputReceipts") or [])
    delivered = bool(receipts) and all(str(r.get("state") or "").upper() == "DELIVERED" for r in receipts)
    return gates.get("regnet", {}).get("verdict") == "PASS" and gates.get("venice", {}).get("verdict") == "CONTINUE" and delivered


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=("prepare", "ingest-gate", "status"))
    ap.add_argument("--state", required=True, type=Path)
    args = ap.parse_args(argv)
    try:
        request = json.loads(sys.stdin.read() or "{}")
        if args.action == "prepare":
            value = prepare(request); _save(args.state, value)
        else:
            value = _read(args.state)
            if args.action == "ingest-gate":
                value = ingest_gate(value, request); _save(args.state, value)
            else:
                value["releaseAllowed"] = release_allowed(value)
        print(json.dumps(value, ensure_ascii=False, sort_keys=True))
        return 0
    except (RunnerError, RegistryError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "state": "BLOCKED", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
