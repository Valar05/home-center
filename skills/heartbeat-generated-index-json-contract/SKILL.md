# heartbeat-generated-index-json-contract

## Purpose
Keep generated-index JSON syntax from becoming an implicit provenance authority channel.

## Trigger
Use this skill when generated-index evidence is decoded, its JSON parser changes, alias semantics change, or a review discovers parser behavior that can select or crash before typed provenance policy runs.

## Canonical law
1. The finite artifact observer owns bytes, topology, exact whole-artifact SHA, and strict UTF-8.
2. JSON admission is a separate semantic gate.
3. Repeated member names are rejected at every object depth. Never choose first-wins or last-wins authority.
4. Duplicate identity is judged after JSON escape decoding: source spellings such as `sourceHead` and `\u0073ourceHead` that decode to the same member name are one duplicate and must fail closed.
5. Distinct supported alias names remain distinct through JSON admission so the existing typed alias-consistency organ, not the JSON parser, owns alias reconciliation.
6. `NaN`, `Infinity`, and `-Infinity` are rejected even if the host JSON library accepts them as extensions.
7. Numeric lexemes are bounded before conversion; non-finite results fail closed.
8. JSON syntax, recursion, and interpreter conversion-limit failures must become a bounded typed rejection, not escape the provenance owner process.
9. Typed alias consistency still runs after JSON admission; this gate does not replace alias policy.
10. Root-shape, source-head, timestamp, clean-tree, freshness, and late-custody semantics remain owned by the existing provenance owner and its existing organs.

## Existing owner
`tools/try_forever_skill_provenance_probe.py` remains the sole provenance owner. Do not create a neighboring generated-index parser owner.

## Current source state
- Strict JSON policy: `tools/try_forever_generated_index_json_policy.py` — SUPPORTING_SOURCE.
- Hostile pure regression: `tools/test_try_forever_generated_index_json_policy.py` — REGRESSION_SOURCE / UNEXECUTED; includes escaped-name semantic duplicates and the JSON-vs-alias ownership boundary.
- Owner-boundary regression: `tools/test_try_forever_generated_index_json_owner_boundary.py` — REGRESSION_SOURCE / UNEXECUTED; its prior RED owner condition is repaired in source but has not been executed.
- Exact owner delta: `patches/try-forever-generated-index-json-owner.delta.json` — APPLIED_SOURCE, originally base-blob locked to owner blob `2f3ebd530f46283a59bd6ff34149042a1b825d89`.
- Existing owner JSON wiring: YES / SOURCE_WIRED. Owner commit `0c137eac3c84cfa6c9fba0b26615e5ddc8ba6628`, authenticated owner blob `1882ed3b6cf7fe7a9ab5c44862640a6f415bdd1d`.
- Authenticated commit diff proves the owner change touched one file and exactly three hunks: strict parser import, strict parser call, and `GeneratedIndexJsonError` mapping into the existing `UNRESOLVED` surface.
- Pre-mutation plan gate for this promotion: `receipts/heartbeat-skill-lights/2026-08-20-0500-plan.json` plus `receipts/venice/2026-08-20-try-forever-heartbeat-0500-plan-review.json` with `PLAN_ALLOWED`.
- She-Raw authoritative review surface: FAULT, account-connection HTTP 400; no synthetic substitute and no retry hammering.
- Command Center Codex agents/jobs/sessions/workers are retired; no worker queue is part of this source-wiring claim.

## Review teeth
A review must explicitly attack:
- duplicate-identical and duplicate-conflicting member names;
- duplicates nested below the root;
- duplicate decoded member names hidden behind JSON escape spelling;
- the boundary where distinct supported aliases must survive JSON parsing and be reconciled later by typed alias policy;
- non-standard numeric constants;
- huge numeric lexemes and non-finite exponent results;
- malformed and deeply nested JSON that would otherwise escape as an unhandled parser failure;
- capability laundering from source existence into TESTED or runtime state;
- duplicate architecture: a second provenance parser/probe/controller is forbidden.

## Promotion discipline
Owner source promotion requires, in order:
1. authenticated owner blob equals the delta base blob before mutation;
2. one authorized non-phone mutation lane applies the delta to the existing sole owner;
3. authenticated owner diff/readback proves strict parser import/call/failure mapping;
4. only then may the owner state become `SOURCE_WIRED`.

Test promotion is separate:
1. execute the hostile policy regression and owner-boundary regression on the exact reviewed source head;
2. require deterministic passing receipts;
3. only then may TESTED advance.

Current state is therefore `SOURCE_WIRED / REGRESSION_SOURCE_UNEXECUTED / TESTED_NO`.

## Evidence membrane
`requested -> supporting source -> owner wired -> regression executed -> tested -> runtime -> deployed -> callable -> executed -> delivered -> accepted`

Never skip a state. Applied source is not executed regression. Repository source is never phone delivery.

## P0 / phone firewall
This skill owns no Phone Hands ticket, primary-phone command, Home Center recovery mutation, Nightcore, Pocket TTS, Chromium, Context Organ, physical acceptance, or P0 coordinator. If a JSON finding affects P0, preserve one concise finding for the canonical P0 owner; do not mutate that chain here.

## Originality Tax
The owner-wiring wound is now closed at SOURCE. Do not rediscover or narrate it again unless fresh readback regresses. Future work must either execute the exact regressions through an authorized non-phone test body or attack a materially different evidence/source wound without manufacturing runtime capability.
