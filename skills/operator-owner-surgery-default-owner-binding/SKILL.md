# Operator Owner Surgery Default Owner Binding

## Purpose
Keep the canonical owner-surgery custody probe from inferring owner authority from an arbitrary textual mention when a textual patch omits an explicit `# OWNER:` header.

This skill owns no patch executor, custody authority, overlay controller, phone lane, recovery daemon, P0 coordinator, or second owner-surgery probe.

## Core laws
- `OWNER BASENAME MENTION != OWNER AUTHORITY`.
- `IMPLICIT DEFAULT OWNER REQUIRES ONE EXACT DIFF TARGET`.
- `PATCH/DEFAULT-OWNER MACHINE INPUT != EXTENSIBLE PYTHON STRING CALLBACK SURFACE`.
- `EXACT MACHINE TEXT != UNBOUNDED MACHINE TEXT`.
- Direct public helper safety must not depend on the canonical caller having already applied a resource throat.
- Without an explicit owner header, exactly one `diff --git` header must exist and it must be exactly `a/<DEFAULT_OWNER> b/<DEFAULT_OWNER>`.
- Patch text and fallback default-owner identity must be exact built-in strings before regex, formatting, or equality work.
- Patch text is capped at 1,048,576 code points before regex traversal; fallback default-owner identity is capped at 4,096 code points before expected-header formatting/equality.
- Case drift, path normalization, basename matching, multi-file fallback, duplicate diff headers, caller-owned string subclasses, and over-budget direct evidence fail closed.
- Structural patch evidence may decide the fallback owner; arbitrary prose, comments, or unrelated diff content may not.
- Source wiring is not regression execution, TESTED, runtime, deployment, delivery, or acceptance.

## Source
`tools/try_forever_owner_surgery_default_owner_binding.py` provides `admit_default_owner_from_patch(...)`.

The policy deliberately observes only zero / one / at-least-two `diff --git` headers. Canonical custody still contributes its enclosing finite artifact observation, but this helper now has independent direct-call throats: exact patch text crosses `MAX_DEFAULT_OWNER_PATCH_CODEPOINTS = 1_048_576` before regex traversal, and exact fallback owner identity crosses `MAX_DEFAULT_OWNER_IDENTITY_CODEPOINTS = 4_096` before expected-header construction or comparison. Exact built-in admission happens before those bounds, so a `str` subclass cannot execute caller-owned callbacks while manufacturing fallback-owner evidence.

Canonical owner `tools/try_forever_owner_surgery_custody_probe.py` consumes this policy inside `inspect_patch(...)` when explicit owner metadata is absent. Owner integration is existing source wiring; the direct resource hardening does not change ordinary accepted patch semantics.

## Regression source
`tools/test_try_forever_owner_surgery_default_owner_binding.py` attacks arbitrary owner mention, missing/duplicate diff headers, case drift, multi-file fallback, and CRLF framing.

`tools/test_try_forever_owner_surgery_default_owner_exact_input_boundary.py` requires callback-bearing patch/default-owner `str` subclasses to fail before callbacks execute.

`tools/test_try_forever_owner_surgery_direct_patch_resource_throats.py` pins max+1 direct patch text and max+1 fallback-owner identity rejection while preserving ordinary exact-string admission across both fallback and metadata helpers.

Status: **SOURCE / UNEXECUTED**.

## Cross-pollination with metadata exactness
The metadata-exactness skill owns explicit owner/header admission. This skill owns only the fallback path used when explicit owner metadata is absent. The exact-scalar and finite-direct-text laws now match across both helpers instead of relying on canonical composition to make direct callers safe. They compose in the same canonical `inspect_patch(...)` owner; no competing custody authority was created.

## Capability membrane
Implementation **YES / SOURCE_WIRED** · authenticated repository readback **YES** · exact built-in fallback inputs **YES / SOURCE_WIRED** · bounded direct patch text **YES / SOURCE_WIRED** · bounded fallback-owner identity **YES / SOURCE_WIRED** · hostile regression source **YES / UNEXECUTED** · canonical-owner fallback wiring **YES / SOURCE** · TESTED **NO** · runtime UI/TalkBack **NO** · deployed/phone/delivered/accepted **NO**.

## P0 / phone firewall
Consumes no Phone Hands, primary-phone execution, recovery queue/relay, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination.
