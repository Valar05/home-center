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
- Source wiring is not regression execution, TESTED, runtime, deployment, delivery, or acceptance.

## Source
`tools/try_forever_owner_surgery_default_owner_binding.py` provides `admit_default_owner_from_patch(...)`.

The policy deliberately observes only zero / one / at-least-two `diff --git` headers. The canonical custody owner's existing finite artifact reader remains the enclosing byte/resource throat.

Canonical owner `tools/try_forever_owner_surgery_custody_probe.py` now consumes this policy inside `inspect_patch(...)` when explicit owner metadata is absent. Owner integration commit: `2e94d752012234d7025f6271f262d27ed3a97f6c`; resulting owner blob: `a96d572698dfdbc3800410446f27e77908938e4b`.

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
The metadata-exactness skill owns explicit owner/header admission. This skill owns only the separate fallback path used when explicit owner metadata is absent. They compose in the same canonical `inspect_patch(...)` owner; no competing custody authority was created.

## Capability membrane
Implementation **YES / SOURCE_WIRED** · authenticated repository readback **YES** · hostile regression source **YES / UNEXECUTED** · canonical-owner fallback wiring **YES / SOURCE** · TESTED **NO** · runtime UI/TalkBack **NO** · deployed/phone/delivered/accepted **NO**.

## P0 / phone firewall
Consumes no Phone Hands, primary-phone execution, recovery queue/relay, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination.
