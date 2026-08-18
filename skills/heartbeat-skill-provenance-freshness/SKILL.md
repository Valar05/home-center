# Heartbeat Skill Provenance Freshness

## Purpose

Make `repository_skill` heartbeat lights prove that the named skill exists in the **current repository tree**. Generated indexes, cached matchers, old receipts, or label-shaped strings may help discover candidates, but they are never sufficient provenance by themselves.

This skill is deliberately source/evidence infrastructure. It owns no overlay controller, renderer, scheduler, phone lane, P0 recovery chain, deployment, or physical acceptance.

## Authority order

For a light whose `provenanceKind` is `repository_skill`:

1. Resolve an actual current-tree `skills/**/SKILL.md` path.
2. Hash the exact current file bytes with SHA-256.
3. Decode the skill as UTF-8 and derive its H1 title without rewriting malformed source into replacement text.
4. Bracket direct skill discovery with repository observations **before and after** the scan. Current-tree authority requires the same available git HEAD and a clean checkout at both observations.
5. Preserve the current repository head, pre/post cleanliness, and snapshot-stability verdict separately from the skill hash.
6. Treat generated indexes only as discovery aids unless they independently pass the generated-index freshness gate below.
7. Even a `VERIFIED_CURRENT` generated index does **not** replace direct current-tree skill existence. It only proves that the index itself may be trusted as current discovery evidence.

A single pre-scan `git status` is not a stable provenance snapshot. If HEAD moves, cleanliness becomes unavailable, or the checkout is dirty before/after discovery, classify the repository snapshot `UNSTABLE`. The discovered paths/hashes may remain diagnostic data, but they may not earn current repository-skill authority for that probe report.

If direct current-tree resolution fails, the light may remain dark or use the correct `doctrine`, `jar`, `reviewer`, or `runtime_boundary` provenance kind when that is what actually exists. Never promote a familiar label into `repository_skill` by vibes.

## Per-file discovery failure isolation

One damaged `SKILL.md` must not erase evidence from every unrelated healthy skill. Direct discovery therefore treats each skill file as an independent provenance record after path-identity checks:

- an I/O failure while hashing becomes a structured `discoveryErrors` record and that skill is omitted;
- malformed UTF-8 while reading the title becomes a structured `discoveryErrors` record; the already-computed byte SHA may remain diagnostic, but the malformed skill does not earn `repository_skill` authority;
- a later title-read I/O failure is isolated the same way;
- discovery continues deterministically through the remaining skill files;
- raw exception prose and hostile file contents are not copied into operator-facing error reasons;
- the error path projection is hard-bounded and carries a short digest suffix if truncation is required;
- `--strict` still fails when any discovery error exists. Isolation means “finish the report,” not “declare the broken skill healthy.”

A report may therefore contain a `STABLE_CLEAN` repository snapshot **and** one or more structured per-file discovery errors. Those statements answer different questions: the checkout stayed stable, but some candidate skill files could not be admitted as valid skill records.

Current structured per-file fields are `path`, `stage`, `error_type`, `reason`, and optional diagnostic `sha256`. They are evidence fields, not a TalkBack script and not permission to surface raw filesystem exception text.

## Generated-index freshness gate

A generated/cached skill index may be classified `VERIFIED_CURRENT` only when all of these hold:

- the direct repository snapshot is `STABLE_CLEAN` across the skill scan;
- current git HEAD is available and unchanged across that scan;
- current checkout cleanliness is available and clean before and after that scan;
- the index declares the exact same source HEAD;
- the index explicitly declares that its source tree was clean;
- its generation timestamp is parseable;
- it is no older than the configured freshness window (default 14 days);
- it is not implausibly in the future.

Otherwise classify it fail-closed:

- `STALE` when a known index mismatch exists, such as foreign HEAD, declared dirty source, or age beyond the freshness window;
- `UNRESOLVED` when required proof is missing or ambiguous, including an unstable current repository snapshot, unavailable checkout cleanliness, missing source HEAD, missing clean-tree declaration, unreadable JSON, missing timestamp, or an implausible future timestamp.

`STALE` and `UNRESOLVED` indexes may suggest where to look. They may not earn an active repository-skill light.

## Canonical probe

Use:

`tools/try_forever_skill_provenance_probe.py`

The probe is standard-library source and performs no network calls. It:

- captures git HEAD and checkout cleanliness before direct skill discovery;
- discovers current `skills/**/SKILL.md` files recursively;
- records repository-relative path, H1 title, and exact SHA-256 for admitted records;
- isolates unreadable/malformed individual skill files as bounded structured discovery errors instead of aborting the entire report;
- captures git HEAD and checkout cleanliness again after discovery;
- grants direct current-tree authority only to a `STABLE_CLEAN` bracketed snapshot;
- fails closed on case-insensitive current-tree path collisions;
- classifies an optional generated index as `VERIFIED_CURRENT`, `STALE`, or `UNRESOLVED`;
- supports `--expected-head` and `--strict`; strict mode rejects an unstable repository snapshot or any discovery error;
- emits execution capability truth from the executing process: an emitted report may say `probeExecutedByThisProcess=true`, while the mere source file existing in GitHub remains only **IMPLEMENTED SOURCE**.

A probe file existing in GitHub is **IMPLEMENTED SOURCE**. A regression file existing in GitHub is **REGRESSION SOURCE**. Neither means the probe or tests have executed. Only output from an authorized invocation can prove `probe executed`; only an authorized test receipt may promote regression source to `TESTED`.

## Regression source

`tools/test_try_forever_skill_provenance_probe.py` pins hostile cases including:

- direct current-tree skill discovery and hashing;
- malformed UTF-8 in one skill becoming a structured error while a healthy peer remains discoverable;
- deterministic per-file hash I/O failure isolation without leaking raw exception prose;
- hard-bounded discovery-error path projection;
- stable clean pre/post repository snapshot;
- HEAD movement during discovery;
- dirty or unavailable post-discovery cleanliness;
- emitted report execution-boundary truth;
- repository-relative generated-index resolution;
- matching clean/fresh index;
- foreign source HEAD;
- dirty index source;
- dirty or unknown current checkout cleanliness;
- stale generation age;
- implausible future timestamps;
- missing clean-tree declaration.

Keep the test import independent of caller working directory so a future runner does not accidentally test Python path luck instead of the probe contract.

## Heartbeat consequence

This skill materially lights when it changes provenance truth: for example, a previously trusted generated matcher is demoted to discovery-only, a current skill path/hash is proven under a stable clean bracket, a moving checkout is prevented from impersonating a current snapshot, one malformed skill is isolated without erasing healthy discoveries, or ambiguous provenance is prevented from becoming an active repository-skill light.

It stays dark when the pulse did not need repository-skill provenance work. Do not list it merely because it exists.

## Capability membrane

Preserve these states independently:

`requested -> implemented source -> exact repository readback -> probe executed -> regression tested -> runtime UI consumed -> deployed -> callable -> executed -> delivered -> accepted`

No earlier state implies a later one. In particular:

- repository skill discovery does not prove Android rendering;
- a fresh index does not prove the named current-tree skill unless the skill itself resolves under a stable clean snapshot;
- a stable checkout does not make an unreadable or malformed individual skill valid;
- a source probe does not prove it executed merely because its file exists;
- a probe report emitted by an executing process may prove that process ran without proving regression tests passed;
- a source probe does not clear Phone Runtime / Phone Hands / P0 gates;
- GitHub source progress is not phone delivery or physical acceptance.

## P0 and duplicate-architecture firewall

This skill may inspect repository/source provenance only. It must not wake, retask, queue, replace, or coordinate Phone Hands, Phone Ingress, Nightcore, Pocket TTS, Chromium, Context Organs, P0 recovery, or their physical acceptance chain. It must not create a neighboring overlay controller, skill registry daemon, scheduler, or deployment path.

If a provenance check exposes a P0-related defect, preserve one concise finding for the canonical P0 owner and stop there.

## Done

A provenance pulse is complete only when it can name:

- the exact current-tree skill path/hash or exact structured failure to admit it;
- the pre/post HEAD and cleanliness observations plus `STABLE_CLEAN` or `UNSTABLE` snapshot verdict;
- the generated-index verdict when one was consulted;
- whether the probe was merely present as source or actually invoked by an authorized runner;
- the exact capability state reached;
- the fact that no later runtime/phone state was inferred without evidence.
