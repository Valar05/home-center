# Operator Owner Surgery Default Owner Binding

## Purpose
Keep the canonical owner-surgery custody probe from inferring owner authority from an arbitrary textual mention when a textual patch omits an explicit `# OWNER:` header.

This skill owns no patch executor, custody authority, overlay controller, phone lane, recovery daemon, P0 coordinator, or second owner-surgery probe.

## Core laws
- `OWNER BASENAME MENTION != OWNER AUTHORITY`.
- `IMPLICIT DEFAULT OWNER REQUIRES ONE EXACT DIFF TARGET`.
- Without an explicit owner header, exactly one `diff --git` header must exist and it must be exactly `a/<DEFAULT_OWNER> b/<DEFAULT_OWNER>`.
- Case drift, path normalization, basename matching, multi-file fallback, and duplicate diff headers fail closed.
- Structural patch evidence may decide the fallback owner; arbitrary prose, comments, or unrelated diff content may not.
- Supporting policy or regression existence is not canonical-owner wiring, regression execution, TESTED, runtime, deployment, delivery, or acceptance.

## Supporting source
`tools/try_forever_owner_surgery_default_owner_binding.py` provides `admit_default_owner_from_patch(...)`.

The policy deliberately observes only zero / one / at-least-two `diff --git` headers. The canonical custody owner's existing finite artifact reader remains the enclosing byte/resource throat.

## Regression source
`tools/test_try_forever_owner_surgery_default_owner_binding.py` attacks:
- arbitrary `OperatorOverlayService.java` mention;
- missing diff header;
- case-drifted owner path;
- multi-file fallback;
- duplicate same-file diff headers;
- CRLF line framing.

Status: **SOURCE / UNEXECUTED**.

## Cross-pollination with metadata exactness
The metadata-exactness skill owns explicit owner/header admission. This skill owns only the separate fallback path used when explicit owner metadata is absent. They must compose in the same canonical `inspect_patch(...)` owner rather than create competing custody authorities.

The current canonical owner still falls back on `"OperatorOverlayService.java" in text`, so canonical-owner consumption of this skill is **NO / RED**.

## Capability membrane
Supporting implementation **YES** · authenticated repository readback **YES** · hostile regression source **YES / UNEXECUTED** · canonical-owner fallback wiring **NO** · TESTED **NO** · runtime UI/TalkBack **NO** · deployed/phone/delivered/accepted **NO**.

## P0 / phone firewall
Consumes no Phone Hands, primary-phone execution, recovery queue/relay, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination.
