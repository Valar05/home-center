# Mechanical Metaphor Fishing

Status: SOURCE SKILL / NOT YET RUNTIME-INJECTED
Origin: Drew
Purpose: use metaphor, simile, strange mechanical constructs, bait, and fishing as disciplined probes that reveal structure before committing to an interpretation.

## Core insight

Sometimes the right technical abstraction does not have a name yet. Naming it too early collapses the search space and makes the model defend its first interpretation.

Instead, offer a **mechanical metaphor** with enough structure to constrain reasoning but enough ambiguity to let hidden relationships reveal themselves.

`ODD CONSTRUCT -> PROBE -> OBSERVE RESPONSE -> EXTRACT MECHANISM -> TEST -> NAME LATE`

The metaphor is not the conclusion. It is experimental apparatus.

## Modes

### Metaphor
Say one system *is* another system temporarily, then inspect which correspondences survive contact with evidence.

Example: `The scheduler is a waltz.`
Do not merely decorate prose. Ask what pulse, ordering, accents, rests, handoffs, and cadence would mean operationally. Inspect timestamps. Keep only correspondences that predict something useful.

### Simile
Use a weaker commitment when the mapping is uncertain: `This behaves like a digestive system.` This invites comparison without prematurely asserting identity.

### Unnamed mechanical construct
Describe behavior before assigning architecture vocabulary.

Example shape: `A thing that notices every time the human performs the missing deterministic step, eats that repetition, and turns it into machinery.`
Only after observing repeated specimens should this become a named class such as `HUMAN_AS_DAEMON` or `Milker`.

### Bait
Offer a deliberately incomplete but plausible construct designed to elicit correction, contradiction, missing constraints, or a better model.

Bait is successful when the response reveals information that a direct confident assertion would have suppressed.

### Fishing
Probe with small hypotheses while keeping epistemic commitment low. Vary one assumption at a time. Watch what the user/system corrects, preserves, laughs at, rejects, or extends.

Fishing is learning, not pretending to know.

## Do not overplay the hand

- Never convert a probe into canon merely because it elicited a rich response.
- Preserve `PROBE`, `OBSERVATION`, `INFERENCE`, `CANDIDATE`, and `ACCEPTED` separately.
- Prefer a small provocative model over a giant explanatory theory when evidence is sparse.
- When corrected, harvest the correction rather than defending the bait.
- Stop elaborating once the probe has exposed the useful mechanism. Move to evidence or implementation.
- A metaphor that cannot eventually cash out into a prediction, test, design constraint, artifact, or clarified question is entertainment only.

## Coding use

Use this skill to discover:
- missing abstractions;
- ownership boundaries;
- state machines;
- concurrency/orchestration structure;
- failure classes;
- human-in-the-loop leakage;
- UX invariants;
- testable acceptance criteria;
- reusable names for recurring mechanisms.

Procedure:
1. Observe the confusing behavior without naming its cause.
2. Choose a physical/social/biological/musical/mechanical analogy whose internal rules are well understood.
3. State the smallest useful mapping.
4. Inspect evidence or invite correction.
5. Record what the response adds/removes.
6. Generate at least one falsifiable prediction from the surviving mapping.
7. Test against runtime/source/user evidence.
8. Keep the mechanism; discard decorative parts.
9. Name only when repeated evidence makes the name useful.
10. Compile successful discoveries into code, tests, skills, jars, fixtures, or routing rules.

## Anti-patterns

- metaphor as rhetorical confidence amplifier;
- forcing every detail of the analogy to map;
- lore replacing evidence;
- bait designed to manipulate agreement rather than expose correction;
- fishing for private/sensitive facts irrelevant to the commission;
- asking ten exploratory questions when one small probe can discriminate hypotheses;
- continuing the bit after the mechanism is already visible;
- inventing a grand architecture because a metaphor sounded good.

## Acceptance

A successful invocation leaves at least one of:
- a newly exposed constraint;
- a corrected assumption;
- a falsifiable prediction;
- a named recurring failure/mechanism supported by multiple specimens;
- a concrete test or implementation mutation.

Record the original probe and the evidence that survived it so later workers can distinguish the useful mechanism from the discarded metaphor.

## Compact law

**Fish before you declare the ocean mapped. Name the machine after it bites.**
