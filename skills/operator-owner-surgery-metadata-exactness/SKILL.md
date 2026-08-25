# Operator Owner Surgery Metadata Exactness

## Purpose
Keep machine custody evidence exact before the canonical owner groups or promotes surgery artifacts. This skill covers four distinct ambiguities discovered after blob identity hardening:

1. authenticated current-owner **key** text must be one exact built-in string, not caller-owned Python text and not text repaired by trimming;
2. owner identity has a bounded source ceiling before it can become a grouping/report key;
3. textual patch base/state/owner headers must not use first-match semantics when duplicate authority metadata exists; and
4. a missing explicit owner header must not fall back to the default owner merely because patch text mentions `OperatorOverlayService.java` somewhere.

This skill owns no patch executor, custody authority, overlay controller, phone lane, recovery daemon, P0 coordinator, or second owner-surgery probe.

## Core laws
- `STR SUBCLASS != AUTHENTICATED OWNER IDENTITY`.
- `NORMALIZATION-DEPENDENT OWNER KEY != AUTHENTICATED OWNER IDENTITY`.
- `UNBOUNDED OWNER KEY != BOUNDED AUTHORITY INPUT`.
- `FIRST MATCH != UNAMBIGUOUS PATCH METADATA`.
- `OWNER BASENAME MENTION != OWNER AUTHORITY`.
- `CARDINALITY-ONE AUTHORITY NEEDS ONLY ZERO / ONE / AT-LEAST-TWO OBSERVATION`, not a materialized list of every hostile duplicate.
- Identical duplicate authority headers are still ambiguous evidence.
- A malformed second authority header still counts as duplicate evidence; validation failure cannot make its label disappear from cardinality.
- Header recognition is line-local. Broad `\s` must not consume a newline and accidentally fuse two authority records.
- Source wiring is not regression execution, TESTED, runtime, deployment, delivery, or acceptance.

## Source organs
`tools/try_forever_owner_surgery_metadata_exactness.py` provides:
- `admit_owner_identity(...)`: exact built-in `str` admission, a 4096-code-point source ceiling, and no leading/trailing-whitespace repair;
- exact built-in string admission occurs before calling `strip()`, so a caller-owned `str` subclass cannot execute an overridden callback inside the evidence boundary;
- `admit_patch_metadata(...)`: exact built-in patch text, exactly one recognized base-owner blob header, exactly one recognized state/status header, at most one explicit owner header, exact lowercase base SHA, and delegation to the existing exact state policy;
- label recognition independent from value admission, so malformed duplicate headers cannot be ignored merely because their values are invalid;
- horizontal-whitespace-only header grammar, preventing cross-line `\s` matching;
- bounded duplicate-cardinality scanning: each authority header family observes at most the first two matching labels because that is sufficient to prove zero/one/ambiguous cardinality. The canonical custody owner's existing 1 MiB finite artifact throat remains the enclosing text-resource authority.

`tools/try_forever_owner_surgery_default_owner_binding.py` provides the separate fallback rule used only when no explicit owner header exists:
- exactly one `diff --git` header;
- exact `a/<DEFAULT_OWNER> b/<DEFAULT_OWNER>` payload;
- no case folding, basename matching, path normalization, multi-file fallback, or duplicate diff-header authority.

## Existing-owner integration
Canonical owner `tools/try_forever_owner_surgery_custody_probe.py` consumes both organs:
- `inspect_patch(...)` delegates base/state/explicit-owner admission to `admit_patch_metadata(...)` and no longer uses first-match metadata authority;
- missing explicit owner delegates to `admit_default_owner_from_patch(...)` instead of arbitrary basename substring search;
- structured delta owner identity delegates to `admit_owner_identity(...)`;
- programmatic current-owner keys delegate to `admit_owner_identity(...)`;
- CLI `--current-owner OWNER=BLOB` no longer calls `owner.strip()` and admits the exact owner key.

The stricter exact-built-in owner admission is therefore inherited by current programmatic, delta, and CLI owner-key paths without creating another canonical custody owner.

Historical integration commit: `2e94d752012234d7025f6271f262d27ed3a97f6c`.
Current metadata-policy blob after callback/resource hardening is tracked by repository readback; regression execution remains separate.

`patches/try-forever-owner-surgery-metadata-exactness-owner.patch` is retained as **APPLIED_SOURCE** provenance for the original base-blob-locked surgery, not as a promotion candidate.

## Code-first review scars
The first supporting parser counted only value-valid regex matches. That was insufficient: a second malformed authority header could disappear from the duplicate count, and broad whitespace regexes risked line-crossing semantics. The corrected source counts recognized header labels first and validates the single admitted value afterward.

A later resource audit found that exact-cardinality admission still materialized every matching `re.Match` object even though authority only needs to distinguish zero, one, and at least two. The supporting policy now stops after the second match while the enclosing canonical owner retains its finite 1 MiB artifact observation.

The first prepared owner patch tried to remove legacy regex declarations with over-escaped unified-diff context. The applied surgery left those declarations harmlessly present and removed their authority from `inspect_patch(...)` itself.

The default-owner review found a distinct authority leak: the canonical owner treated any textual `OperatorOverlayService.java` mention as sufficient fallback evidence when `# OWNER:` was absent. The applied surgery now requires exact single-file diff ownership.

The 06:58 review found a Python-container boundary upstream of textual exactness: `isinstance(value, str)` followed by `value.strip()` allowed a `str` subclass to run caller-owned code before evidence admission. Exact built-in string admission now happens first, and owner identity has its own 4096-code-point source ceiling before grouping/report work.

## Regression source
- `tools/test_try_forever_owner_surgery_metadata_exactness.py` — supporting policy fixtures, including callback-free `str`-subclass rejection, owner-key source ceiling, malformed duplicate labels, cross-line header attack, and adversarial many-duplicate cardinality source, **UNEXECUTED**.
- `tools/test_try_forever_owner_surgery_default_owner_binding.py` — supporting exact fallback-owner fixtures, **UNEXECUTED**.
- `tools/test_try_forever_owner_surgery_metadata_owner_boundary.py` — existing-owner source boundary, expected to match SOURCE_WIRED shape but still **UNEXECUTED**.
- `tools/test_try_forever_owner_surgery_metadata_owner_patch.py` — applied-source provenance/readback boundary, **UNEXECUTED**.

## Capability membrane
Implementation **YES / SOURCE_WIRED** · authenticated repository readback **YES** · exact built-in owner-string admission **YES / SOURCE** · bounded owner identity **YES / SOURCE** · bounded cardinality scan **YES / SOURCE** · exact fallback-owner policy **YES / SOURCE** · applied owner surgery **YES / APPLIED_SOURCE** · regression source **YES / UNEXECUTED** · existing-owner integration **YES / SOURCE** · TESTED **NO** · runtime UI/TalkBack **NO** · deployed/phone/delivered/accepted **NO**.

## P0 / phone firewall
Consumes no Phone Hands, primary-phone execution, recovery queue/relay, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination.
