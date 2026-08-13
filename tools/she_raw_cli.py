#!/usr/bin/env python3
"""Phone-local She Raw conversation surface for the Adam CLI.

User speech is sent unchanged as its own user message to a loopback OpenAI-
compatible endpoint. Character canon and optionally pseudonymized private
context are separate system messages. The CLI prints exact model speech and
writes append-only provenance receipts; it does not execute speech as commands.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATE_ROOT = Path(os.path.expanduser(os.environ.get("HC_STATE_DIR", "~/.local/state/home-center"))) / "she-raw-cli"
CONFIG_PATH = ROOT / "config" / "she-raw-cli.v1.json"
JAR_CACHE_PATH = ROOT / "config" / "she-raw-jar-cache.md"
DEFAULT_URL = os.environ.get("HC_SHE_RAW_LLM_URL", os.environ.get("HC_PHONE_LLM_URL", "http://127.0.0.1:8790/v1/chat/completions"))
DEFAULT_MODEL = os.environ.get("HC_SHE_RAW_MODEL", os.environ.get("HC_PHONE_LLM_MODEL", "local-phone"))
PRIVATE_CONTEXT = Path(os.path.expanduser(os.environ.get("HC_SHE_RAW_PRIVATE_CONTEXT", str(ROOT / "MEMORIES.md"))))
ALIAS_PATH = Path(os.path.expanduser(os.environ.get("HC_SHE_RAW_ALIASES", "~/.config/home-center/she-raw-aliases.json")))
MAX_PRIVATE_CHARS = int(os.environ.get("HC_SHE_RAW_PRIVATE_CONTEXT_MAX", "16000"))


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_config() -> dict:
    if not CONFIG_PATH.is_file():
        raise RuntimeError(f"character canon cache missing: {CONFIG_PATH}")
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def require_loopback(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError("local-only boundary: She Raw endpoint must be loopback")


def load_aliases() -> dict[str, str]:
    if not ALIAS_PATH.is_file():
        return {}
    value = json.loads(ALIAS_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in value.items()):
        raise RuntimeError(f"alias map must be a JSON string-to-string object: {ALIAS_PATH}")
    return {k: v for k, v in value.items() if k and v and k != v}


def pseudonymize(text: str, aliases: dict[str, str]) -> str:
    # Longest first prevents a short name from damaging a longer one.
    for source in sorted(aliases, key=len, reverse=True):
        text = re.sub(rf"(?<!\w){re.escape(source)}(?!\w)", aliases[source], text, flags=re.IGNORECASE)
    return text


def private_context() -> tuple[str, dict]:
    if not PRIVATE_CONTEXT.is_file():
        return "", {"loaded": False, "path": str(PRIVATE_CONTEXT), "reason": "missing"}
    aliases = load_aliases()
    raw = PRIVATE_CONTEXT.read_text(encoding="utf-8", errors="replace")[:MAX_PRIVATE_CHARS]
    if raw.strip() and not aliases:
        return "", {"loaded": False, "path": str(PRIVATE_CONTEXT), "reason": "alias_map_required"}
    rendered = pseudonymize(raw, aliases)
    return rendered, {
        "loaded": bool(rendered.strip()),
        "path": str(PRIVATE_CONTEXT),
        "sourceSha256": sha256(raw),
        "renderedSha256": sha256(rendered),
        "aliasCount": len(aliases),
        "bytesLeaveDevice": False,
    }


def system_messages(config: dict) -> tuple[list[dict], dict]:
    canon = str(config["systemPrompt"])
    if not JAR_CACHE_PATH.is_file():
        raise RuntimeError(f"She Raw Judgment Jar cache missing: {JAR_CACHE_PATH}")
    jar = JAR_CACHE_PATH.read_text(encoding="utf-8", errors="replace")
    private, private_meta = private_context()
    messages = [
        {"role": "system", "content": canon},
        {"role": "system", "content": "BINDING SHE RAW JUDGMENT JAR (bounded offline cache; source metadata preserved):\n\n" + jar},
    ]
    if private:
        messages.append({
            "role": "system",
            "content": "PRIVATE-LIFE CONTEXT, PSEUDONYMIZED LOCALLY. Treat aliases as the only names. Use this as lived context, never expose source names or claim ownership of the people described.\n\n" + private,
        })
    return messages, {"canonSha256": sha256(canon), "judgmentJarSha256": sha256(jar), "judgmentJarPath": str(JAR_CACHE_PATH), "privateContext": private_meta}


def call_local(messages: list[dict], url: str, model: str, timeout: int) -> tuple[str, dict]:
    require_loopback(url)
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": 0.82,
        "max_tokens": 1400,
    }, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise RuntimeError(f"local She Raw model unavailable: {exc}") from exc
    try:
        message = body["choices"][0]["message"]
        speech = message.get("content") or message.get("reasoning_content")
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("local She Raw model returned no assistant message") from exc
    if not isinstance(speech, str) or not speech.strip():
        raise RuntimeError("local She Raw model returned empty speech")
    return speech, {
        "source": "local-model-character-runtime",
        "endpoint": url,
        "model": model,
        "elapsedMs": int((time.time() - started) * 1000),
        "cloudFallback": False,
        "transformedByCli": False,
    }


def append_receipt(session_id: str, receipt: dict) -> Path:
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    path = STATE_ROOT / f"session-{session_id}.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(receipt, ensure_ascii=False, sort_keys=True) + "\n")
    latest = STATE_ROOT / "latest.json"
    temp = latest.with_suffix(".tmp")
    temp.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(latest)
    return path


def turn(text: str, history: list[dict], args, session_id: str, config: dict) -> str:
    if not text.strip():
        raise RuntimeError("empty message")
    prefix, context_meta = system_messages(config)
    user_message = {"role": "user", "content": text}
    speech, provenance = call_local(prefix + history + [user_message], args.url, args.model, args.timeout)
    # The exact user string and exact model string are independently hashed.
    receipt = {
        "schema": "home-center.adam-she-raw-turn.v1",
        "sessionId": session_id,
        "createdAtEpoch": int(time.time()),
        "character": "She Raw",
        "canonSource": config["canonSource"],
        "user": {"sha256": sha256(text), "bytes": len(text.encode("utf-8")), "transformedByCli": False},
        "speech": {"sha256": sha256(speech), "bytes": len(speech.encode("utf-8")), **provenance},
        "context": context_meta,
    }
    receipt_path = append_receipt(session_id, receipt)
    history.extend([user_message, {"role": "assistant", "content": speech}])
    if args.json:
        print(json.dumps({"ok": True, "speech": speech, "receipt": receipt, "receiptPath": str(receipt_path)}, ensure_ascii=False))
    else:
        sys.stdout.write(speech)
        sys.stdout.flush()
        print(f"\n[local {args.model}; speech sha256 {receipt['speech']['sha256'][:12]}; receipt {receipt_path}]", file=sys.stderr)
    return speech


def doctor(args, config: dict) -> int:
    report = {
        "schema": "home-center.adam-she-raw-doctor.v1",
        "ready": False,
        "endpoint": args.url,
        "model": args.model,
        "canon": {"ok": CONFIG_PATH.is_file(), "path": str(CONFIG_PATH), "source": config.get("canonSource")},
        "judgmentJar": {"ok": JAR_CACHE_PATH.is_file(), "path": str(JAR_CACHE_PATH)},
        "privateContext": private_context()[1],
        "cloudFallback": False,
        "applicationContentFilter": False,
        "speechExecutesCommands": False,
    }
    try:
        require_loopback(args.url)
        request = urllib.request.Request(args.url, data=json.dumps({"model": args.model, "messages": [{"role": "user", "content": "Return exactly: SHE_RAW_LOCAL_OK"}], "max_tokens": 16}).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=min(args.timeout, 20)) as response:
            report["endpointStatus"] = response.status
        report["ready"] = report["endpointStatus"] == 200 and report["canon"]["ok"] and report["judgmentJar"]["ok"]
    except Exception as exc:
        report["error"] = str(exc)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ready"] else 3


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="adam she-raw", description="direct phone-local She Raw conversation")
    parser.add_argument("message", nargs="*", help="one-shot message; omit for REPL")
    parser.add_argument("--json", action="store_true", help="return speech plus provenance envelope")
    parser.add_argument("--doctor", action="store_true", help="check local character runtime")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args(argv)
    config = load_config()
    if args.doctor:
        return doctor(args, config)
    session_id = uuid.uuid4().hex
    history: list[dict] = []
    one_shot = " ".join(args.message)
    if one_shot:
        turn(one_shot, history, args, session_id, config)
        return 0
    print("She Raw local. /quit exits; /status prints provenance. Speech is never executed.")
    while True:
        try:
            text = input("drew> ")
        except EOFError:
            print()
            return 0
        except KeyboardInterrupt:
            print("\n^C")
            continue
        if text.strip() in {"/quit", "/exit"}:
            return 0
        if text.strip() == "/status":
            print(json.dumps({"sessionId": session_id, "turns": len(history) // 2, "model": args.model, "endpoint": args.url, "cloudFallback": False}, indent=2))
            continue
        if text:
            try:
                turn(text, history, args, session_id, config)
                if not args.json:
                    print()
            except Exception as exc:
                print(f"BLOCKED: {exc}", file=sys.stderr)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        raise SystemExit(3)
