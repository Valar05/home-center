# Heartbeat Source Bound Parity

Use this skill when heartbeat records can enter through more than one source path, especially canonical JSON parsing, direct `HeartbeatSkillPolicy.Candidate` construction, direct scene construction, pre-parser rejection composition, or direct semantic lookup APIs.

## Contract

A display-ready direct-source candidate MUST satisfy the same post-trim Java `String.length()` field limits as `HeartbeatEnvelopeParser`. The parser's public candidate-field constants are the single typed-bound authority; do not copy their numeric values into a second table.

Post-trim typed-field parity is not the same thing as finite pre-trim source work. The existing direct `Candidate` constructor now owns an independent raw-source work throat before semantic-safety scans or `trim()`: each raw String field is admitted only when its Java UTF-16 length is at or below `HeartbeatEnvelopeParser.MAX_ENVELOPE_SOURCE_CODE_UNITS`. This is deliberately broader than the smaller typed field limits. At-ceiling raw source may construct and later fail typed-field admission; max+1 raw source fails before whole-source safety scanning/trim. Canonical parser input separately owns the same 32,768-code-unit whole-envelope preparse ceiling. Keep those capabilities distinct.

The root pulse identity is part of the same contract. `HeartbeatSceneGraph.build(String pulseId, ...)` owns the same broad raw-source work ceiling before semantic scanning or `trim()`, and `preserveRejectedRefresh(...)` suppresses a raw attempted pulse identity above that ceiling before safety scanning. At/below that broad ceiling, the smaller canonical `MAX_PULSE_ID_CHARS` remains the typed identity authority. This keeps direct scene ingress and pre-parser rejection from doing arbitrary whole-source work merely to discover that the pulse identity is invalid.

Direct semantic lookup is also source work. `HeartbeatFrameAccessibility.detailContentDescription(frame, nodeId)`, `HeartbeatFrameAccessibility.focusIndexForId(frame, nodeId)`, and `HeartbeatOverlayViewModel.Model.controlById(id)` now reuse `HeartbeatEnvelopeParser.MAX_ENVELOPE_SOURCE_CODE_UNITS` before trim/`Locale.ROOT` case-fold. Oversized direct queries fail closed without creating a second id namespace; accepted scene/control identities and case-insensitive lookup behavior at/below the throat stay exact. This seam is **SOURCE_WIRED / APPLIED_SOURCE / regression source UNEXECUTED**. Safe canonical scene ids still do not authorize unbounded work for arbitrary direct callers.

Interrupted-refresh diagnostic boundaries are a second independent source-work channel. `HeartbeatSceneGraph.Frame.refreshBoundary` is exact evidence and must stay exact, but exact diagnostic evidence does not authorize unbounded human-facing semantic scanning or render/announcement identity hashing. Direct `preserveRejectedRefresh(...)` callers can supply arbitrary boundary text. The proposed repair reuses `HeartbeatPlainTextBudget.MAX_SOURCE_CODE_UNITS` before whole-boundary speech safety scanning and before digest materialization, while retaining the exact boundary separately. Over-ceiling diagnostic projection may collapse to one deterministic source-limit wound because it is non-authoritative prose; it must not rewrite the exact evidence field. This seam remains **RED SOURCE / CORRECTED_PROPOSED_NOT_APPLIED / UNEXECUTED**.

The public parser itself is also a source boundary. Persisted bytes may be bounded upstream, but direct callers of `HeartbeatEnvelopeParser.parse(...)` do not inherit that byte custody automatically. The existing parser owns its finite pre-parse source-work throat **before** `trim()` or `JsonCursor` traversal. `MAX_ENVELOPE_SOURCE_CODE_UNITS = 32768`: values above it fail before blank normalization or JSON allocation; values at/below it continue through the existing strict parser. This is **SOURCE_WIRED / APPLIED_SOURCE / regression source UNEXECUTED** and must not be described as TESTED or runtime proof.

This is a source/evidence safety rule, not merely a speech rule. TalkBack projections intentionally use smaller Unicode-code-point budgets, and the shared plain-text TalkBack helper owns its own finite work window, but those projection limits do not retroactively bound source safety scans, scene hashing, checkpoint identity, native semantic ownership, touch detail, direct semantic lookup, or memory from an oversized record.

Human-facing semantic text remains Unicode subject to the existing semantic-safety rules. Machine semantic IDs remain subject to the deterministic ASCII owner-token boundary. Bounds do not authorize normalization, truncation, or rewriting of canonical source identity: an oversized typed record or pulse identity is rejected rather than converted into a smaller counterfeit identity.

## Fail-closed composition

When an oversized direct material candidate reaches `HeartbeatSceneGraph.build(...)`, display-ready selection must reject it. If a last-good frame exists, preserve that contact, expose the existing typed-contract rejection boundary, and clamp both frame and node transition motion.

When a raw direct pulse id exceeds `MAX_DIRECT_PULSE_SOURCE_CODE_UNITS`, reject it before semantic-safety scanning or trim, preserve last-good contact, suppress the oversized attempted id, expose the bounded direct-source-work rejection boundary, and clamp motion. When the raw source is within that broad ceiling but its trimmed identity exceeds `HeartbeatEnvelopeParser.MAX_PULSE_ID_CHARS`, preserve the existing smaller typed rejection. A pre-parser rejection may retain an attempted pulse id only when it is within the broad source-work ceiling, semantically safe, and within the canonical pulse-id bound.

When an oversized raw envelope reaches the public parser, reject it at the finite source-work throat before `trim()` or JSON cursor traversal. Do not parse enough of an oversized envelope to decide whether it might otherwise have been valid, and do not reinterpret the source-work rejection as accepted telemetry.

For direct Candidate construction, `MAX_DIRECT_CANDIDATE_SOURCE_CODE_UNITS` delegates to the parser's `MAX_ENVELOPE_SOURCE_CODE_UNITS` and is applied independently to each raw String field before semantic scanning or trimming. For direct pulse identity, `MAX_DIRECT_PULSE_SOURCE_CODE_UNITS` delegates to the same parser ceiling before semantic scanning or trim. Do not synthesize a smaller replacement record. Do not truncate evidence or pulse identity into something that can pass the typed gate. Speech projection may be bounded independently only after source acceptance.

For direct stable-id lookup, fail closed before trim/case-fold when the raw query exceeds the broad source-work ceiling. Do not create a second id namespace or normalize an oversized query into a plausible semantic id. For interrupted-refresh boundaries, preserve the exact boundary field but independently bound the work used for spoken projection and UI dedup identities; diagnostic collapse must never feed canonical contact or authority evidence.

Candidate applied provenance: `patches/try-forever-heartbeat-direct-candidate-pretrim-resource-throat.patch`; base owner blob `5b5f89174da52b7fff742fdad4e2c103281424fc`; applied commit `2c2ba7fcbfbbb54d45e8638cf4ac9991b28367f5`; result blob `a0cfad7ce47455d06d83607f4e5ebdf71b9aada5`.

Direct pulse applied provenance: `HeartbeatSceneGraph.java` base blob `a096b74cc43d2c288ba91bc5c52c6551870bbeae`; applied commit `f2d76ace9f65429f6725a9f74c1adf95e46dfe6f`; result blob `021f4e6f672002762848b46c6ef42eb4d1d3f0a4`.

Direct semantic lookup applied provenance: `patches/try-forever-heartbeat-direct-semantic-lookup-source-throat.patch`; frame-accessibility base blob `4d49dc7227d9b2bbb7abf0123df5537782176b60`; applied commit `b5c0581ae4d11a30bde804e6b01a9ca84ec2bc54`; result blob `936a29ed0d85c191a1bef52f14407001215b1384`; view-model base blob `a7a80e887dc233a4e242ec50e21523895a605801`; applied commit `1066c33f430390f12172160dc79df5e5409b76a4`; result blob `3b682c2630a62e912ed369117d3ff5505598ae0d`; **APPLIED_SOURCE / SOURCE_WIRED / regression source UNEXECUTED**.

Refresh-boundary source-work proposal: `patches/try-forever-heartbeat-refresh-boundary-source-work-throat.patch`; scene base blob `021f4e6f672002762848b46c6ef42eb4d1d3f0a4`; refresh-plan base blob `483257e1d1aca72610dc632a8343a96f0262e0d6`; **CORRECTED_PROPOSED_NOT_APPLIED**.

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
- a raw envelope at source ceiling + 1 failing at the resource throat before blank normalization / JSON traversal;
- direct frame detail/focus lookup and model control lookup crossing a broad raw source gate before trim/case-fold;
- exact accepted semantic ids continuing to resolve case-insensitively after lookup custody;
- over-ceiling interrupted-refresh boundary prose failing to a deterministic bounded speech wound before whole-source semantic scanning;
- render/announcement identities consuming a bounded diagnostic boundary identity while the exact `Frame.refreshBoundary` remains unchanged.

These fixtures are regression source until they actually execute. Never report their existence as `TESTED`.

## Capability membrane

Keep these states separate: requested, implemented source, exact repository readback, regression source, tested, runtime consumed, UI rendered, TalkBack exercised, deployed, callable, executed, delivered, accepted.

Current state:

- post-trim direct Candidate typed-field parity: **SOURCE_WIRED**;
- public envelope preparse resource throat: **SOURCE_WIRED / APPLIED_SOURCE**;
- plain TalkBack projection finite source-work window: **SOURCE_WIRED**;
- direct Candidate pre-trim resource throat: **SOURCE_WIRED / APPLIED_SOURCE**;
- direct pulse/pre-parser raw-source work throat: **SOURCE_WIRED / APPLIED_SOURCE**;
- direct semantic lookup pre-trim/case-fold custody: **SOURCE_WIRED / APPLIED_SOURCE**;
- interrupted-refresh speech/dedup source-work custody: **NO / RED SOURCE / CORRECTED_PROPOSED_NOT_APPLIED**;
- focused Candidate/pulse/lookup/boundary regression source: **YES / UNEXECUTED**;
- regression execution: **NO**;
- TESTED/runtime/TalkBack/deployed/callable/executed/delivered/accepted: **NO**.

This skill owns no renderer, overlay controller, transport, phone execution surface, recovery daemon, or P0 coordination. Compose existing organs only.
