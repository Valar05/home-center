# Heartbeat Source Bound Parity

Use this skill when heartbeat records can enter through more than one source path, especially canonical JSON parsing, direct `HeartbeatSkillPolicy.Candidate` construction, direct scene construction, or pre-parser rejection composition.

## Contract

A display-ready direct-source candidate MUST satisfy the same post-trim Java `String.length()` field limits as `HeartbeatEnvelopeParser`. The parser's public candidate-field constants are the single typed-bound authority; do not copy their numeric values into a second table.

Post-trim typed-field parity is not the same thing as finite pre-trim source work. The direct `Candidate` constructor currently runs semantic-safety scans and `trim()` over raw caller Strings before `hasTypedSourceContract(...)` reaches the smaller typed field limits. Canonical parser input already has a 32,768-code-unit whole-envelope preparse throat, but direct Candidate construction does not inherit that protection. Keep this as a separate capability state.

The root pulse identity is part of the same contract. `HeartbeatSceneGraph.build(String pulseId, ...)` MUST reject any post-trim pulse id larger than `HeartbeatEnvelopeParser.MAX_PULSE_ID_CHARS`, and `preserveRejectedRefresh(...)` MUST NOT retain an oversized attempted pulse id as diagnostic frame state. Canonical parser rejection, direct scene ingress, and pre-parser rejection therefore cannot disagree about how large a pulse identity is allowed to become.

The public parser itself is also a source boundary. Persisted bytes may be bounded upstream, but direct callers of `HeartbeatEnvelopeParser.parse(...)` do not inherit that byte custody automatically. The existing parser owns its finite pre-parse source-work throat **before** `trim()` or `JsonCursor` traversal. `MAX_ENVELOPE_SOURCE_CODE_UNITS = 32768`: values above it fail before blank normalization or JSON allocation; values at/below it continue through the existing strict parser. This is **SOURCE_WIRED / APPLIED_SOURCE / regression source UNEXECUTED** and must not be described as TESTED or runtime proof.

This is a source/evidence safety rule, not merely a speech rule. TalkBack projections intentionally use smaller Unicode-code-point budgets, and the shared plain-text TalkBack helper now owns its own finite work window, but those projection limits do not retroactively bound direct Candidate constructor safety scans, scene hashing, checkpoint identity, native semantic ownership, touch detail, or memory from an oversized source record.

Human-facing semantic text remains Unicode subject to the existing semantic-safety rules. Machine semantic IDs remain subject to the deterministic ASCII owner-token boundary. Bounds do not authorize normalization, truncation, or rewriting of canonical source identity: an oversized typed record or pulse identity is rejected rather than converted into a smaller counterfeit identity.

## Fail-closed composition

When an oversized direct material candidate reaches `HeartbeatSceneGraph.build(...)`, display-ready selection must reject it. If a last-good frame exists, preserve that contact, expose the existing typed-contract rejection boundary, and clamp both frame and node transition motion.

When an oversized direct pulse id reaches `HeartbeatSceneGraph.build(...)`, reject it before incomplete/identity-collision handling, preserve last-good contact, suppress the oversized attempted id, expose a bounded root-identity rejection boundary, and clamp motion. A pre-parser rejection may retain an attempted pulse id only when it is semantically safe **and** within the canonical pulse-id bound.

When an oversized raw envelope reaches the public parser, reject it at the finite source-work throat before `trim()` or JSON cursor traversal. Do not parse enough of an oversized envelope to decide whether it might otherwise have been valid, and do not reinterpret the source-work rejection as accepted telemetry.

For direct Candidate construction, the proposed pre-trim resource throat is the existing parser's `MAX_ENVELOPE_SOURCE_CODE_UNITS` applied independently to each raw String field before semantic scanning or trimming. This broad work ceiling is deliberately separate from the much smaller typed field limits: at-ceiling raw source may still construct and later fail the typed field contract; max+1 raw source must fail before whole-source scan/trim. The exact surgery is `patches/try-forever-heartbeat-direct-candidate-pretrim-resource-throat.patch`, currently **PROPOSED_NOT_APPLIED** against `HeartbeatSkillPolicy` blob `5b5f89174da52b7fff742fdad4e2c103281424fc`.

Do not synthesize a smaller replacement record. Do not truncate evidence or pulse identity into something that can pass the typed gate. Speech projection may be bounded independently only after source acceptance.

## Regression requirements

Keep source fixtures for:

- one direct typed candidate exactly at every parser-governed variable field bound;
- each variable candidate field exceeding its parser bound by one;
- direct candidate rejection preserving last-good contact and forbidding transition motion;
- a raw direct Candidate String exactly at the broad pre-trim work ceiling reaching ordinary constructor semantics even if it later fails the smaller typed field limit;
- raw direct Candidate source at broad work ceiling + 1 failing before semantic scan/trim work;
- direct pulse identity exactly at `MAX_PULSE_ID_CHARS` being accepted;
- direct pulse identity at `MAX_PULSE_ID_CHARS + 1` failing closed like canonical parsing;
- pre-parser rejection suppressing an oversized attempted pulse id while preserving the exact rejection boundary and last-good contact;
- a raw envelope exactly at the public parser source ceiling still reaching existing parser semantics;
- a raw envelope at source ceiling + 1 failing at the resource throat before blank normalization / JSON traversal.

These fixtures are regression source until they actually execute. Never report their existence as `TESTED`.

## Capability membrane

Keep these states separate: requested, implemented source, exact repository readback, regression source, tested, runtime consumed, UI rendered, TalkBack exercised, deployed, callable, executed, delivered, accepted.

Current state:

- post-trim direct Candidate typed-field parity: **SOURCE_WIRED**;
- public envelope preparse resource throat: **SOURCE_WIRED / APPLIED_SOURCE**;
- plain TalkBack projection finite source-work window: **SOURCE_WIRED**;
- direct Candidate pre-trim resource throat: **NO / PROPOSED_NOT_APPLIED / RED regression source**;
- regression execution: **NO**;
- TESTED/runtime/TalkBack/deployed/callable/executed/delivered/accepted: **NO**.

This skill owns no renderer, overlay controller, transport, phone execution surface, recovery daemon, or P0 coordination. Compose existing organs only.
