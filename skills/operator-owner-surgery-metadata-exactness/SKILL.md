# Operator Owner Surgery Metadata Exactness

## Purpose
Keep machine custody evidence exact and finite before the canonical owner groups or promotes surgery artifacts. This skill covers authenticated owner keys, diagnostic context, patch-header cardinality, direct patch-text resource custody, and the separate default-owner fallback boundary.

This skill owns no patch executor, custody authority, overlay controller, phone lane, recovery daemon, P0 coordinator, or second owner-surgery probe.

## Core laws
- `STR SUBCLASS != AUTHENTICATED OWNER IDENTITY`.
- `NORMALIZATION-DEPENDENT OWNER KEY != AUTHENTICATED OWNER IDENTITY`.
- `UNBOUNDED OWNER KEY != BOUNDED AUTHORITY INPUT`.
- `CALLER DIAGNOSTIC CONTEXT != TRUSTED FORMAT STRING INPUT`.
- `EXACT DIAGNOSTIC CONTEXT != UNBOUNDED DIAGNOSTIC CONTEXT`.
- `EXACT PATCH TEXT != UNBOUNDED REGEX INPUT`.
- Direct public helper safety must not depend on canonical v10 having already bounded the artifact.
- `DIAGNOSTIC PROSE != AUTHORITY EVIDENCE`.
- `FIRST MATCH != UNAMBIGUOUS PATCH METADATA`.
- `OWNER BASENAME MENTION != OWNER AUTHORITY`.
- Cardinality-one authority needs only zero / one / at-least-two observation, not a materialized list of every hostile duplicate.
- Identical duplicate authority headers are still ambiguous evidence.
- A malformed second authority header still counts as duplicate evidence; validation failure cannot make its label disappear from cardinality.
- Header recognition is line-local. Broad `\s` must not consume a newline and fuse authority records.
- Source wiring is not regression execution, TESTED, runtime, deployment, delivery, or acceptance.

## Source organs
`tools/try_forever_owner_surgery_metadata_exactness.py` provides:
- `_admit_diagnostic_field(...)`: exact non-empty built-in diagnostic context capped at 256 code points before formatted errors;
- `admit_owner_identity(...)`: exact built-in owner identity capped at 4,096 code points with no leading/trailing-whitespace repair;
- `admit_patch_metadata(...)`: exact built-in patch text capped at 1,048,576 code points **before regex traversal**, exactly one recognized base-owner blob header, exactly one recognized state/status header, at most one explicit owner header, exact lowercase base SHA, and delegation to the existing exact state policy;
- label recognition independent from value admission so malformed duplicate headers cannot disappear;
- horizontal-whitespace-only header grammar, preventing cross-line `\s` matching;
- bounded duplicate-cardinality scanning that stops after the second matching label.

Canonical v10 still supplies an enclosing one-observation artifact bound. The direct metadata helper now has its own source throat as well, so an independent caller cannot turn exact-but-unbounded text into a regex resource surface.

`tools/try_forever_owner_surgery_default_owner_binding.py` owns the separate fallback rule used only when no explicit owner header exists: exactly one exact `diff --git` target, exact built-in inputs, a 1,048,576-code-point direct patch-text throat, and a 4,096-code-point fallback-owner throat before formatting/equality.

## Existing-owner integration
Canonical owner `tools/try_forever_owner_surgery_custody_probe.py` consumes both organs. `inspect_patch(...)` delegates base/state/explicit-owner admission to `admit_patch_metadata(...)`; missing explicit owner delegates to `admit_default_owner_from_patch(...)`; structured delta owner identity and programmatic/CLI current-owner keys reuse `admit_owner_identity(...)`.

The stricter helper throats are therefore defense-in-depth around existing composition, not a new authority lane. Ordinary admitted patch/contact semantics remain unchanged.

## Review scars
Earlier repairs closed first-match header authority, malformed duplicate disappearance, cross-line whitespace matching, `str`-subclass callbacks, and unbounded owner/diagnostic scalar inputs. The 07:00 resource review found a separate fact: exact built-in patch text was still unbounded for **direct** helper callers even though canonical v10 happened to call through a one-MiB observation. The helper now owns the same finite order of magnitude before regex work. The neighboring default-owner helper had the same dependency on caller composition and was repaired in parallel.

## Regression source
- `tools/test_try_forever_owner_surgery_metadata_exactness.py` — exact owner/diagnostic/header/cardinality fixtures, **UNEXECUTED**.
- `tools/test_try_forever_owner_surgery_default_owner_binding.py` — exact fallback-owner fixtures, **UNEXECUTED**.
- `tools/test_try_forever_owner_surgery_default_owner_exact_input_boundary.py` — callback-free fallback input admission, **UNEXECUTED**.
- `tools/test_try_forever_owner_surgery_direct_patch_resource_throats.py` — max+1 direct metadata text, fallback patch text, and fallback-owner identity resource boundaries plus ordinary parity, **UNEXECUTED**.
- Existing canonical-owner integration/provenance boundaries remain source-only unless an authorized execution lane proves otherwise.

## Capability membrane
Implementation **YES / SOURCE_WIRED** · authenticated repository readback **YES** · exact built-in owner-string admission **YES / SOURCE** · bounded owner identity **YES / SOURCE** · exact bounded diagnostic-field admission **YES / SOURCE** · bounded direct patch metadata text **YES / SOURCE_WIRED** · bounded fallback patch/default-owner evidence **YES / SOURCE_WIRED** · bounded cardinality scan **YES / SOURCE** · exact fallback-owner policy **YES / SOURCE** · regression source **YES / UNEXECUTED** · existing-owner integration **YES / SOURCE** · TESTED **NO** · runtime UI/TalkBack **NO** · deployed/phone/delivered/accepted **NO**.

## P0 / phone firewall
Consumes no Phone Hands, primary-phone execution, recovery queue/relay, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination.
