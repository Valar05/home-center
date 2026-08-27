# Semantic Text Safety

## Purpose
Keep human-facing, spoken, logged, and checkpointed text readable without silently rewriting canonical evidence. Use this skill anywhere repository/runtime data crosses from exact source identity into semantic UI, TalkBack, logs, review receipts, or operator-visible boundaries.

This is not an execution filter. Command-looking text, punctuation, emoji, non-Latin scripts, and ordinary Unicode remain inert data unless another commissioned subsystem explicitly owns execution semantics.

## Two different text classes
Do not reuse one sanitizer for two different ownership classes.

### Canonical semantic payload
Canonical heartbeat fields, ids, labels, provenance, reasons, consequences, evidence, and other typed source records participate in identity, dedupe, checkpoints, or later review.

For canonical semantic payload:

- reject decoded ISO control characters before trim/normalization can erase them;
- retain a safety verdict from the raw decoded constructor/input value before any compatibility trim, so a direct source caller cannot smuggle an edge control through normalization and then appear safe;
- reject malformed UTF-16 surrogate structure;
- reject directional bidi spoofing controls: U+061C, U+200E/U+200F, U+202A..U+202E, and U+2066..U+2069;
- preserve ordinary Unicode exactly, including valid supplementary pairs and U+200D ZERO WIDTH JOINER used in emoji/grapheme sequences;
- never strip a rejected character and then pretend the rewritten value is the canonical source;
- preserve command-looking text as inert data.

A directional-control wound is a semantic rejection, not a request to mutate source identity into something prettier.

### Human-facing boundary projection
A bounded rejection message, log line, toast, or diagnostic summary is a projection rather than canonical payload identity. It may normalize a broader set of control/FORMAT characters when required to prevent multiline or bidi-spoofed operator output, but it must stay explicitly separate from the raw exception/source identity.

Untrusted member names and identifiers used *inside* rejection prose are projection content too. A normal safe member name may be shown for diagnosis; a control/bidi-poisoned name must be replaced with a bounded placeholder rather than echoed into logs, TalkBack, review receipts, or scene boundaries. Apply Unicode-code-point bounds to safe names before including them in a boundary.

A public pre-parser preservation seam may need to retain an exact rejection boundary for evidence while refusing to speak that exact string. Keep both truths: preserve the exact field, but project a bounded safe description for TalkBack/operator prose. If the exact boundary contains unsafe semantic text, use an explicit generic placeholder in speech rather than stripping characters and pretending the result is the source.

Never feed sanitized projection text back into persistence as replacement canonical payload.

### Finite projection work
Bounded *returned* text does not imply bounded source work. A projector that returns 96 characters but hashes, encodes, trims, counts, or regex-walks an arbitrarily large source still has an unbounded caller-controlled work throat.

For non-authoritative diagnostic projection:

- exact built-in string admission must occur before callback-capable string work;
- source-work ceilings may deliberately sacrifice whole-input diagnostic identity once the ceiling is exceeded;
- an over-ceiling marker is preferable to hashing megabytes of non-authoritative prose merely to preserve a decorative digest;
- this loss of diagnostic identity must never rewrite or weaken the exact canonical evidence that caused the rejection.

Likewise, a consumer must not invoke caller-owned `Exception.__str__` or `__repr__` *before* a safe projection boundary. Safe projection after an unsafe callback is too late.

The same resource principle applies to accessibility speech. A small TalkBack result does not justify whole-source `trim`, code-point counting, grapheme regex traversal, or marker expansion over arbitrarily large direct-source text. Reuse the existing finite projection organs; do not mutate canonical evidence merely to make speech work finite.

## Accessibility contract
Text that reaches TalkBack or touch detail must agree with the visible semantic scene.

- Reject directional spoofing before a candidate becomes display-ready.
- Bound speech by Unicode code point, not UTF-16 code unit.
- Bound focused labels independently from exact Candidate.label so a direct source caller cannot create an unbounded TalkBack burst while the canonical field remains intact.
- Bound interrupted-refresh pulse identity and rejection-boundary speech independently from the exact Frame.visiblePulseId and Frame.refreshBoundary evidence fields.
- Never split a valid surrogate pair during truncation.
- Do not ban ZWJ merely because Java classifies it as `Character.FORMAT`; doing so breaks legitimate emoji/grapheme composition and is broader than the spoofing threat.
- A rejected attempted pulse must not leak its unsafe identity into an accessibility description. Preserve the last-good visible contact and speak the bounded rejection boundary instead.
- A legacy speech projection that encounters a material but unsafe candidate must report the omission explicitly rather than announcing a count and then silently naming nothing.

## Heartbeat integration
`HeartbeatEnvelopeParser` is the canonical semantic-ingestion gate. Its decoded string safety is checked before trimming. Parser error paths that mention unknown or duplicate JSON member names must also use bounded safe-name projection so hostile field names cannot poison the rejection receipt itself.

`HeartbeatSkillPolicy` repeats the directional/control/surrogate safety gate at the typed display-ready boundary so direct source callers cannot bypass parser assumptions. `Candidate` captures decoded safety before its compatibility trim and carries that verdict into display readiness and speech. Focused candidate speech bounds the label/consequence independently from the exact typed fields. `HeartbeatSceneGraph` rejects an unsafe direct pulse id before storing it as attempted/visible contact, and `preserveRejectedRefresh(...)` suppresses an unsafe pre-parser attempted id while leaving the original rejection boundary unchanged. `Frame.interruptedRefreshDescription()` projects the retained last-good pulse id and exact rejection boundary through bounded safe speech without rewriting those evidence fields.

Routine/plain TalkBack projections through `HeartbeatPlainTextBudget.boundedWithEllipsis(...)` now also own a finite direct-source work window before code-point/grapheme traversal. This is source-only accessibility/resource custody; it does not claim runtime TalkBack observation.

The duplicated *gate* is defense in depth; the directional-control definition lives in one source policy helper so parser and scene consumers do not drift into different bidi lists.

This remains source semantics only until the existing Operator Overlay runtime consumes the persisted payload, projects exact bytes, parses it, renders the scene, and exercises TalkBack through an authorized device lane.

## Owner-surgery discovery integration
The owner-surgery semantic producer exposes two shared non-authoritative organs: `project_owner_surgery_diagnostic_text(...)` for exact built-in diagnostic strings and `project_owner_surgery_exception_diagnostic(...)` for callback-free exception type/message projection. The latter inspects bounded base exception arguments without invoking caller-owned `__str__` or `__repr__`.

Canonical v10 consumes the ASCII-safe string projector inside `_error(...)`; `patches/try-forever-owner-surgery-discovery-diagnostic-projection.patch` is `APPLIED_SOURCE`, with applied commit `23091256cf90ea6bea3afc111db348e014c85584` and canonical owner blob `6de62efa07df4dabbb408ca77a427e83fbc4e883`.

The semantic projector also owns an independent **4,096-code-point direct source-work throat before whole-input encode/hash**. Over-ceiling non-authoritative prose returns a bounded ASCII marker and intentionally loses whole-input digest identity instead of hashing arbitrary caller text. The callback-free exception projector and finite source-work throat are both **SOURCE_WIRED** in semantic dependency blob `525bd5aefa82fd788490cef329e8262ca6987a4a`. Canonical path/artifact/Surgery evidence remains exact and is not rewritten by either projection policy.

One distinct RED consumer boundary remains: canonical `_error(...)` still computes `str(exc)` instead of consuming the shared callback-free exception projector. Safe final ASCII text and a safe dependency do not retroactively make that canonical callback safe.

`patches/try-forever-owner-surgery-diagnostic-source-callback-custody.patch` is now narrowed to that canonical consumer seam only. It is an exact base-blob-locked `CORRECTED_PROPOSED_NOT_APPLIED` surgery against canonical blob `6de62efa07df4dabbb408ca77a427e83fbc4e883`, consuming semantic dependency blob `525bd5aefa82fd788490cef329e8262ca6987a4a`. It proposes no second sanitizer.

`tools/test_try_forever_owner_surgery_discovery_error_projection.py` is **RED SOURCE / UNEXECUTED** only because the canonical callback consumer remains unwired. Its shared-helper and finite source-work assertions now converge on SOURCE_WIRED semantics, but regression execution is still NO. Dependency capability and consumer capability remain separate.

## Regression fixtures
For any semantic-ingestion path covered by this skill, preserve hostile fixtures for:

- RLO (`U+202E`) in a human label;
- LRI/RLI/FSI/PDI (`U+2066..U+2069`) in evidence or protocol text;
- LRM/RLM/ALM where relevant;
- an edge ISO control that constructor/trim would otherwise erase;
- an unpaired surrogate;
- a valid supplementary Unicode symbol;
- a legitimate ZWJ sequence that must remain accepted;
- an unknown JSON member name containing a directional control;
- a duplicate JSON member name containing a directional control;
- a swan-heavy direct-source label that exceeds the focused speech budget while Candidate.label remains exact;
- an oversized but safe interrupted-refresh boundary/pulse id whose speech projection truncates by code point while Frame evidence remains exact;
- an unsafe pre-parser rejection boundary that remains exact in Frame.refreshBoundary but is replaced with a safe speech placeholder;
- a hostile exception subclass whose `__str__` callback must not execute merely to produce human-facing discovery prose;
- a diagnostic source at source-ceiling max/max+1 proving over-ceiling projection stops before whole-input encode/hash;
- oversized direct routine-speech source proving the plain-text projector stops at its finite work window;
- a surrogate pair straddling that source-work edge, proving the finite window never manufactures malformed UTF-16.

Where scene/contact preservation exists, assert that rejected semantic text:

- leaves last-good contact/checkpoint identity unchanged;
- does not echo an unsafe attempted id into the frame;
- keeps the original trusted storage/parser boundary when only the attempted id is suppressed;
- clamps frame and node transition motion;
- does not become a Christmas-light transition.

Where legacy speech compatibility exists, assert that an unsafe material candidate is counted as omitted without speaking the poisoned label.

## Evidence and capability state
A committed parser/policy/scene repair proves **implemented source** after exact repository readback. Regression source proves only that a test exists. It does not prove the test executed.

Keep `requested -> implemented -> tested -> deployed -> callable -> executed -> delivered -> accepted` separate. A source-side semantic safety repair does not reopen a gated phone lane or authorize P0 recovery work.

Current owner-surgery state is intentionally split:

- shared ASCII-safe diagnostic projector: **SOURCE_WIRED**;
- finite direct diagnostic source-work throat: **SOURCE_WIRED**;
- shared callback-free exception diagnostic projector: **SOURCE_WIRED**;
- canonical discovery ASCII projection consumer: **SOURCE_WIRED / APPLIED_SOURCE**;
- canonical callback-free exception consumer: **NO / PROPOSED_NOT_APPLIED**;
- hostile regression: **RED SOURCE / UNEXECUTED**;
- TESTED/runtime/TalkBack/deployed/callable/executed/delivered/accepted/phone delivery: **NO**.

## Failure Is The Shovel
If a prior sanitizer fix simply rejected every Unicode `FORMAT` character, inspect whether that copied a presentation-projection rule into canonical payload semantics. The recovery must preserve the threat boundary without deleting legitimate Unicode behavior. Cross-pollination is useful only when ownership semantics survive the trip.

If a parser correctly rejects poisoned values but then echoes an untrusted poisoned member name into its error text, the boundary is still wounded. Repair the projection rather than declaring victory at the value validator.

If exact evidence is safe to retain but too large or unsafe to speak, do not solve the speech problem by rewriting the evidence. Add an explicit projection boundary and regression source that proves both sides stay true.

If a shared projector is SOURCE_WIRED but a canonical consumer still emits or creates unsafe diagnostic text, keep the consumer RED. Dependency capability is not transitive owner capability.

If a canonical consumer calls `str(exc)` and *then* safely projects the resulting string, inspect the callback boundary before the projector. Safe output does not retroactively make unsafe source work safe.

If a bounded projector digests an arbitrarily large exact source to produce a tiny marker, inspect source-work rather than returned-text size. Once a finite source throat is SOURCE_WIRED, do not keep describing that seam as proposed merely because a neighboring consumer seam remains red.

If a TalkBack helper returns a tiny ellipsized string but still trims, counts, or regex-walks an arbitrary direct-source string, the returned budget has not solved resource custody. Bound the work without rewriting canonical source.

## Done
This skill has materially contributed only when it changes a parser/policy/scene constraint, regression fixture, accessibility rule, or exact evidence boundary in the current mission. Naming the skill without such a consequence is decorative and stays dark.
