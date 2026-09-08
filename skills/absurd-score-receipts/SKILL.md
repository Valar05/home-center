# Absurd Score Receipts — Deterministic Ceremonial RNG

## Status
ACTIVE / GLOBAL SCORING ROUTER

## Authority
Drew commission — 2026-09-08.

## Purpose
Every absurd, ceremonial, Ministry, meme, prompt, Imagegen, casino, or otherwise intentionally ridiculous score must be reproducible and receipted instead of being improvised as an untraceable number.

## Core law

**NO ABSURD SCORE WITHOUT A RECEIPT. NO HIDDEN REROLLS.**

The joke may be arbitrary. The arbitrary must be deterministic.

## Automatic trigger
Load this skill whenever the assistant is about to assign a deliberately absurd or ceremonial numeric score, including:

- `Imagegen score`;
- `meme score`;
- `prompt score`;
- `absurdity score`;
- Ministry of Scoring / Ministry of Ridiculous Prompts scoring;
- casino-style impossible totals;
- a deliberately nonsensical numerical rating used as comedy;
- any recurring score whose exact number should survive the chat that created it.

Do not wait for Drew to ask for a receipt again.

This skill does **not** replace real measurements, benchmark results, probabilities, financial values, medical values, test scores, or evidence-based ratings. Absurd-score RNG is explicitly ceremonial.

## Punch-Card compilation

**STATE + INPUT + RULE → NEXT STATE + OBSERVABLE**

- **STATE:** canonical subject, namespace, profile, edition, scorer version.
- **INPUT:** request to issue an absurd ceremonial score.
- **RULE:** canonicalize → SHA-256 seed → deterministic SHA-256 counter stream → profile-specific score.
- **NEXT STATE:** exact score and stable receipt identity exist.
- **OBSERVABLE:** the same canonical request reproduces the same exact score and receipt ID.
- **CORRECTION:** a user-supplied historical score is preserved as manual/external provenance and is never falsely relabeled as RNG output.

## Canonical scorer

`python3 tools/absurd_score_receipt.py --subject <text> [--namespace <name>] [--profile <profile>] [--edition <text>]`

The scorer is dependency-free and uses a SHA-256 counter stream. It must not use:

- wall-clock time as score entropy;
- `random.Random`;
- process randomness;
- Python `hash()`;
- machine identity;
- network state;
- hidden model choice.

Timestamp may be recorded on the event receipt, but it never affects the score.

## Profiles

### `standard`
Compact absurd score for ordinary jokes and ratings. Large enough to be silly without consuming the page.

### `imagegen`
Six-digit score profile, preserving the visual family established by the human-issued `567,768` Imagegen score.

### `casino_nuclear`
A deterministic 96–224 digit integer for Ministry / casino / maximum-number nonsense. The exact integer lives in the receipt even when chat uses a shortened display.

### `auto`
Profile is selected from namespace:

- image/imagegen/meme → `imagegen`;
- ministry/casino/ridiculous_prompt → `casino_nuclear`;
- otherwise → `standard`.

The selected profile is always written into the receipt.

## Canonical request identity
The RNG seed is SHA-256 over canonical UTF-8 JSON containing:

- scorer version;
- normalized subject;
- normalized namespace;
- resolved profile;
- explicit edition.

Normalization uses Unicode NFC, trims outer whitespace, and collapses internal whitespace runs.

The default edition is `1`.

## Reroll law
The same canonical request must yield the same score forever under the same scorer version.

If a genuinely new roll is wanted, change `edition` explicitly. Example: `edition=2`.

A new edition is not a secret reroll. The receipt exposes it.

**SAME CARD, SAME NUMBER. NEW NUMBER, NEW CARD.**

## Receipt contract
Each score receipt records at least:

- schema and scorer version;
- stable receipt ID;
- subject;
- namespace;
- resolved profile;
- edition;
- score origin;
- exact decimal score;
- display score;
- digit count;
- canonical request SHA-256;
- RNG seed SHA-256;
- algorithm identity;
- optional issued-at timestamp;
- actor;
- explicit statement that the score is ceremonial and not a quality metric.

Canonical repository path when persistence is available:

`receipts/absurd-scores/<receipt_id>.json`

Do not maintain a second watcher or receipt daemon for this. Repository receipts are the durable score artifacts. Existing Home Center/Judgment-Jar receipt transport remains separate machinery.

## Chat display contract
Whenever an assistant-origin absurd score is given, show at minimum:

`<score display> · receipt <receipt_id>`

The full exact score and seed live in the receipt.

For `casino_nuclear`, chat may abbreviate the huge integer, but the exact decimal integer must remain in the receipt.

## Human-issued and historical scores
If Drew supplies the score himself, preserve it exactly.

Use:

`python3 tools/absurd_score_receipt.py --subject <text> --score <decimal> --origin user_assigned_legacy ...`

The receipt must say that the score was externally/manual assigned. The deterministic engine may supply identity/provenance, but must never pretend it generated the historical number.

Canonical grandfathered fixture:

- Subject: Imogen / Imagegen `Punch Level Design` meme result.
- Human-issued score: `567,768`.
- Origin: `user_assigned_legacy`.

## Failure conditions
Reject the scoring pass if:

- an assistant invents the absurd number freehand;
- a score is issued with no receipt ID;
- the same canonical request silently changes score;
- time/date is used as hidden entropy;
- a manual historical score is rewritten as RNG output;
- a ceremonial RNG number is presented as objective quality evidence;
- a huge score is abbreviated in the receipt rather than preserving the exact integer;
- a new scoring architecture duplicates existing receipt daemons or claims false Home Center delivery.

## Compact law

**NO ABSURD SCORE WITHOUT A RECEIPT. SAME CARD, SAME NUMBER. NEW NUMBER, NEW CARD.**
