# Operator Owner Surgery Metadata Exactness

## Purpose
Keep machine custody evidence exact before the canonical owner groups or promotes surgery artifacts. This skill covers three distinct ambiguities discovered after blob identity hardening:

1. authenticated current-owner **key** text must not gain authority by structural trimming;
2. textual patch base/state/owner headers must not use first-match semantics when duplicate authority metadata exists; and
3. a missing explicit owner header must not fall back to the default owner merely because the patch text mentions `OperatorOverlayService.java` somewhere.

This skill owns no patch executor, custody authority, overlay controller, phone lane, recovery daemon, P0 coordinator, or second owner-surgery probe.

## Core laws
- `NORMALIZATION-DEPENDENT OWNER KEY != AUTHENTICATED OWNER IDENTITY`.
- `FIRST MATCH != UNAMBIGUOUS PATCH METADATA`.
- `OWNER BASENAME MENTION != OWNER AUTHORITY`.
- `CARDINALITY-ONE AUTHORITY NEEDS ONLY ZERO / ONE / AT-LEAST-TWO OBSERVATION`, not a materialized list of every hostile duplicate.
- Identical duplicate authority headers are still ambiguous evidence.
- A malformed second authority header still counts as duplicate evidence; validation failure cannot make its label disappear from cardinality.
- Header recognition is line-local. Broad `\s` must not consume a newline and accidentally fuse two authority records.
- Supporting policy or prepared surgery existence is not canonical-owner wiring, regression execution, TESTED, runtime, deployment, delivery, or acceptance.

## Supporting source
`tools/try_forever_owner_surgery_metadata_exactness.py` provides:
- `admit_owner_identity(...)`: exact non-empty owner identity with no leading/trailing-whitespace repair;
- `admit_patch_metadata(...)`: exactly one recognized base-owner blob header, exactly one recognized state/status header, at most one explicit owner header, exact lowercase base SHA, and delegation to the existing exact state policy;
- label recognition independent from value admission, so malformed duplicate headers cannot be ignored merely because their values are invalid;
- horizontal-whitespace-only header grammar, preventing cross-line `\s` matching;
- bounded duplicate-cardinality scanning: each authority header family observes at most the first two matching labels because that is sufficient to prove zero/one/ambiguous cardinality. The canonical custody owner's existing 1 MiB finite artifact throat remains the enclosing text-resource authority.

`tools/try_forever_owner_surgery_default_owner_binding.py` provides the separate fallback rule used only when no explicit owner header exists:
- exactly one `diff --git` header;
- exact `a/<DEFAULT_OWNER> b/<DEFAULT_OWNER>` payload;
- no case folding, basename matching, path normalization, multi-file fallback, or duplicate diff-header authority.

The reusable fallback doctrine also lives at `skills/operator-owner-surgery-default-owner-binding/SKILL.md`.

## Prepared existing-owner surgery
`patches/try-forever-owner-surgery-metadata-exactness-owner.patch` is one exact surgery against the authenticated canonical-owner blob `523d8005212745738106733e91be6dd625caf767`.

It composes the existing supporting organs into the existing owner only:
- `inspect_patch(...)` delegates base/state/explicit-owner admission to `admit_patch_metadata(...)` and removes first-match authority;
- when explicit owner metadata is absent, `inspect_patch(...)` delegates default-owner admission to `admit_default_owner_from_patch(...)` instead of arbitrary basename substring search;
- structured delta owner identity delegates to `admit_owner_identity(...)`;
- programmatic current-owner map keys delegate to `admit_owner_identity(...)`;
- CLI `--current-owner OWNER=BLOB` removes `owner.strip()` and admits the exact owner key instead.

Patch state is **`CORRECTED_PROPOSED_NOT_APPLIED`**. It is prepared source, not implementation.

## Code-first review scars
The first supporting parser counted only value-valid regex matches. That was insufficient: a second malformed authority header could disappear from the duplicate count, and broad whitespace regexes risked line-crossing semantics. The corrected source counts recognized header labels first and validates the single admitted value afterward.

A later resource audit found that exact-cardinality admission still materialized every matching `re.Match` object even though authority only needs to distinguish zero, one, and at least two. The supporting policy now stops after the second match while the enclosing canonical owner retains its finite 1 MiB artifact observation.

The first prepared owner patch also tried to remove the legacy regex declarations with over-escaped unified-diff context. That patch shape was unsafe to promote. The corrected patch leaves the declarations harmlessly present and removes their authority from `inspect_patch(...)` itself, which is the behavior the RED owner boundary requires.

The default-owner review then found a distinct authority leak: the canonical owner treats any textual `OperatorOverlayService.java` mention as sufficient fallback evidence when `# OWNER:` is absent. The corrected prepared surgery composes exact single-file diff ownership instead of spawning a competing patch or custody owner.

## Regression source
- `tools/test_try_forever_owner_surgery_metadata_exactness.py` — supporting policy fixtures, including malformed duplicate labels, cross-line header attack, and adversarial many-duplicate cardinality source, **UNEXECUTED**.
- `tools/test_try_forever_owner_surgery_default_owner_binding.py` — supporting exact fallback-owner fixtures, **UNEXECUTED**.
- `tools/test_try_forever_owner_surgery_metadata_owner_boundary.py` — intentionally RED existing-owner boundary, now including fallback-owner binding, **UNEXECUTED**.
- `tools/test_try_forever_owner_surgery_metadata_owner_patch.py` — proves exact Git-blob lock, combined patch contents, and that prepared provenance does not launder the current owner into SOURCE_WIRED, **UNEXECUTED**.

The RED boundary requires the existing `try_forever_owner_surgery_custody_probe.py` to consume all exact gates and retire CLI `owner.strip()`, first-match `BASE_RE/STATE_RE/OWNER_RE.search(...)` authority, and arbitrary-basename default-owner inference.

## Current owner truth
Canonical v10 owner wiring for this combined metadata/default-owner slice: **NO / RED**.

Authenticated owner readback remains blob `523d8005212745738106733e91be6dd625caf767`. The historical Command Center worker surface is retired; no duplicate worker route is authorized. The audited GitHub mutation surface requires full-file replacement, so a prepared patch is not reported as applied merely because it exists.

The previously completed blob-identity surgery remains valid and separate: blob text itself is already exact SOURCE_WIRED. This skill advances the **owner key**, **textual patch header cardinality**, and **implicit default-owner binding** channels without reopening blob normalization.

## Capability membrane
Supporting implementation **YES** · authenticated repository readback **YES** · bounded cardinality scan **YES / SOURCE** · exact fallback-owner policy **YES / SOURCE** · exact combined owner surgery **YES / CORRECTED_PROPOSED_NOT_APPLIED** · supporting regression source **YES / UNEXECUTED** · existing-owner integration **NO** · TESTED **NO** · runtime UI/TalkBack **NO** · deployed/phone/delivered/accepted **NO**.

## P0 / phone firewall
Consumes no Phone Hands, primary-phone execution, recovery queue/relay, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination.
