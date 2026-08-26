# Operator Owner Surgery Default Owner Binding

## Purpose
Keep the canonical owner-surgery custody probe from inferring owner authority from an arbitrary textual mention when a textual patch omits an explicit `# OWNER:` header.

This skill owns no patch executor, custody authority, overlay controller, phone lane, recovery daemon, P0 coordinator, or second owner-surgery probe.

## Core laws
- `OWNER BASENAME MENTION != OWNER AUTHORITY`.
- `IMPLICIT DEFAULT OWNER REQUIRES ONE EXACT DIFF TARGET`.
- `PATCH/DEFAULT-OWNER MACHINE INPUT != EXTENSIBLE PYTHON STRING CALLBACK SURFACE`.
- Without an explicit owner header, exactly one `diff --git` header must exist and it must be exactly `a/<DEFAULT_OWNER> b/<DEFAULT_OWNER>`.
- Patch text and fallback default-owner identity must be exact built-in strings before regex, formatting, or equality work.
- Case drift, path normalization, basename matching, multi-file fallback, duplicate diff headers, and caller-owned string subclasses fail closed.
- Structural patch evidence may decide the fallback owner; arbitrary prose, comments, or unrelated diff content may not.
- Source wiring is not regression execution, TESTED, runtime, deployment, delivery, or acceptance.

## Source
`tools/try_forever_owner_surgery_default_owner_binding.py` provides `admit_default_owner_from_patch(...)`.

The policy deliberately observes only zero / one / at-least-two `diff --git` headers. The canonical custody owner's existing finite artifact reader remains the enclosing byte/resource throat. Exact built-in scalar admission now occurs before regex and expected-diff-header formatting, so a `str` subclass cannot execute caller-owned callbacks while manufacturing fallback-owner evidence.

Canonical owner `tools/try_forever_owner_surgery_custody_probe.py` consumes this policy inside `inspect_patch(...)` when explicit owner metadata is absent. Owner integration is existing source wiring; this exact-input hardening does not change ordinary accepted patch semantics.

## Regression source
`tools/test_try_forever_owner_surgery_default_owner_binding.py` attacks:
- arbitrary `OperatorOverlayService.java` mention;
- missing diff header;
- case-drifted owner path;
- multi-file fallback;
- duplicate same-file diff headers;
- CRLF line framing.

`tools/test_try_forever_owner_surgery_default_owner_exact_input_boundary.py` additionally requires callback-bearing patch/default-owner `str` subclasses to fail before their callbacks execute while preserving ordinary exact-string admission.

Status: **SOURCE / UNEXECUTED**.

## Cross-pollination with metadata exactness
The metadata-exactness skill owns explicit owner/header admission. This skill owns only the separate fallback path used when explicit owner metadata is absent. The exact-scalar rule now matches metadata exactness instead of leaving the fallback path broader than the explicit-owner path. They compose in the same canonical `inspect_patch(...)` owner; no competing custody authority was created.

## Capability membrane
Implementation **YES / SOURCE_WIRED** · authenticated repository readback **YES** · exact built-in fallback inputs **YES / SOURCE_WIRED** · hostile regression source **YES / UNEXECUTED** · canonical-owner fallback wiring **YES / SOURCE** · TESTED **NO** · runtime UI/TalkBack **NO** · deployed/phone/delivered/accepted **NO**.

## P0 / phone firewall
Consumes no Phone Hands, primary-phone execution, recovery queue/relay, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination.
