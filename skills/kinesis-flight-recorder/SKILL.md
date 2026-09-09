# Kinesis Flight Recorder Skill

Status: VIDEO EVIDENCE PREPROCESSOR

## Purpose

Use this skill for uploaded/reference video when Drew wants Embodied Kinesis, KEY-KI, Door Kata, acting, contact, pose extraction, or adversarial-performance analysis without repeatedly spending model turns scrubbing the same media.

This is a **bounded evidence-recorder skill**, not an animation-direction skill.

It inherits:

- `skills/fortress-core/SKILL.md`
- `skills/motion-direction/SKILL.md`

ASCII Kinesis/UAPL is optional and applies only when the current commission selects that representation.

## Prime law — KEYS, NOT FRAME AUTOPSY

For a qualifying video:

1. Commission one deterministic recorder pass.
2. Do not repeatedly extract/open frames in model turns.
3. Do not poll a background process from the model.
4. Let the runtime write its own status/manifest/storyboard/result packet.
5. Inspect that bounded packet once when it is actually needed.
6. Escalate only to answer one named unresolved temporal/pose/contact question.

Pocket law:

`KEYS, NOT FRAMES. LAUNCH, LEAVE, READ THE RECEIPT.`

## Source-role correction

The recorder observes evidence; it does not silently assign animation authority.

Default for a Drew-performed action video used to make an animation:

`source_roles = [POSE_REFERENCE, CONTACT_REFERENCE]`

unless the commission explicitly adds `TIMING_REFERENCE` or `FULL_PERFORMANCE_REFERENCE`.

Therefore:

- frame/time addresses identify where evidence was observed;
- a storyboard may reveal pose order/contact/load candidates;
- measured clip cadence is **not automatically animation timing**;
- the downstream direction worker authors timing/spacing/holds/anticipation/recoil/recovery by default.

`TIMESTAMP != TIMING AUTHORITY`

The recorder may preserve exact timestamps because they are useful addresses. It must never rewrite their role merely because they are precise.

## Script

Authoritative script:

`skills/kinesis-flight-recorder/kinesis_flight_recorder.py`

Default single-video run:

```bash
python3 skills/kinesis-flight-recorder/kinesis_flight_recorder.py VIDEO.mp4 --detach
```

Adversarial pair:

```bash
python3 skills/kinesis-flight-recorder/kinesis_flight_recorder.py PRIMARY.mp4 \
  --compare ADVERSARY.mp4 \
  --relation adversarial_opposite \
  --detach
```

The detach call returns immediately with PID/output directory. The child owns remaining work; the model does not babysit it.

## Minimal-maximal default

Default deterministic pass:

- `ffprobe` once per video for duration/dimensions/frame-rate metadata;
- SHA-256 once;
- one low-resolution uniform storyboard with 12 samples;
- one JSON manifest per video;
- one root result packet;
- no OCR;
- no audio transcription;
- no object detector;
- no optical-flow cathedral;
- no model calls;
- no per-frame extraction loop through ChatGPT.

This is enough to establish gross choreography, pose/contact candidates, phase order, body/object continuity, and where one targeted inspection might be worth doing.

It is not enough to claim source-authentic animation timing unless timing authority was part of the commission and the evidence resolution actually supports the timing claim.

## Evidence classes

Never launder evidence across states:

- **DREW_REPORTED** — Drew describes contact, intention, flaw, pose, or timing.
- **SCRIPT_OBSERVED** — deterministic metadata/hash/sampling proves only what was measured/sampled.
- **MODEL_OBSERVED** — later visual inspection of the bounded packet.
- **INFERRED** — interpretation from evidence.
- **ACCEPTED** — Drew promotes an interpretation/performance.

Source role is a separate axis. A fact can be `SCRIPT_OBSERVED` and still be only a `POSE_ADDRESS`, not `TIMING_REFERENCE`.

A sparse storyboard cannot prove sub-frame contact or exposure timing merely because a frame-rate number exists.

## Pose/contact reading policy

When the packet is later inspected, prefer facts that survive retiming:

- decisive pose states;
- goal / terminal predicate;
- support/contact changes;
- possession / hand availability;
- root and momentum changes;
- load path;
- commitment thresholds;
- correction from actual resulting state;
- invariants across variants;
- what changed because a different solution was chosen.

Do not reward motion merely for existing.

## Adversarial-pair law

When Drew performs an adversarial opposite:

- preserve the relation explicitly (`adversarial_opposite` by default);
- do not average performances;
- ask what task/environment forced both to preserve;
- ask what changed because KI chose a different route;
- treat contrast as evidence about pose/causal structure, not automatic instruction to average timing.

Presence is not an obligation to inspect immediately.

## Targeted escalation

A second pass exists only for a named question, e.g.:

- Did the hand contact metal rather than glass?
- Did the door self-close the final few millimeters?
- Which limb owned contact at commitment?
- Is this apparent pose change real or sampling aliasing?

Use `--start`, `--end`, and a modest higher `--samples` count. Do not reanalyze the whole clip because one instant is ambiguous.

If the question is animation timing, first verify the commission actually assigned source timing authority. Otherwise the correct downstream action is direction, not more forensic sampling.

## Output source-role ledger

Whenever the packet is promoted into animation work, carry or add fields equivalent to:

```json
{
  "source_roles": ["POSE_REFERENCE", "CONTACT_REFERENCE"],
  "timestamp_role": "POSE_ADDRESS",
  "timing_authority": false
}
```

If timing is explicitly source-owned, say so instead of inferring it from metadata.

## Persona lock

The recorder is a tool, not a speaker.

Preprocessing may change what the active character knows. It may not steal persona, camera, embodiment, or judgment authority.

Failures: `RESEARCH_CAMERA_THEFT`, `RECORDER_BECAME_NARRATOR`.

## Fire-and-forget contract

`--detach` must:

- create output directory;
- write launch receipt with PID + command identity;
- spawn one background child;
- return immediately;
- never require model polling.

Child state converges:

`RUNNING -> DONE` or `RUNNING -> FAILED`.

`DONE` requires `result.json` plus declared artifacts. `FAILED` requires an error string in `status.json`.

## Persistence truth

Local/phone execution is valid construction/observation input but not durable completion proof.

When the commission requires preservation, promote the bounded packet through the authorized Home Center/GitHub lane and read it back there.

Do not upload a forest of frames when storyboard + manifests + a targeted crop answer the question.

## Tango canary

PASS only when:

- one launch processes one short video without model babysitting;
- default output is bounded;
- status converges without polling;
- evidence class and source role remain distinct;
- timestamps remain addresses unless timing authority is explicit;
- pair relation is preserved without forced analysis;
- failures converge to `FAILED`;
- active persona survives preprocessing.

FAIL on repeated model frame extraction, full temporal autopsy by default, or `VIDEO_TIMING_LEAK`.

## Acceptance line

`IF THE MODEL HAS TO BABYSIT THE VIDEO, THE RECORDER FAILED.`

`IF A TIMESTAMP SILENTLY BECOMES AN EASING CURVE, MOTION DIRECTION FAILED.`
