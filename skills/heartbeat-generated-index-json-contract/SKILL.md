# heartbeat-generated-index-json-contract

## Purpose
Keep generated-index JSON syntax from becoming an implicit provenance authority channel.

## Trigger
Use this skill when generated-index evidence is decoded, its JSON parser changes, alias semantics change, or a review discovers parser behavior that can select or crash before typed provenance policy runs.

## Canonical law
1. The finite artifact observer owns bytes, topology, exact whole-artifact SHA, and strict UTF-8.
2. JSON admission is a separate semantic gate.
3. Repeated member names are rejected at every object depth. Never choose first-wins or last-wins authority.
4. `NaN`, `Infinity`, and `-Infinity` are rejected even if the host JSON library accepts them as extensions.
5. Numeric lexemes are bounded before conversion; non-finite results fail closed.
6. JSON syntax, recursion, and interpreter conversion-limit failures must become a bounded typed rejection, not escape the provenance owner process.
7. Typed alias consistency still runs after JSON admission; this gate does not replace alias policy.
8. Root-shape, source-head, timestamp, clean-tree, freshness, and late-custody semantics remain owned by the existing provenance owner and its existing organs.

## Existing owner
`tools/try_forever_skill_provenance_probe.py` remains the sole provenance owner. Do not create a neighboring generated-index parser owner.

## Current source state
- Strict JSON policy: `tools/try_forever_generated_index_json_policy.py` — SUPPORTING_SOURCE.
- Hostile pure regression: `tools/test_try_forever_generated_index_json_policy.py` — REGRESSION_SOURCE / UNEXECUTED.
- Owner-boundary regression: `tools/test_try_forever_generated_index_json_owner_boundary.py` — RED / UNEXECUTED while the owner calls default `json.loads`.
- Exact owner delta: `patches/try-forever-generated-index-json-owner.delta.json` — PROPOSED_NOT_APPLIED, base-blob locked.
- Existing owner JSON wiring: NO until authenticated readback proves otherwise.

## Review teeth
A review must explicitly attack:
- duplicate-identical and duplicate-conflicting member names;
- duplicates nested below the root;
- non-standard numeric constants;
- huge numeric lexemes and non-finite exponent results;
- malformed and deeply nested JSON that would otherwise escape as an unhandled parser failure;
- capability laundering from source existence into TESTED or owner-wired state.

## Evidence membrane
`requested -> supporting source -> owner wired -> regression executed -> tested -> runtime -> deployed -> callable -> executed -> delivered -> accepted`

Never skip a state. A prepared delta is not owner wiring. A RED source fixture is not a failing executed test. Repository source is never phone delivery.

## P0 / phone firewall
This skill owns no Phone Hands ticket, primary-phone command, Home Center recovery mutation, Nightcore, Pocket TTS, Chromium, Context Organ, physical acceptance, or P0 coordinator. If a JSON finding affects P0, preserve one concise finding for the canonical P0 owner; do not mutate that chain here.

## Originality Tax
Once duplicate-member/host-parser permissiveness is identified, do not keep rediscovering it as prose. The next promotion is existing-owner composition plus authenticated readback and executed regression evidence through an authorized non-phone lane.
