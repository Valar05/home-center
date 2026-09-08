#!/usr/bin/env python3
"""Regression contract for deterministic absurd-score receipts."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from absurd_score_receipt import make_receipt  # noqa: E402

SKILL = (ROOT / "skills/absurd-score-receipts/SKILL.md").read_text(encoding="utf-8")
CORE = (ROOT / "skills/fortress-core/SKILL.md").read_text(encoding="utf-8")
RITSU = (ROOT / "skills/haraway-hotel-operator/SKILL.md").read_text(encoding="utf-8")

for needle in [
    "NO ABSURD SCORE WITHOUT A RECEIPT. NO HIDDEN REROLLS.",
    "SAME CARD, SAME NUMBER. NEW NUMBER, NEW CARD.",
    "sha256-counter-v1",
    "casino_nuclear",
    "user_assigned_legacy",
    "567,768",
]:
    assert needle in SKILL, f"absurd-score skill missing invariant: {needle}"

for text, label in [(CORE, "Fortress Core"), (RITSU, "Ritsu")]:
    assert "skills/absurd-score-receipts/SKILL.md" in text, f"{label} does not route absurd scoring"

base = dict(
    subject="Punch Level Design meme",
    namespace="imagegen",
    profile="auto",
    edition="1",
    actor="Ritsu",
)
a = make_receipt(**base, issued_at="2026-09-08T03:00:00-05:00")
b = make_receipt(**base, issued_at="2099-01-01T00:00:00+00:00")
assert a["score"] == b["score"], "timestamp changed deterministic score"
assert a["receipt_id"] == b["receipt_id"], "timestamp changed receipt identity"
assert a["rng_seed_sha256"] == b["rng_seed_sha256"], "timestamp changed RNG seed"
assert a["profile"] == "imagegen"
assert len(a["score"]["decimal"]) == 6
assert a["score_origin"] == "deterministic_rng"
assert a["ceremonial"] is True and a["quality_metric"] is False

edition2 = make_receipt(**{**base, "edition": "2"})
assert edition2["receipt_id"] != a["receipt_id"], "explicit new edition did not change receipt identity"
assert edition2["rng_seed_sha256"] != a["rng_seed_sha256"], "explicit new edition did not change seed"

nuclear = make_receipt(
    subject="Spiritual sock argument with a drill instructor",
    namespace="ministry",
    profile="auto",
)
assert nuclear["profile"] == "casino_nuclear"
assert 96 <= nuclear["score"]["digits"] <= 224
assert nuclear["score"]["decimal"].isdigit()
assert "× 10^" in nuclear["score"]["display"]

manual = make_receipt(
    subject="Imogen Punch Level Design meme result",
    namespace="imagegen",
    profile="imagegen",
    score="567,768",
    origin="user_assigned_legacy",
    issued_at="2026-09-08T03:27:02-05:00",
    actor="Drew",
)
assert manual["score"]["decimal"] == "567768"
assert manual["score"]["display"] == "567,768"
assert manual["score_origin"] == "user_assigned_legacy"
assert manual["quality_metric"] is False

print("ABSURD SCORE RECEIPT CONTRACT PASS")
