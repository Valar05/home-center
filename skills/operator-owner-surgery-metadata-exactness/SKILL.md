# Operator Owner Surgery Metadata Exactness

## Purpose
Keep machine custody evidence exact before the canonical owner groups or promotes surgery artifacts. This skill covers two distinct ambiguities discovered after blob identity hardening:

1. authenticated current-owner **key** text must not gain authority by structural trimming; and
2. textual patch base/state/owner headers must not use first-match semantics when duplicate authority metadata exists.

This skill owns no patch executor, custody authority, overlay controller, phone lane, recovery daemon, P0 coordinator, or second owner-surgery probe.

## Core laws
- `NORMALIZATION-DEPENDENT OWNER KEY != AUTHENTICATED OWNER IDENTITY`.
- `FIRST MATCH != UNAMBIGUOUS PATCH METADATA`.
- Identical duplicate authority headers are still ambiguous evidence.
- A malformed second authority header still counts as duplicate evidence; validation failure cannot make its label disappear from cardinality.
- Header recognition is line-local. Broad `\s` must not consume a newline and accidentally fuse two authority records.
- Supporting policy existence is not canonical-owner wiring, regression execution, TESTED, runtime, deployment, delivery, or acceptance.

## Supporting source
`tools/try_forever_owner_surgery_metadata_exactness.py` provides:
- `admit_owner_identity(...)`: exact non-empty owner identity with no leading/trailing-whitespace repair;
- `admit_patch_metadata(...)`: exactly one recognized base-owner blob header, exactly one recognized state/status header, at most one explicit owner header, exact lowercase base SHA, and delegation to the existing exact state policy;
- label recognition independent from value admission, so malformed duplicate headers cannot be ignored merely because their values are invalid;
- horizontal-whitespace-only header grammar, preventing cross-line `\s` matching.

The policy deliberately allows an absent explicit owner header so the canonical owner's existing default-owner fallback can remain a separate rule.

## Code-first review scar
The first supporting parser counted only value-valid regex matches. That was insufficient: a second malformed authority header could disappear from the duplicate count, and broad whitespace regexes risked line-crossing semantics. The corrected source counts recognized header labels first and validates the single admitted value afterward.

## Regression source
- `tools/test_try_forever_owner_surgery_metadata_exactness.py` — supporting policy fixtures, including malformed duplicate labels and cross-line header attack, **UNEXECUTED**.
- `tools/test_try_forever_owner_surgery_metadata_owner_boundary.py` — intentionally RED existing-owner boundary, **UNEXECUTED**.

The RED boundary requires the existing `try_forever_owner_surgery_custody_probe.py` to consume both exact gates and retire CLI `owner.strip()` plus first-match `BASE_RE/STATE_RE/OWNER_RE.search(...)` authority.

## Current owner truth
Canonical v10 owner wiring for this metadata-exactness slice: **NO / RED**.

The previously completed blob-identity surgery remains valid and separate: blob text itself is already exact SOURCE_WIRED. This skill advances the **owner key** and **textual patch header cardinality** channels without reopening blob normalization.

## Capability membrane
Supporting implementation **YES** · authenticated repository readback **YES** · supporting regression source **YES / UNEXECUTED** · existing-owner metadata integration **NO** · TESTED **NO** · runtime UI/TalkBack **NO** · deployed/phone/delivered/accepted **NO**.

## P0 / phone firewall
Consumes no Phone Hands, primary-phone execution, recovery queue/relay, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination.
