# Heartbeat Semantic ID Boundary

## Purpose
Keep one heartbeat light identity equivalent everywhere that owns semantic routing: parser dedupe, scene/model lookup, native Button tags, persistent selection, viewport restoration, structure identity, presentation identity, and transition identity.

A human label can be Unicode. A machine owner key cannot be allowed to acquire a different equivalence relation in each layer.

## Identity contract
A display-ready `HeartbeatSkillPolicy.Candidate.id` is a deterministic ASCII token:

- ASCII letters `A-Z` / `a-z`;
- digits `0-9`;
- punctuation `- _ . / :`.

Canonical producers should emit stable lowercase ids. Uppercase ASCII remains accepted for migration/evidence continuity because the existing presentation layer already treats ASCII case-only drift as the same UI owner while exact checkpoint evidence can preserve the original spelling.

Non-ASCII ids are rejected at the typed source-contract boundary even when their characters are otherwise safe semantic Unicode. Labels, activation reasons, consequences, evidence, and provenance remain ordinary safe Unicode and may include valid ZWJ emoji sequences.

## Why the alphabet is narrow
The heartbeat stack historically used both:

- `toLowerCase(Locale.ROOT)` for parser dedupe, scene/model maps, structure hashes, and presentation hashes;
- `String.equalsIgnoreCase(...)` for native child tags, selection, and viewport ownership.

Those operations are not the same Unicode equivalence relation. A source-distinct Unicode pair can therefore be considered different by one layer and the same native owner by another. The typed ID boundary removes that split without weakening exact source/evidence identity and without creating a second controller.

Do not fix this by normalizing or rewriting an accepted non-ASCII id after parsing. Rewriting would destroy canonical source identity. Reject the typed record before display readiness instead.

## Required composition
Use the existing organs:

1. `HeartbeatSkillPolicy.hasTypedSourceContract(...)` rejects an invalid machine id.
2. `HeartbeatEnvelopeParser` already requires that typed contract, so canonical wire ingestion fails closed.
3. `HeartbeatSceneGraph.selectDisplayReadyLights(...)` already uses the same contract, so direct source callers cannot bypass the boundary into presentation.
4. Existing native/view-model/viewport owners may retain their current ASCII case-tolerant lookup behavior; the accepted alphabet makes their equivalence relation deterministic.

No new overlay controller, renderer, state store, transport path, phone ingress path, or P0 recovery owner is authorized by this skill.

## Regression law
Source regression must pin all of these:

- ordinary lowercase ASCII id accepted;
- uppercase ASCII case drift accepted;
- at least one Unicode case-equivalence split rejected;
- a visually confusable non-ASCII id rejected while its human label may remain Unicode;
- canonical parser rejection preserves the source/runtime membrane;
- direct-source rejection preserves the last-good scene and earns no transition motion.

A regression source file is **not** executed test evidence until the deterministic test lane actually runs it.

## Accessibility consequence
One semantic ID must name one touch/focus/detail owner. If two accepted source IDs can alias the same native Button tag or viewport owner, TalkBack selection and visible contact become ambiguous even if the labels look correct. The machine-ID boundary therefore protects accessibility identity, not merely parser neatness.

## Capability membrane
Keep these states separate:

`requested -> implemented source -> exact repository readback -> regression source -> tested -> runtime observed -> deployed -> callable -> executed -> delivered -> accepted`

Source policy and source fixtures do not prove Android execution, runtime TalkBack behavior, phone delivery, or physical acceptance.

## P0 firewall
This skill is source-only. It must not consume Phone Hands, primary-phone execution, queue/device probes, Home Center recovery mutation, Nightcore, Pocket TTS, Chromium, Context Organs, or any P0 physical acceptance surface.
