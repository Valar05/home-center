#!/usr/bin/env python3
"""Deterministic ceremonial score generator with reproducible receipts.

Examples:
  python3 tools/absurd_score_receipt.py --subject "Punch Level Design meme" --namespace imagegen
  python3 tools/absurd_score_receipt.py --subject "Sock theology" --namespace ministry --profile casino_nuclear
  python3 tools/absurd_score_receipt.py --subject "Punch Level Design meme" --namespace imagegen --score 567768 --origin user_assigned_legacy
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable

SCORER_VERSION = "absurd-score-rng.v1"
STREAM_DOMAIN = b"absurd-score-sha256-counter-v1\0"
SEED_DOMAIN = b"absurd-score-seed-v1\0"
RECEIPT_DOMAIN = b"absurd-score-receipt-v1\0"


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFC", str(value))
    return re.sub(r"\s+", " ", value.strip())


def canonical_json_bytes(payload: dict) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def resolve_profile(namespace: str, profile: str) -> str:
    if profile != "auto":
        return profile
    ns = normalize_text(namespace).lower().replace("-", "_").replace(" ", "_")
    if ns in {"image", "imagegen", "image_gen", "meme", "imogen"}:
        return "imagegen"
    if ns in {"ministry", "casino", "ridiculous_prompt", "ridiculous_prompts", "ministry_of_scoring"}:
        return "casino_nuclear"
    return "standard"


@dataclass
class HashStream:
    seed_digest: bytes
    counter: int = 0
    buffer: bytes = b""

    def _refill(self) -> None:
        block = hashlib.sha256(
            STREAM_DOMAIN + self.seed_digest + self.counter.to_bytes(8, "big")
        ).digest()
        self.counter += 1
        self.buffer += block

    def take(self, count: int) -> bytes:
        while len(self.buffer) < count:
            self._refill()
        out, self.buffer = self.buffer[:count], self.buffer[count:]
        return out

    def randbelow(self, n: int) -> int:
        if n <= 0:
            raise ValueError("n must be positive")
        width = max(1, (n.bit_length() + 7) // 8)
        ceiling = 1 << (width * 8)
        limit = ceiling - (ceiling % n)
        while True:
            value = int.from_bytes(self.take(width), "big")
            if value < limit:
                return value % n


def comma_group(decimal_text: str) -> str:
    chunks = []
    text = decimal_text
    while text:
        chunks.append(text[-3:])
        text = text[:-3]
    return ",".join(reversed(chunks))


def abbreviated_display(decimal_text: str) -> str:
    if len(decimal_text) <= 30:
        return comma_group(decimal_text)
    mantissa = f"{decimal_text[0]}.{decimal_text[1:13]}"
    return f"{mantissa} × 10^{len(decimal_text) - 1}"


def generated_score(profile: str, stream: HashStream) -> str:
    if profile == "imagegen":
        return str(100_000 + stream.randbelow(900_000))
    if profile == "standard":
        return str(10_000 + stream.randbelow(999_990_000))
    if profile == "casino_nuclear":
        digits = 96 + stream.randbelow(129)  # 96..224 digits
        first = str(1 + stream.randbelow(9))
        rest = "".join(str(stream.randbelow(10)) for _ in range(digits - 1))
        return first + rest
    raise ValueError(f"unknown profile: {profile}")


def canonical_request(*, subject: str, namespace: str, profile: str, edition: str) -> dict:
    return {
        "scorer_version": SCORER_VERSION,
        "subject": normalize_text(subject),
        "namespace": normalize_text(namespace).lower(),
        "profile": resolve_profile(namespace, profile),
        "edition": normalize_text(edition),
    }


def make_receipt(
    *,
    subject: str,
    namespace: str = "absurd",
    profile: str = "auto",
    edition: str = "1",
    score: str | None = None,
    origin: str | None = None,
    issued_at: str | None = None,
    actor: str = "Ritsu",
) -> dict:
    request = canonical_request(
        subject=subject,
        namespace=namespace,
        profile=profile,
        edition=edition,
    )
    canonical = canonical_json_bytes(request)
    request_sha = hashlib.sha256(canonical).hexdigest()
    seed_digest = hashlib.sha256(SEED_DOMAIN + canonical).digest()
    seed_sha = seed_digest.hex()
    stream = HashStream(seed_digest)

    if score is None:
        score_decimal = generated_score(request["profile"], stream)
        score_origin = origin or "deterministic_rng"
        if score_origin != "deterministic_rng":
            raise ValueError("generated scores must use origin=deterministic_rng")
    else:
        raw = str(score).replace(",", "").strip()
        if not re.fullmatch(r"[0-9]+", raw):
            raise ValueError("manual score must be a non-negative decimal integer")
        score_decimal = raw.lstrip("0") or "0"
        score_origin = origin or "external_manual"
        if score_origin == "deterministic_rng":
            raise ValueError("manual score cannot claim deterministic_rng origin")

    identity_payload = {
        "request": request,
        "score_decimal": score_decimal,
        "score_origin": score_origin,
        "algorithm": "sha256-counter-v1",
    }
    receipt_digest = hashlib.sha256(
        RECEIPT_DOMAIN + canonical_json_bytes(identity_payload)
    ).hexdigest()
    receipt_id = f"ASR-{receipt_digest[:16]}"

    return {
        "schema": "absurd-score.receipt.v1",
        "receipt_id": receipt_id,
        "scorer_version": SCORER_VERSION,
        "actor": normalize_text(actor),
        "issued_at": issued_at,
        "subject": request["subject"],
        "namespace": request["namespace"],
        "profile": request["profile"],
        "edition": request["edition"],
        "score_origin": score_origin,
        "score": {
            "decimal": score_decimal,
            "display": abbreviated_display(score_decimal),
            "digits": len(score_decimal),
        },
        "canonical_request_sha256": request_sha,
        "rng_seed_sha256": seed_sha,
        "rng_algorithm": "sha256-counter-v1",
        "score_entropy_excludes": [
            "wall_clock_time",
            "process_randomness",
            "python_hash",
            "machine_identity",
            "network_state",
            "model_choice",
        ],
        "ceremonial": True,
        "quality_metric": False,
        "meaning": "absurd ceremonial score; not objective quality evidence",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--namespace", default="absurd")
    parser.add_argument(
        "--profile",
        choices=("auto", "standard", "imagegen", "casino_nuclear"),
        default="auto",
    )
    parser.add_argument("--edition", default="1")
    parser.add_argument("--score", help="preserve an externally/manual assigned decimal score")
    parser.add_argument("--origin")
    parser.add_argument("--issued-at")
    parser.add_argument("--actor", default="Ritsu")
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    receipt = make_receipt(
        subject=args.subject,
        namespace=args.namespace,
        profile=args.profile,
        edition=args.edition,
        score=args.score,
        origin=args.origin,
        issued_at=args.issued_at,
        actor=args.actor,
    )
    if args.pretty:
        print(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        print(json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
