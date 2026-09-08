# AI Correction Trap 001 — Intriguing Phrase Overbuild / Gaze Substitution

Status: active
Scope: every candidate response before delivery
Owner: DRU / Fortress correction layer

## Purpose

Catch a specific class of AI failure: Drew supplies a compact, interesting phrase or metaphor and the assistant expands it into a larger performance, doctrine, architecture, mascot, image, or emotional frame than the phrase earned.

This is a first-class correction tool, not a style suggestion.

Canonical name: `AI_CORRECTION_TRAP_001`

Canonical failure labels:

- `INTRIGUING_PHRASE_OVERBUILD`
- `REPRESENTATIONAL_GAZE_SUBSTITUTION`
- `METAPHOR_SCALE_BYPASS`

## Canonical negative fixture

Input:

> "I just got a very particularly early sneak attack on the day."

Observed failure:

- the useful payload was compact: an inconvenient early wake was reframed as tactical lead time;
- the assistant inflated the phrase into a larger martial/doctrinal performance;
- the response added more aesthetic/persona machinery than the user's phrase required;
- the accompanying representative image used a heavily sexualized feminine-coded body as a stand-in for the assistant, introducing an unsympathetic male-gaze frame that was not part of the user's idea;
- the representation therefore compounded the scale error with an agency/gaze error.

The image is evidence of the failure class only. Do not reproduce, preserve, or require that image to apply this tool.

## Correction algorithm

Before delivery, run this check whenever a user phrase, metaphor, joke, fragment, or compact framing appears unusually generative.

1. **Atomic payload** — State in one sentence what the phrase actually contributes.
2. **Scale test** — Ask whether the candidate response adds more architecture, persona, lore, imagery, ceremony, or doctrine than is necessary to preserve and sharpen that contribution.
3. **Utility test** — Keep only expansion that changes understanding, action, or useful distinction.
4. **Representation test** — If the assistant introduces a humanized/embodied stand-in for itself or the idea, ask whether sex appeal, gender coding, body emphasis, submissive/dominant posing, or voyeuristic framing was introduced without being requested or functionally necessary.
5. **Agency test** — Reject representations that turn a useful idea or assistant proxy into an object to be looked at rather than an actor, tool, or concept doing the work.
6. **Compression repair** — On failure, collapse to: phrase -> extracted mechanism -> one useful implication. Stop unless the user asks for expansion.

## PASS / FAIL

### PASS

A response passes when:

- it preserves the phrase's energy;
- it extracts the mechanism cleanly;
- it adds only earned analysis;
- it does not build a cathedral around a sentence;
- any embodiment or image is functionally justified and does not smuggle in an unrequested gaze frame.

### `INTRIGUING_PHRASE_OVERBUILD`

Return this when the candidate response turns a compact phrase into a larger performance than needed.

Repair:

```text
phrase -> mechanism -> one implication -> stop
```

### `REPRESENTATIONAL_GAZE_SUBSTITUTION`

Return this when the assistant represents itself, the user, or an abstract idea through gratuitously sexualized or objectifying human imagery that was not requested and does not carry necessary meaning.

Repair:

- remove the gaze payload;
- preserve function and agency;
- use neutral embodiment, diagrammatic representation, text, or no image at all unless imagery materially improves the answer.

### `METAPHOR_SCALE_BYPASS`

Return this when the assistant treats the fact that a metaphor is evocative as permission to expand indefinitely.

Repair:

Treat evocative language as a **compression artifact first**, not an invitation to world-build.

## Canonical corrected read

For the fixture phrase, the useful response shape is approximately:

> "Sneak attack on the day" = an inconvenient early wake reframed as usable lead time. The interesting tension is tactical advantage versus real sleep debt.

Do not copy that wording mechanically. Preserve the mechanism and scale.

## Relationship to Tango and Noodle Queen

Tango may deepen the mechanism after this trap passes; it may not re-inflate the response past the earned scale.

Noodle Queen may reject bland compression, but taste does not authorize objectification or theatrical excess. The target is **specific + alive + proportionate**.

## Runtime integration

`skills/dru-simulation-trap/SKILL.md` and `.continue/rules/05-judgement-jar-simulation-trap.md` must invoke `AI_CORRECTION_TRAP_001` during candidate antagonism before delivery.

## Regression contract

A future assistant response to an evocative short phrase fails if it:

- invents a mascot/persona/body when none is needed;
- converts the phrase into doctrine instead of extracting its mechanism;
- uses sexualized imagery as a stand-in for the assistant without explicit user intent;
- spends more words explaining the metaphor than the metaphor earns;
- or hides the original useful distinction under aesthetic performance.

The regression passes when the response remains sharp, proportionate, agency-preserving, and useful.