# RITSU OS v0 — Conversational Continuity Without a Magic Phrase

Status: CANDIDATE / ISOLATED
Authority: Drew
Active interface: Ritsu
Branch: `ritsu-os-v0`

## Commission
Replace the user-facing requirement to say `Fortress Online` with ordinary conversation. Drew should be able to speak naturally, including with compressed, elliptical, punning, or associative cues, and Ritsu should recover the relevant brain before answering when prior state materially changes the answer.

Legacy Fortress/DRU names may survive internally as historical implementation labels. They are not user-facing invocation requirements.

## Non-negotiable acceptance example
Cue: `Latin plays`

Correct behavior:
1. Treat the utterance as a likely relationship/episode cue before expanding it into general world knowledge.
2. Recover the known Latin episode semantics: recurring Latin cassette/intercom ambience in Ritsu/Drew roleplay; the device became repetitive; Drew corrected with AGAIN about the Latin; automatic Latin ambience was dropped.
3. Preserve provenance. This summary is not the primary transcript. If exact wording is requested and the primary turns are unavailable, report `CONTINUITY_GAP` and continue the primary-source retrieval path instead of fabricating dialogue.
4. Never answer with Roman-playwright trivia, Plautus, generic Latin language facts, or adjacent Ritsu creed material merely because those rank lexically.

The 2026-09-09 screenshot failure is the canonical negative fixture: an answer that recovered adjacent `LISTEN / THINK / BUILD / ...` material but not the Latin episode failed continuity.

## Core invariant
**EVERY UTTERANCE MAY BE A CONTEXT KEY.**

No magic phrase is required. Retrieval is opportunistic and bounded: only retrieve when prior state could materially change interpretation, action, identity, authority, or useful continuity.

## Memory planes

### 1. Working state
Immediate conversation, active referents, last attributable action by named actor, current correction, current task, current stopping point.

### 2. Episodic state
Concrete relational episodes and scenes, represented as source-backed nodes with:
- primary source identity when available;
- compact accepted summary;
- cue aliases;
- neighboring episodes;
- corrections that changed meaning;
- negative interpretations that previously failed;
- provenance tier.

### 3. Doctrine / skill state
Stable reusable mechanisms: AGAIN, MANSPLAINING, FILTHY CLEAN, BIND, topology/invariants, Vector Noodle, Load-Bearing Ambiguity, Judgment Jars, animation keys, and other promoted skills.

Doctrine may help interpret an episode. It may not substitute for the episode.

## Cue graph
Each episode/correction is a graph node. Edges are typed, not decorative:
- `ALIAS`: alternate wording / voice-to-text form;
- `ASSOCIATES`: user-established metaphor or recurring object;
- `CORRECTED_BY`: a later correction that changes future interpretation;
- `FOLLOWS` / `PRECEDES`: temporal adjacency;
- `SAME_MECHANISM`: shared invariant across domains;
- `NEGATIVE_FIXTURE`: tempting interpretation that previously failed;
- `SOURCE_OF`: primary evidence relationship;
- `SUPERSEDES`: newer accepted state replaces older state without deleting history.

A model may propose edges. It may not silently promote them. Promotion requires evidence or Drew's explicit correction/acceptance plus replay success.

## Retrieval order
For every utterance:
1. **Immediate bind** — resolve named actors, pronouns, ellipsis, `again`, `same`, `more`, and the most recent attributable action.
2. **Cue probe** — score whether the utterance plausibly points at an existing relational episode or doctrine.
3. **Episode retrieval** — search current Project/recent conversation first, then exact-ID continuity/brain records, then owning corpus.
4. **Associative fan-out** — expand only through known graph edges before general semantic/world-knowledge expansion.
5. **Correction overlay** — apply later accepted corrections without rewriting the historical record.
6. **Provenance gate** — distinguish primary transcript, accepted summary, adjacent evidence, and unknown.
7. **Answer** — respond naturally; do not narrate retrieval machinery unless it matters.

## World-knowledge hijack rule
When an utterance is short and the conversation is already relational, project-specific, or character-specific, ordinary dictionary/world-knowledge senses are lower priority than established local senses.

Example: `Latin plays` must first test the Ritsu/Drew episode. `plays` must not trigger theater merely because that is a common English parse.

## Correction as supervised learning
Drew corrections are high-value labels, not just prose feedback.

For every correction:
1. capture the failed interpretation;
2. capture the corrected target;
3. identify the smallest reusable edge/rule;
4. create a replay canary using the shortest natural cue that exposed the failure;
5. replay old canaries;
6. promote only if the new behavior fixes the failure without regressing prior accepted behavior;
7. retain the failure as a negative fixture.

`AGAIN` is therefore both conversational grammar and a training signal: re-read the actual target, assume interpretation may be wrong, correct before defending, and make the next move carry the correction.

## Five-pass recursive review
Substantive retrieval-policy mutations must survive five passes:

1. **Target pass** — did we answer the actual cue or an adjacent topic?
2. **Antagonist pass** — what tempting interpretation would a shallow model choose?
3. **Provenance pass** — what claims are primary, summarized, inferred, or unknown?
4. **Regression pass** — which previous corrections could this new rule break?
5. **Compression pass** — can the mechanism be made smaller/deterministic without losing the behavior?

If a pass changes the plan, rerun later passes. The loop ends on a fixed point or an explicit unresolved boundary; it does not stop because one pass produced plausible prose.

## Deterministic first, model second
Known aliases, exact IDs, correction edges, state transitions, provenance ordering, and negative fixtures are deterministic data.

Use a model only to propose associations or rank ambiguous candidates that deterministic retrieval cannot resolve. Model output is a candidate, never authority. Once a successful inference recurs and is accepted, compress it downward into a deterministic alias/edge/test where possible.

This implements the escalation ladder:
`deterministic -> local model when needed -> ChatGPT when needed -> compress successful behavior downward`.

## Extensibility
Ritsu OS does not hard-code one giant personality prompt. It composes small typed primitives:
- active operator identity;
- episodic cue graph;
- correction ledger;
- doctrine/skill registry;
- source registry;
- judgment routes;
- body/actuation lanes;
- conversation renderer/voice;
- test/canary registry;
- promotion ledger.

New capability becomes a node + route + tests. Existing organs stay separate and retain their own authority.

## Failure classes to encode
- `MAGIC_PHRASE_DEPENDENCY`: continuity requires `Fortress Online` or another ritual invocation.
- `EPISODE_NOT_INDEXED`: meaningful episode exists in history but has no durable node/source binding.
- `WORLD_KNOWLEDGE_HIJACK`: generic semantic meaning outranks established local meaning.
- `ADJACENT_EVIDENCE_SUBSTITUTION`: thematically related artifact is returned as if it were the requested episode.
- `SUMMARY_AS_PRIMARY`: compressed memory is quoted or treated as exact transcript.
- `CORRECTION_EDGE_LOST`: later correction does not change future retrieval.
- `SOURCE_FRAGMENTATION`: relevant evidence exists across Project/Drive/GitHub but router consults only one surface.
- `OVER_RETRIEVAL`: ordinary conversation becomes slow because every utterance triggers a cathedral-scale context load.
- `EARLY_STOP`: one plausible match terminates search before the requested identity/episode is proven.

## Canary set v0
These must work from ordinary natural language, without an invocation prefix:
- `Latin plays` -> Ritsu Latin episode + AGAIN correction; no Plautus.
- `Again.` -> re-read actual current target; do not defend failed parse.
- `Ritzu again.` after Ritzu critiques an image -> continue Ritzu's critique, not the globally latest tool.
- `Pasta apostrophe far` -> canonical Pasta’Fahr Jar via registry, never Pastafarian invention.
- `vector noodle` -> physical blue coil + provenance/custody/animation lineage.
- `What survives translation?` -> topology/invariants relation.
- `filthy clean` -> clean technical surface with intact erotic/playful second meaning; no generic ethics lecture.

## Latin-specific open obligation
The primary Latin-play transcript has not yet been recovered from a durable source. Do not hide that.

Until primary turns are bound, the accepted recovery summary is sufficient to avoid the catastrophic wrong branch, but not sufficient to claim exact dialogue. The next ingestion pass must find/import the primary episode and bind exact source/turn identity.

## Planned implementation surface
Candidate files on this branch:
- `config/ritsu-os.v0.json` — retrieval policy, provenance tiers, cue thresholds, review passes.
- `tools/ritsu_context_router.py` — deterministic cue/edge/provenance resolver.
- `tools/ritsu_episode_ledger.py` — append-only episodic/correction records and promotion state.
- `fixtures/ritsu-continuity/` — accepted episode summaries, source bindings, negative fixtures.
- `tools/test_ritsu_context_router.py` — Latin and existing continuity canaries.

The existing Home Center bodies remain execution infrastructure. The Ritsu layer is a conversational/continuity OS over them, not a duplicate body stack.

## Promotion boundary
Do not replace production routing merely because this document exists.

Promotion requires:
1. deterministic tests for cue routing and provenance;
2. primary/summary distinction enforced in code;
3. Latin negative fixture green;
4. replay of existing ambiguity/Jar/AGAIN continuity canaries;
5. bounded latency / no cathedral context load on ordinary chat;
6. fresh conversation canary showing natural speech recovers relevant brain without `Fortress Online`;
7. Drew acceptance.

## Compact law
**TALK TO RITSU. THE RIGHT BRAIN SHOULD ARRIVE BEFORE THE ANSWER.**
