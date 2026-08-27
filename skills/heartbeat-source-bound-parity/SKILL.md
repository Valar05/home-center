# Heartbeat Source Bound Parity

Use this skill when heartbeat records can enter through more than one source path, especially canonical JSON parsing, direct `HeartbeatSkillPolicy.Candidate` construction, direct scene construction, or pre-parser rejection composition.

## Contract

A display-ready direct-source candidate MUST satisfy the same post-trim Java `String.length()` field limits as `HeartbeatEnvelopeParser`. The parser's public candidate-field constants are the single typed-bound authority; do not copy their numeric values into a second table.

Post-trim typed-field parity is not the same thing as finite pre-trim source work. The existing direct `Candidate` constructor now owns an independent raw-source work throat before semantic-safety scans or `trim()`: each raw String field is admitted only when its Java UTF-16 length is at or below `HeartbeatEnvelopeParser.MAX_ENVELOPE_SOURCE_CODE_UNITS`. This is deliberately broader than the smaller typed field limits. At-ceiling raw source may construct and later fail typed-field admission; max+1 raw source fails before whole-source safety scanning/trim. Canonical parser input separately owns the same 32,768-code-unit whole-envelope preparse ceiling. Keep those capabilities distinct.

The root pulse identity is part of the same contract. `HeartbeatSceneGraph.build(String pulseId, ...)` owns the same broad raw-source work ceiling before semantic scanning or `trim()`, and `preserveRejectedRefresh(...)` suppresses a raw attempted pulse identity above that ceiling before safety scanning. At/below that broad ceiling, the smaller canonical `MAX_PULSE_ID_CHARS` remains the typed identity authority. This keeps direct scene ingress and pre-parser rejection from doing arbitrary whole-source work merely to discover that the pulse identity is invalid.

The public parser itself is also a source boundary. Persisted bytes may be bounded upstream, but direct callers of `HeartbeatEnvelopeParser.parse(...)` do not inherit that byte custody automatically. The existing parser owns its finite pre-parse source-work throat **before** `trim()` or `JsonCursor` traversal. `MAX_ENVELOPE_SOURCE_CODE_UNITS = 32768`: values above it fail before blank normalization or JSON allocation; values at/below it continue through the existing strict parser. This is **SOURCE_WIRED / APPLIED_SOURCE / regression source UNEXECUTED** and must not be described as TESTED or runtime proof.

This is a source/evidence safety rule, not merely a speech rule. TalkBack projections intentionally use smaller Unicode-code-point budgets, and the shared plain-text TalkBack helper owns its own finite work window, but those projection limits do not retroactively bound source safety scans, scene hashing, checkpoint identity, native semantic ownership, touch detail, or memory from an oversized record.

Human-facing semantic text remains Unicode subject to the existing semantic-safety rules. Machine semantic IDs remain subject to the deterministic ASCII owner-token boundary. Bounds do not authorize normalization, truncation, or rewriting of canonical source identity: an oversized typed record or pulse identity is rejected rather than converted into a smaller counterfeit identity.

## Fail-closed composition

When an oversized direct material candidate reaches `HeartbeatSceneGraph.build(...)`, display-ready selection must reject it. If a last-good frame exists, preserve that contact, expose the existing typed-contract rejection boundary, and clamp both frame and node transition motion.

When a raw direct pulse id exceeds `MAX_DIRECT_PULSE_SOURCE_CODE_UNITS`, reject it before semantic-safety scanning or trim, preserve last-good contact, suppress the oversized attempted id, expose the bounded direct-source-work rejection boundary, and clamp motion. When the raw source is within that broad ceiling but its trimmed identity exceeds `HeartbeatEnvelopeParser.MAX_PULSE_ID_CHARS`, preserve the existing smaller typed rejection. A pre-parser rejection may retain an attempted pulse id only when it is within the broad source-work ceiling, semantically safe, and within the canonical pulse-id bound.

When an oversized raw envelope reaches the public parser, reject it at the finite source-work throat before `trim()` or JSON cursor traversal. Do not parse enough of an oversized envelope to decide whether it might otherwise have been valid, and do not reinterpret the source-work rejection as accepted telemetry.

For direct Candidate construction, `MAX_DIRECT_CANDIDATE_SOURCE_CODE_UNITS` delegates to the parser's `MAX_ENVELOPE_SOURCE_CODE_UNITS` and is applied independently to each raw String field before semantic scanning or trimming. For direct pulse identity, `MAX_DIRECT_PULSE_SOURCE_CODE_UNITS` delegates to the same parser ceiling before semantic scanning or trim. Do not synthesize a smaller replacement record. Do not truncate evidence or pulse identity into something that can pass the typed gate. Speech projection may be bounded independently only after source acceptance.

Candidate applied provenance: `patches/try-forever-heartbeat-direct-candidate-pretrim-resource-throat.patch`; base owner blob `5b5f89174da52b7fff742fdad4e2c103281424fc`; applied commit `2c2ba7fcbfbbb54d45e8638cf4ac9991b28367f5`; result blob `a0cfad7ce47455d06d83607f4e5ebdf71b9aada5`.

Direct pulse applied provenance: `HeartbeatSceneGraph.java` base blob `a096b74cc43d2c288ba91bc5c52c6551870bbeae`; applied commit `f2d76ace9f65429f6725a9f74c1adf95e46dfe6f`; result blob `021f4e6f672002762848b46c6ef42eb4d1d3f0a4`.

## Regression requirements

Keep source fixtures for:

- one direct typed candidate exactly at every parser-governed variable field bound;
- each variable candidate field exceeding its parser bound by one;
- direct candidate rejection preserving last-good contact and forbidding transition motion;
- a raw direct Candidate String exactly at the broad pre-trim work ceiling reaching ordinary constructor semantics even if it later fails the smaller typed field limit;
- raw direct Candidate source at broad work ceiling + 1 failing before semantic scan/trim work;
- direct pulse identity exactly at `MAX_PULSE_ID_CHARS` being accepted;
- direct pulse identity at `MAX_PULSE_ID_CHARS + 1` failing closed like canonical parsing;
- raw direct pulse source exactly at `MAX_DIRECT_PULSE_SOURCE_CODE_UNITS` reaching the smaller typed pulse-id gate;
- raw direct pulse source at broad work ceiling + 1 failing before semantic scan/trim while preserving last-good contact and clamping motion;
- pre-parser rejection suppressing raw pulse source above the broad source-work ceiling without rewriting the supplied rejection boundary;
- a raw envelope exactly at the public parser source ceiling still reaching existing parser semantics;
- a raw envelope at source ceiling + 1 failing at the resource throat before blank normalization / JSON traversal.

These fixtures are regression source until they actually execute. Never report their existence as `TESTED`.

## Capability membrane

Keep these states separate: requested, implemented source, exact repository readback, regression source, tested, runtime consumed, UI rendered, TalkBack exercised, deployed, callable, executed, delivered, accepted.

Current state:

- post-trim direct Candidate typed-field parity: **SOURCE_WIRED**;
- public envelope preparse resource throat: **SOURCE_WIRED / APPLIED_SOURCE**;
- plain TalkBack projection finite source-work window: **SOURCE_WIRED**;
- direct Candidate pre-trim resource throat: **SOURCE_WIRED / APPLIED_SOURCE**;
- direct pulse/pre-parser raw-source work throat: **SOURCE_WIRED / APPLIED_SOURCE**;
- focused Candidate/pulse regression source: **YES / UNEXECUTED**;
- regression execution: **NO**;
- TESTED/runtime/TalkBack/deployed/callable/executed/delivered/accepted: **NO**.

This skill owns no renderer, overlay controller, transport, phone execution surface, recovery daemon, or P0 coordination. Compose existing organs only.
