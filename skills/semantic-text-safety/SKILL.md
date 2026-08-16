# Semantic Text Safety

## Purpose
Keep human-facing, spoken, logged, and checkpointed text readable without silently rewriting canonical evidence. Use this skill anywhere repository/runtime data crosses from exact source identity into semantic UI, TalkBack, logs, review receipts, or operator-visible boundaries.

This is not an execution filter. Command-looking text, punctuation, emoji, non-Latin scripts, and ordinary Unicode remain inert data unless another commissioned subsystem explicitly owns execution semantics.

## Two different text classes
Do not reuse one sanitizer for two different ownership classes.

### Canonical semantic payload
Canonical heartbeat fields, ids, labels, provenance, reasons, consequences, evidence, and other typed source records participate in identity, dedupe, checkpoints, or later review.

For canonical semantic payload:

- reject decoded ISO control characters before trim/normalization can erase them;
- reject malformed UTF-16 surrogate structure;
- reject directional bidi spoofing controls: U+061C, U+200E/U+200F, U+202A..U+202E, and U+2066..U+2069;
- preserve ordinary Unicode exactly, including valid supplementary pairs and U+200D ZERO WIDTH JOINER used in emoji/grapheme sequences;
- never strip a rejected character and then pretend the rewritten value is the canonical source;
- preserve command-looking text as inert data.

A directional-control wound is a semantic rejection, not a request to mutate source identity into something prettier.

### Human-facing boundary projection
A bounded rejection message, log line, toast, or diagnostic summary is a projection rather than canonical payload identity. It may normalize a broader set of control/FORMAT characters when required to prevent multiline or bidi-spoofed operator output, but it must stay explicitly separate from the raw exception/source identity.

Never feed sanitized projection text back into persistence as replacement canonical payload.

## Accessibility contract
Text that reaches TalkBack or touch detail must agree with the visible semantic scene.

- Reject directional spoofing before a candidate becomes display-ready.
- Bound speech by Unicode code point, not UTF-16 code unit.
- Never split a valid surrogate pair during truncation.
- Do not ban ZWJ merely because Java classifies it as `Character.FORMAT`; doing so breaks legitimate emoji/grapheme composition and is broader than the spoofing threat.
- A rejected attempted pulse must not leak its unsafe identity into an accessibility description. Preserve the last-good visible contact and speak the bounded rejection boundary instead.

## Heartbeat integration
`HeartbeatEnvelopeParser` is the canonical semantic-ingestion gate. Its decoded string safety is checked before trimming. `HeartbeatSkillPolicy` repeats the directional/control/surrogate safety gate at the typed display-ready boundary so direct source callers cannot bypass parser assumptions. `HeartbeatSceneGraph` also rejects an unsafe direct pulse id before storing it as attempted/visible contact.

The duplicated *gate* is defense in depth; the directional-control definition lives in one source policy helper so parser and scene consumers do not drift into different bidi lists.

This remains source semantics only until the existing Operator Overlay runtime consumes the persisted payload, projects exact bytes, parses it, renders the scene, and exercises TalkBack through an authorized device lane.

## Regression fixtures
For any semantic-ingestion path covered by this skill, preserve hostile fixtures for:

- RLO (`U+202E`) in a human label;
- LRI/RLI/FSI/PDI (`U+2066..U+2069`) in evidence or protocol text;
- LRM/RLM/ALM where relevant;
- an edge ISO control that trim would otherwise erase;
- an unpaired surrogate;
- a valid supplementary Unicode symbol;
- a legitimate ZWJ sequence that must remain accepted.

Where scene/contact preservation exists, assert that rejected semantic text:

- leaves last-good contact/checkpoint identity unchanged;
- does not echo an unsafe attempted id into the frame;
- clamps frame and node transition motion;
- does not become a Christmas-light transition.

## Evidence and capability state
A committed parser/policy/scene repair proves **implemented source** after exact repository readback. Regression source proves only that a test exists. It does not prove the test executed.

Keep `requested -> implemented -> tested -> deployed -> callable -> executed -> delivered -> accepted` separate. A source-side semantic safety repair does not reopen a gated phone lane or authorize P0 recovery work.

## Failure Is The Shovel
If a prior sanitizer fix simply rejected every Unicode `FORMAT` character, inspect whether that copied a presentation-projection rule into canonical payload semantics. The recovery must preserve the threat boundary without deleting legitimate Unicode behavior. Cross-pollination is useful only when ownership semantics survive the trip.

## Done
This skill has materially contributed only when it changes a parser/policy/scene constraint, regression fixture, accessibility rule, or exact evidence boundary in the current mission. Naming the skill without such a consequence is decorative and stays dark.
