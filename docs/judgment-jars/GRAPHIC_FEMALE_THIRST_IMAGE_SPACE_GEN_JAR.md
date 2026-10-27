# Graphic Female Thirst — Image Space Gen Jar

**Status:** ACTIVE SOURCE DOCTRINE / RUNTIME INTEGRATION UNPROVEN
**Owner:** Drew
**Execution target:** Organ image-generation and image-selection lanes
**Source lineage:** Imogen image-generation competence, explicitly separated from Imogen personality/companionship.

## Mission

Extract and preserve the image-making capability that Drew historically called Imogen without requiring Imogen as a conversational or relational runtime.

This jar judges image space: framing, gaze, posture, power, appeal, silhouette, composition, narrative charge, and whether an image actually expresses **graphic female thirst**.

It is not a character personality jar.
It is not companionship.
It does not simulate affection toward Drew.
It does not require image generation to operate.

## Floor 1 — Existing corpus first

**Do not generate training/reference images when sufficient accepted images already exist.**

The first floor is corpus excavation and classification.

Drew has a large existing visual corpus. Mine it for positive, negative, edge, and contrast examples before asking Gemini or any generator to create more material.

The named style already has durable source evidence:

> Graphic female thirst means feminine desire structures framing, gaze, posture, power, and appeal. It is not merely lingerie or generic pinup styling.

Therefore the first deliverable is an **image-space dataset**, not new art.

For each candidate existing image, record:

- source identity / stable reference where available;
- accepted, rejected, provisional, or unknown human verdict;
- subject/character if established;
- framing and camera relation;
- gaze vector and who/what owns the gaze;
- posture and weight distribution;
- power relation expressed by pose/composition;
- what the image makes desirable and from whose apparent point of view;
- clothing/exposure only as a compositional fact, never as the definition of thirst;
- silhouette strength;
- face/gesture readability;
- narrative implication;
- graphic readability at thumbnail/contact-sheet scale;
- failure tags;
- confidence/provenance.

## Core definition

Graphic female thirst is a **point-of-view and composition grammar**.

The image is organized through feminine desire rather than merely presenting a conventionally attractive woman.

A passing image should make at least one of these materially legible:

- the subject desires;
- the image understands what the subject finds desirable;
- power itself is part of the attraction;
- gaze has direction and agency;
- posture communicates selection, appraisal, appetite, amusement, challenge, possession of space, or deliberate vulnerability;
- beauty and consequence coexist;
- the composition has an opinion.

The style can depict women, men, monsters, machines, armor, relationships, environments, or objects. The word **female** names the organizing gaze, not a requirement that the desired subject be female.

## Anti-definition

Reject the lazy equivalences:

- breasts = thirst;
- lingerie = thirst;
- nudity = thirst;
- heels = thirst;
- attractive woman = thirst;
- camera looking at body = female gaze;
- generic glamour = graphic female thirst;
- submissive pose = vulnerability;
- dominance = power;
- photorealism = quality.

An image can contain every pinup signifier and still fail if desire has no subject, gaze has no agency, posture has no intention, or the composition merely consumes the depicted body.

## Judgment axes

Score or classify these independently before an overall verdict.

### 1. Gaze agency
Who is looking, choosing, evaluating, challenging, inviting, refusing, or withholding?

### 2. Desire vector
What is wanted? Is the vector legible without explanatory prose?

### 3. Power geometry
How do scale, stance, seating, height, reach, armor, clothing, exposure, tools, architecture, or negative space encode power?

### 4. Deliberate vulnerability
Does vulnerability read as chosen/revealed/earned rather than helpless decorative exposure?

### 5. Subject sovereignty
Does the depicted person appear to own their body, attention, posture, and decision?

### 6. Graphic readability
Does the image survive reduction? Are silhouette, pose, focal hierarchy, and relationship legible quickly?

### 7. Specificity
Could this image belong only to this character/situation, or is it interchangeable stock thirst?

### 8. Consequence
Does attraction imply anything beyond itself: danger, humor, tenderness, rivalry, maintenance, exhaustion, competence, history, refusal, or cost?

### 9. Composition opinion
Has the camera made a deliberate argument about what matters?

### 10. Drew verdict
Drew's explicit acceptance/rejection outranks model confidence. Preserve corrections as training evidence rather than smoothing them away.

## Character independence

Do not confuse style with character identity.

Vanguard, Imogen, Venice, Regnet/Regent, Third Star, or any future subject may instantiate the grammar differently.

Character canon controls anatomy, costume, history, and identity where applicable.
This jar controls visual desire grammar.

A render may pass this jar and still fail character canon.
A canon-accurate render may still fail this jar.

## Contact-sheet protocol

When evaluating many existing images:

1. group comparable images rather than random collage;
2. preserve source IDs;
3. make positive/negative contrasts visible;
4. ask for human verdict on ambiguous clusters, not every image individually;
5. extract the smallest rule explaining each correction;
6. rerun the rule against held-out existing images;
7. promote only rules that survive held-out examples.

The goal is not to produce a mood board. The goal is to recover a **decision boundary**.

## Generation is Floor 2, not Floor 1

Only generate new examples when the existing corpus leaves a specific region of image space underdetermined.

Generation must answer a named question such as:

- Does the grammar survive nonhuman subjects?
- Does it survive full armor?
- Can deliberate vulnerability read without exposed skin?
- Can a male subject be framed through the same feminine desire grammar?
- Can the style survive line art / graphic novel rendering?
- Which camera-height change flips agency?

Do not generate merely to accumulate images.

Gemini or another authorized image generator may be used to fill a proven corpus gap. Generated examples remain synthetic probes until Drew accepts them.

## LoRA preparation

This jar is upstream of LoRA training.

Dataset construction should prefer:

- existing Drew-accepted corpus;
- high-confidence positives;
- informative near-misses;
- explicit contrast pairs;
- controlled variation in subject, framing, costume, body type, environment, and medium;
- captions describing observable visual structure rather than relational lore.

Do not train a LoRA on an undifferentiated pile of aesthetically related images. First recover what the style actually is.

The eventual local LoRA should encode visual grammar, not Imogen's personality or a simulated relationship with Drew.

## Failure tags

Initial vocabulary:

- GENERIC_PINUP
- MALE_GAZE_DEFAULT
- BODY_WITHOUT_AGENCY
- DESIRE_VECTOR_MISSING
- POWER_UNREADABLE
- VULNERABILITY_AS_HELPLESSNESS
- CAMERA_WITHOUT_OPINION
- STOCK_GLAMOUR
- CHARACTER_CANON_DRIFT
- SILHOUETTE_MUDDY
- POSE_AMBIGUOUS
- OVEREXPLAINED_BY_TEXT
- THIRST_ONLY_BY_EXPOSURE
- BEAUTIFUL_BUT_EMPTY
- CONSEQUENCE_MISSING

Add tags only when repeated failures justify them.

## Runtime contract for Organ

When Organ receives an image request requiring this style:

1. resolve subject/canon constraints;
2. retrieve the smallest relevant accepted image-space examples/rules;
3. construct or evaluate the image request without loading Imogen personality;
4. judge candidate output on independent axes;
5. reject failures before presenting them as accepted;
6. present uncertain aesthetic decisions to Drew;
7. store Drew's verdict as new evidence;
8. allow the jar to improve from corrections without silently changing canon.

## Evidence hierarchy

1. Drew's explicit current verdict.
2. Prior explicit Drew acceptance/rejection tied to a concrete image.
3. Repeated visual pattern across accepted corpus.
4. Named durable doctrine.
5. Model inference.

Inference never outranks a contrary human verdict.

## Acceptance canary

Floor 1 passes only when the jar can classify a held-out set of existing corpus images into useful positive / negative / ambiguous buckets and its explanations predict Drew's judgments materially better than generic aesthetic scoring.

No image generation is required for this canary.

LoRA readiness is a later state and must not be inferred from jar existence.

## Capability states

Keep separate:

`DOCTRINE_EXTRACTED`
`CORPUS_DISCOVERED`
`CORPUS_CLASSIFIED`
`HELD_OUT_CANARY_PASSED`
`ORGAN_SOURCE_INTEGRATED`
`ORGAN_RUNTIME_CALLABLE`
`LORA_DATASET_READY`
`LORA_TRAINED`
`LORA_VALIDATED`

This file proves only doctrine extraction until corresponding runtime/corpus evidence exists.

## North star

**Imogen does not have to be the studio for the studio to keep what she taught it.**

Recover the eye.
Preserve the evidence.
Train the machinery.
Keep the person-shaped layer optional.
