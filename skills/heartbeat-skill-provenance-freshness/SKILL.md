# Heartbeat Skill Provenance Freshness

## Purpose

Make `repository_skill` heartbeat lights prove that the named skill exists in the **current repository tree**. Generated indexes, cached matchers, old receipts, or label-shaped strings may help discovery, but they are never sufficient provenance by themselves.

This skill is source/evidence infrastructure. It owns no overlay controller, renderer, scheduler, phone lane, P0 recovery chain, deployment, or physical acceptance.

## Authority order

For a light whose `provenanceKind` is `repository_skill`:

1. Resolve an actual current-tree `skills/**/SKILL.md` path.
2. Read the bounded UTF-8 title throat first. A malformed or title-resource-over-budget file is rejected before whole-file hashing.
3. Hash the **entire** admitted file with SHA-256 only when EOF is reached inside the whole-skill hash byte budget. A prefix digest is never authority.
4. Bracket direct skill discovery with repository observations before and after the scan. Current-tree authority requires the same available git HEAD and a clean checkout at both observations.
5. Preserve repository head, pre/post cleanliness, snapshot verdict, title admission, and exact whole-file hash as distinct evidence.
6. Treat generated indexes only as discovery aids unless they independently pass the generated-index freshness gate.
7. Even `VERIFIED_CURRENT` generated-index evidence never replaces direct current-tree skill existence.

A single pre-scan `git status` is not a stable provenance snapshot. If HEAD moves, cleanliness becomes unavailable, or the checkout is dirty before/after discovery, classify the repository snapshot `UNSTABLE`. Discovered records may remain diagnostic, but they do not earn current repository-skill authority for that probe report.

If direct current-tree resolution fails, keep the light dark or use the correct `doctrine`, `jar`, `reviewer`, or `runtime_boundary` provenance kind. Never promote a familiar label into `repository_skill` by vibes.

## Per-file failure isolation

One damaged `SKILL.md` must not erase unrelated healthy evidence. Each candidate file is independent after path-identity checks:

- malformed UTF-8 or title-resource failure becomes a bounded `stage=title` discovery error and stops before whole-file hash work;
- title-read I/O failure is isolated the same way;
- whole-file hash I/O failure becomes a bounded `stage=hash` discovery error;
- whole-file hash resource overflow becomes `SkillHashResourceLimitError`, omits that skill, and returns no prefix SHA;
- missing skill roots, path escapes, and case-insensitive identity collisions use the same structured error envelope;
- discovery continues deterministically through healthy peers;
- raw exception prose and hostile file contents are never copied into operator-facing reasons;
- error-path projection is hard-bounded and carries a short digest suffix when shortened;
- `--strict` still fails on any discovery error. Isolation means “finish the evidence report,” not “declare the wounded skill healthy.”

The probe report schema is `try-forever-skill-provenance.v2`. Discovery-error fields are `path`, `stage`, `error_type`, `reason`, optional diagnostic `sha256`, and optional `related_path`. They are evidence fields, not a TalkBack script.

## Title extraction resource throat

A valid UTF-8 file can still be hostile if title extraction scans or allocates without bounds. The canonical probe therefore:

- scans at most `MAX_SKILL_TITLE_SCAN_BYTES = 64 KiB` for the first Markdown H1;
- reads at most `MAX_SKILL_TITLE_LINE_BYTES = 8 KiB` for one candidate line;
- admits at most `MAX_SKILL_TITLE_CHARS = 256` Unicode code points as the H1 title;
- decodes only a line already proven inside the byte budget;
- rejects line/scan/title overflow with `SkillTitleResourceLimitError`;
- never truncates hostile source into a plausible repository identity;
- never skips an oversized preamble to bless a later H1;
- preserves folder-name fallback only for titleless files that complete inside the scan budget.

Because title admission now precedes whole-file hashing, title-stage failure normally has no diagnostic whole-file SHA. That absence is intentional: do not pay later provenance work after an earlier admission gate already failed.

## Whole-skill hash resource throat

Chunk-bounded memory is not a bounded workload. A giant `SKILL.md` can still force unbounded total I/O if the probe hashes to EOF without a declared file budget. The canonical probe therefore also enforces:

- `MAX_SKILL_HASH_BYTES = 1 MiB` total file bytes eligible for repository-skill hashing;
- `SKILL_HASH_CHUNK_BYTES = 64 KiB` maximum normal read chunk;
- an exact-max file must still reach EOF and receives the SHA of its complete bytes;
- the probe performs one bounded look-ahead byte at the limit to distinguish exact-max EOF from max+1;
- max+1 rejects with `SkillHashResourceLimitError` and returns **no prefix digest**;
- a valid short title plus an oversized body is a `stage=hash` discovery error;
- healthy peer skills continue discovery;
- title admission runs before the whole-file hash so malformed/title-resource wounds terminate before unnecessary full-file work.

This limit is source-provenance policy, not speech truncation and not a generated-index limit. Increasing it later requires an explicit policy change; silently hashing a prefix or normalizing a giant file into authority is forbidden.

## Generated-index freshness gate

A generated/cached skill index may be `VERIFIED_CURRENT` only when all of these hold:

- direct repository snapshot is `STABLE_CLEAN` across the skill scan;
- git HEAD exists and is unchanged;
- checkout cleanliness is available and clean before and after discovery;
- index declares the exact same source HEAD;
- index explicitly declares a clean source tree;
- generation timestamp is parseable, not implausibly future, and inside the configured freshness window.

Otherwise fail closed:

- `STALE` for known mismatch such as foreign HEAD, declared dirty source, or excess age;
- `UNRESOLVED` when required proof is missing or ambiguous, including unstable checkout, missing cleanliness/source HEAD/timestamp, unreadable JSON, or implausible future time.

A current index is still only discovery evidence. It never substitutes for the current `SKILL.md` record.

## Canonical probe

Use `tools/try_forever_skill_provenance_probe.py`.

The probe is standard-library source and performs no network calls. It captures pre/post HEAD and cleanliness, recursively discovers `skills/**/SKILL.md`, isolates per-file wounds, validates the bounded title throat before bounded full-file SHA, fails closed on case-insensitive path collisions, classifies an optional generated index, supports `--expected-head` and `--strict`, and emits capability truth from the executing process.

A probe file existing in GitHub is **IMPLEMENTED SOURCE**. A regression file existing in GitHub is **REGRESSION SOURCE**. Neither means execution occurred. Only output from an authorized invocation can prove `probe executed`; only an authorized test receipt can promote regression source to `TESTED`.

## Regression source

`tools/test_try_forever_skill_provenance_probe.py` pins:

- direct current-tree discovery and exact SHA;
- malformed UTF-8 rejection before whole-file hash;
- deterministic per-file hash I/O isolation without raw exception leakage;
- exact-max whole-file hash acceptance;
- max+1 whole-file hash rejection with no prefix authority;
- title rejection occurring before hash invocation;
- short-title/oversized-body hash rejection while a healthy peer survives;
- hard-bounded discovery-error paths;
- stable/unstable pre/post repository snapshots;
- emitted process capability truth;
- generated-index resolution, freshness, dirty/missing state, foreign HEAD, stale age, and future timestamp behavior.

`tools/test_try_forever_skill_title_resource_budget.py` separately pins the title throat: exact-max H1, max+1 H1, oversized first line, total scan exhaustion, malformed UTF-8 classification, healthy-peer survival, and bounded folder fallback.

Keep test imports independent of caller working directory. Test source is not test execution.

## Heartbeat consequence

This skill lights only when it changes provenance truth: for example, a stale matcher is demoted, a moving checkout is blocked from authority, a malformed or oversized skill is isolated, an unbounded title/hash workload gains an explicit throat, or a current path/hash is proven under a stable clean bracket. It stays dark when no repository-skill provenance work occurred.

## Capability membrane

Preserve independently:

`requested -> implemented source -> exact repository readback -> probe executed -> regression tested -> runtime UI consumed -> deployed -> callable -> executed -> delivered -> accepted`

No earlier state implies a later one. In particular:

- current-tree skill evidence does not prove Android rendering;
- stable checkout does not make a malformed/resource-over-budget skill valid;
- exact-max source acceptance does not prove a runner executed the probe;
- regression source does not mean TESTED;
- repository provenance does not clear Phone Runtime / Phone Hands / P0 gates;
- GitHub source progress is not phone delivery or physical acceptance.

## P0 and duplicate-architecture firewall

This skill may inspect repository/source provenance only. It must not wake, retask, queue, replace, or coordinate Phone Hands, Phone Ingress, Nightcore, Pocket TTS, Chromium, Context Organs, P0 recovery, or their physical acceptance chain. It must not create a neighboring overlay controller, skill registry daemon, scheduler, provenance probe, or deployment path.

If provenance work exposes a P0 defect, preserve one concise finding for the canonical P0 owner and stop there.

## Done

A provenance pulse can close only when it can name the exact current-tree skill path/hash or structured admission failure, pre/post repository snapshot truth, generated-index verdict when used, whether the probe merely exists or actually ran, the exact capability state reached, and the fact that no later runtime/phone state was inferred without evidence.
