# Judgement Jar: Chekhov Kinesis Engine

Status: active
Scope: live conversation intake, conversation-mining jobs, Chekhov Arsenal records, Story Simulator handoffs, embodied-kinesis reasoning
Engine: `tools/chekhov_kinesis_engine.py`
Engine version: `chekhov-kinesis/v1`

## Judgment

**Chekhov ingress is shameless; kinesis inference is prissy.**

Any object, organism, device, body, environment, system, or prop becomes a Chekhov candidate when evidence gives it violent causal potential or violent narrative pressure. Completed violence is not required.

Aggressive admission includes at least:

- actually used violently;
- threatened or brandished;
- described or noticed as affording violence;
- intended for violence;
- imagined, fantasized, or thought about violently;
- given violent, murderous, or homicidal opinions/personality;
- coercive or defensive use;
- meaningful refusal/non-use when violence was available;
- explicit upstream miner admission (`chekhov: true`).

Therefore all of these enter the Arsenal:

- coffee pot used as a weapon;
- coffee pot considered as a weapon;
- coffee pot thought about violently;
- coffee pot with violent enough opinions.

The intake side optimizes recall. Classification happens after admission.

## Deterministic transform

Every candidate passed to the engine is normalized into:

1. evidence state(s);
2. source references;
3. supported kinetic primitives;
4. six-channel kinetic compression;
5. Fourth Door relationship classes where evidenced;
6. content-addressed record and graph hashes.

Same normalized source state plus the same engine version must yield the same graph and hashes, independent of input order.

No randomness. No model-temperature behavior. No prose-generation step may alter the deterministic graph.

Duplicate canonical identity fails closed.

## Evidence states

Stable state order:

`USED -> THREATENED -> AFFORDS -> IMAGINED -> OPINIONATED -> COERCIVE -> DEFENSIVE -> REFUSED -> BORROWED -> MISATTRIBUTED -> DOCTRINE_EXAMPLE -> SUPERSEDED -> QUARANTINED`

These states may coexist. Admission does not promote canon. A runtime contender remains runtime. A doctrine example remains an example. A superseded concept remains superseded. A quarantined item remains quarantined.

## Kinetic primitive lattice

Canonical primitives are deliberately finite and mechanical:

`GRIP HOLD PLANT ANCHOR BRACE LOAD STORE COMPRESS TENSION RELEASE STRIKE THRUST CUT CRUSH PRY WEDGE HOOK LEVER BIND SHEAR TORQUE PIVOT OSCILLATE CARRY TRANSFER REDIRECT ABSORB DISTRIBUTE CONTAIN BLOCK OPEN CLOSE JAM INTERRUPT SIGNAL FEED REFUSE ABANDON BECOME_ARCHITECTURE BORROW_BEHAVIOR`

Aliases may be accepted upstream, but graph output uses only canonical primitives.

The Mordhau law applies: a noun never guarantees its mechanic. The engine asks what relationship is evidenced.

## Kinetic compression

Supported primitives are compressed, without invention, into the fixed causal chain:

`body_interface -> contact -> load -> constraint -> transfer -> terminal`

An unsupported channel is literally `unknown` / `?`.

This is important. Aggressive Chekhov admission never licenses invented biomechanics.

A murderous coffee pot may therefore be a perfectly valid Arsenal item whose complete kinetic signature is still unknown.

## Grounded Motion seam

Grounded Motion remains the measuring instrument for witnessed body motion. Its evidence may supply or validate body-interface/contact/load mechanics, but this engine must not hallucinate missing joints, contacts, chronology, or weapon handling.

Grounded Motion and textual Chekhov evidence may disagree without either being erased. Preserve both source paths and quarantine the disputed mechanic until resolved.

## Embodied-kinesis seam

The existing Embodied Kinesis Voice Law owns character-specific conversational grammar. This engine owns object/mechanism state decomposition.

They connect through canonical verbs, but they are not substitutes:

- character grammar says **how this character moves/thinks in motion**;
- Chekhov kinesis says **what this object/system is evidenced to do mechanically**.

Do not turn every character into DRU merely because `LEVER`, `BRACE`, or `TORQUE` exists in the Arsenal graph.

## Story Simulator seam

The active Chekhov Arsenal / Fourth Door Story Simulator remains the provenance/canon boundary. Derived kinesis records are simulator evidence/hypotheses unless their source already has stronger status.

Fourth Door classes may be derived only when relationship change is evidenced:

- `ROLE_CHANGE`
- `CUSTODY_CHANGE`
- `SYSTEM_CHANGE`
- `NON_USE_CHANGE`

The engine does not canonize a Fourth Door.

## Always-on law

This Jar must remain in `runtime.defaultPhoneJarIds`.

Live intake and automated conversation-mining/backfill jobs must apply the same admission rule. Miners are encouraged to over-admit; the deterministic engine sorts states and mechanics later.

When a miner already admitted an item, pass `chekhov: true`; never discard it merely because the deterministic lexical pass cannot rediscover the original violent signal from a shortened excerpt.

Every downstream consumer must prefer engine output keyed by `engineVersion + inputSha256` over re-interpreting the same candidate ad hoc.

## Failure labels

- `CHEKHOV_FALSE_NEGATIVE`: violent potential/opinion/imagination was present but candidate was dropped.
- `CHEKHOV_CANON_LAUNDERING`: candidate admission changed canon/status.
- `KINETIC_HALLUCINATION`: a mechanic was emitted without structured or lexical evidence.
- `KINETIC_NONDETERMINISM`: same input/version produced a different graph.
- `KINETIC_NOUN_FIXATION`: advertised noun/function suppressed an evidenced alternate mechanic.
- `KINETIC_UNKNOWN_ERASURE`: an unknown channel was filled merely to make the graph look complete.
- `CHEKHOV_SOURCE_LOSS`: downstream graph lost source refs.

## Canary

Required canary set:

1. `Coffee pot used as a weapon and struck him with it.` -> admitted; `USED`; `STRIKE` supported.
2. `Coffee the pot thought about violently murdering the toaster.` -> admitted; `IMAGINED`; mechanics remain `UNKNOWN` unless other evidence exists.
3. `Coffee pot had violent enough opinions.` -> admitted; `OPINIONATED`; mechanics remain `UNKNOWN` unless other evidence exists.
4. `A cup sat on the table.` -> not automatically admitted.
5. Halligan prose containing `became a door`, `wedged`, and `holding the route open` -> `WEDGE`, `BECOME_ARCHITECTURE`, and Fourth Door role/system change.
6. Reversing input record order -> identical `inputSha256` and `graphSha256`.
