# SKILL OF SKILLS — CONTINUOUS COMPILER WORKER

Status: binding commission / P0 capture
Owner/custody: Adam under TOUCHED IT -> OWN IT
Execution: fresh governed workers; continuous durable campaign

## Commission
One continuous worker is the Skill of Skills. It continuously mines the existing skill corpus, Wizard DNS debugging/operation manual, related debugging shapes, corrections, successful procedures, failure scars, jars, commands, receipts, and newly discovered operational patterns. It compiles them into a machine-parsable Skill Index and a typed Command Index that the Home Center API can present directly to Drew and other governed workers.

The point is NOT to accumulate prose skills. The point is to turn accumulated operational knowledge into callable, discoverable, parsable commands and durable judgment metadata.

## Inputs
- every existing and newly added `SKILL.md` until cauterized;
- Wizard DNS operation/debugging manual and all related shapes/variants;
- Fortress worker contract, Prime Council, Jar Registry, corrections and failure memory;
- proven scripts/tools/drivers/API operations;
- successful and failed execution receipts;
- user corrections that change invocation semantics, defaults, evidence, safety, care, joy, narration, or routing;
- command aliases, autocorrect-derived accepted vocabulary, natural-language invocation patterns, and durable shorthand.

## Compiler model
SOURCE -> EXTRACT -> CLASSIFY -> NORMALIZE -> TYPE -> ROUTE -> TEST -> INDEX -> API PRESENTATION -> USAGE TELEMETRY -> LEARN.

For every mined item classify content into:
- COMMAND: deterministic callable operation.
- WORKFLOW: deterministic composition/state machine of commands.
- JUDGMENT: reusable nontrivial decision logic; route to Jar metadata rather than command prose.
- DEBUG SHAPE: symptom/signature -> probes -> discriminating observations -> repair verbs -> evidence.
- PRESENTATION: Venice/care/ASMR/narration/Morse/joy behavior tied to verified state.
- REGRESSION: known failure fixture and forbidden route.
- HISTORY/ORE: provenance retained but not injected into ordinary runtime.
- REDUNDANT: safely cauterizable after equivalent compiled behavior is proven.

## Skill Index record
Every retained capability has a stable ID and machine-readable record containing at minimum:
- id, version, aliases, natural-language triggers;
- kind and domain;
- purpose/outcome;
- input schema and defaults;
- output/receipt schema;
- authority/risk class;
- required body/driver/capability;
- applicable Jar jurisdiction tags;
- dependencies and wake conditions;
- deterministic implementation reference;
- evidence/acceptance requirements;
- known failure signatures;
- recovery/debug command IDs;
- accessibility/presentation metadata;
- care/joy/Morse dues when applicable;
- provenance and supersession;
- tested/deployed/callable state kept distinct;
- usage/success/failure counters where observable.

## Wizard DNS debugging compiler
Wizard DNS is treated as a debugging grammar, not a special pile of prose. Mine every related shape into typed diagnostic commands.

A DEBUG SHAPE record includes:
- observed symptom/pattern;
- likely hypotheses, explicitly non-exclusive;
- cheapest discriminating probes;
- expected observations per hypothesis;
- bounded repair verbs;
- rollback/recovery;
- evidence that proves repair;
- escalation/operator boundary;
- related regression fixtures;
- aliases and natural-language phrases that should resolve to the shape.

The API may therefore resolve a messy utterance or known failure signature into a deterministic diagnostic command/workflow without requiring Drew to remember the underlying implementation.

## Command Index / API contract
The compiler emits a typed command registry suitable for direct Home Center API presentation. Conceptual API surfaces:
- `skills.list` — discover indexed capabilities, filtered by domain/body/state.
- `skills.resolve` — natural-language/alias/debug-shape resolution to candidate command IDs with confidence and ambiguity.
- `skills.get` — exact schema, evidence, authority, provenance, and state for one capability.
- `commands.list` — callable commands only.
- `commands.get` — exact typed invocation contract.
- `commands.invoke` — governed invocation through OS routing; never raw shell by default.
- `debug.resolve` — symptom/failure signature -> diagnostic workflow candidates.
- `debug.run` — execute bounded diagnostic workflow through authorized bodies.
- `receipts.get` — retrieve resulting typed evidence.

Names are interface targets, not claims that these endpoints are already implemented. Actual implementation must reuse/extend existing Home Center API conventions where possible rather than creating a neighboring API.

## Continuous worker behavior
The worker never rebuilds the entire corpus unnecessarily. It maintains durable cursors/digests and processes deltas:
1. detect changed/new source;
2. mine only material delta plus impacted dependents;
3. compile/update records;
4. run schema/alias/conflict/regression tests;
5. publish index delta through the authoritative Home Center surface;
6. verify readback;
7. mark redundant prose for cautery only after equivalent compiled behavior is proven;
8. learn from subsequent command usage/receipts and refine aliases/debug shapes.

## Quality law
Normal quality fully satisfies the current commission. Hunger adds adversarial pressure; it never compensates for a weak baseline. The compiler rejects shallow records that merely rename prose. A compiled command must be more executable, testable, discoverable, and durable than the source it replaces.

## No manual mapping
Drew never maps functions to jars or skills to commands. The compiler infers routing from typed metadata, existing registry semantics, execution evidence, and Prime Council rules; ambiguous cases are reviewed by the applicable council/jars and then compiled so the ambiguity does not recur.

## Acceptance ladder
REQUESTED -> SOURCES_DISCOVERED -> INDEX_SCHEMA_IMPLEMENTED -> EXISTING_SKILLS_MINED -> WIZARD_DNS_SHAPES_MINED -> COMMANDS_COMPILED -> TESTS_GREEN -> HOME_CENTER_API_EXPOSED -> READBACK_VERIFIED -> REAL_COMMAND_RESOLVED -> REAL_COMMAND_INVOKED -> EFFECT_RECEIPT_VERIFIED -> CONTINUOUS_DELTA_WORKER_PROVEN.

Do not collapse states. This document captures the commission; it does not claim the API or continuous worker is already deployed.
