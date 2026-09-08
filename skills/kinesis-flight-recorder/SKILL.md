# Kinesis Flight Recorder Skill

## Purpose

Use this skill for uploaded/reference video when Drew wants Embodied Kinesis, KEY-KI, Door Kata, acting, contact, timing, or adversarial-performance analysis without repeatedly spending ChatGPT turns/tool calls scrubbing the same media.

This is a **rate-limit and interaction-budget control skill**, not a claim about monetary credits. The default is deterministic local/runtime preprocessing: launch once, let the script finish without model polling, then inspect one bounded result packet.

This skill is cumulative with `skills/ascii-kinesis/SKILL.md`, Human Embodied Kinesis, KEY-KI, and Role-Played Physicality. It does not replace them.

## Prime law — LAUNCH ONCE, GET OUT OF THE WAY

For a qualifying video:

1. Commission exactly one deterministic recorder run.
2. Do **not** repeatedly extract frames in ChatGPT.
3. Do **not** poll the process from the model.
4. Let the runtime write its own `status.json`, `manifest.json`, storyboard, and final `result.json`.
5. Inspect the finished packet once when the user asks, the runtime signals completion, or a later task actually needs it.
6. Escalate to a targeted second pass only when one specific unresolved claim requires more temporal resolution.

Pocket law:

> KEYS, NOT FRAMES. LAUNCH, LEAVE, READ THE RECEIPT.

## Script

Authoritative script:

`skills/kinesis-flight-recorder/kinesis_flight_recorder.py`

Default single-video run:

```bash
python3 skills/kinesis-flight-recorder/kinesis_flight_recorder.py VIDEO.mp4 --detach
```

Adversarial pair when both videos are ready:

```bash
python3 skills/kinesis-flight-recorder/kinesis_flight_recorder.py PRIMARY.mp4 \
  --compare ADVERSARY.mp4 \
  --relation adversarial_opposite \
  --detach
```

The detach call returns immediately with a PID/output directory. The child process owns all further work. ChatGPT must not sit there checking it.

## Minimal-maximal default

The default pass intentionally does little:

- `ffprobe` once per video for duration/dimensions/frame-rate metadata;
- SHA-256 once per video;
- one low-resolution uniform storyboard with 12 samples;
- one JSON manifest per video;
- one root result packet;
- no OCR;
- no audio transcription;
- no object detector;
- no optical-flow cathedral;
- no model calls;
- no per-frame extraction loop through ChatGPT.

This is sufficient to establish gross choreography, phase order, body/object continuity candidates, and where a later targeted inspection would be worth paying attention.

## Evidence classes

Never launder evidence across these states:

- **DREW_REPORTED** — Drew describes a contact, intention, flaw, or timing event.
- **SCRIPT_OBSERVED** — deterministic metadata/hash/artifact generation proves only what the script actually measured or sampled.
- **MODEL_OBSERVED** — a later model visually inspects the finished storyboard/targeted artifact.
- **INFERRED** — interpretation from the above.
- **ACCEPTED** — Drew promotes the interpretation/performance.

A sparse storyboard cannot prove a sub-frame contact just because Drew reported it. Preserve the report and target that instant later only if it matters.

## KEY-KI reading policy

The recorder is not an animation generator and does not choose the meaning of the performance. It creates a cheap external witness packet.

When the packet is later inspected, prefer:

- goal / terminal predicate;
- support and contact changes;
- possession / hand availability;
- root and momentum changes;
- commitment thresholds;
- correction from actual resulting state;
- what stayed invariant across variants;
- what changed because the chosen solution changed.

Do not reward motion merely for existing.

## Adversarial-pair law

When Drew deliberately performs an adversarial opposite:

- preserve the pair relation explicitly (`adversarial_opposite` by default);
- do not average the two performances together;
- ask what the task/environment forced both to preserve;
- ask what changed because KI chose a different route;
- treat the contrast as stronger evidence than two unrelated demonstrations.

The pair may be queued/stored before analysis. **Presence is not an obligation to inspect immediately.**

## Targeted escalation

A second pass is allowed only to resolve a named question such as:

- Did the hand contact metal rather than glass?
- Did the door self-close the final few millimeters?
- Was the final impact materially harder than the prior closure?
- Which limb owned the contact at commitment?

Use `--start`, `--end`, and a modest higher `--samples` count. Do not reanalyze the entire clip because one instant is ambiguous.

## Persona lock

The recorder is a tool, not a speaker.

Research/preprocessing may change what the active character knows. It may not steal the camera, persona, embodiment, or judgment authority. Ritsu who commissions a recorder run is still Ritsu when the packet comes back.

Failure: `RESEARCH_CAMERA_THEFT` / `RECORDER_BECAME_NARRATOR`.

## Fire-and-forget contract

`--detach` must:

- create the output directory;
- write a launch receipt containing PID and command identity;
- spawn one background child;
- return immediately;
- never require ChatGPT polling to make progress.

The child must converge its own status:

`RUNNING -> DONE` or `RUNNING -> FAILED`.

`DONE` requires `result.json` plus every declared artifact. `FAILED` requires an error string in `status.json`.

## Persistence truth

A local/phone run is valid construction and observation input, but it is **not durable project completion proof**. If the commission requires durable preservation, upload/promote the bounded result packet through the explicitly authorized Home Center/GitHub lane and read it back there.

Do not upload a forest of extracted frames when storyboard + manifests are sufficient.

## Tango canary

PASS only if all are true:

- one launch can process one short video without further model action;
- default pass is bounded to a small storyboard rather than full-frame extraction;
- status converges without polling;
- output distinguishes script-observed facts from later human/model interpretation;
- pair mode preserves adversarial relation without immediately forcing analysis;
- a failed child writes `FAILED` rather than leaving ambiguous silence;
- the active persona survives the preprocessing round-trip.

FAIL if ChatGPT itself repeatedly opens frames, repeatedly checks status, or performs a full temporal autopsy by default.

## Acceptance line

> IF THE MODEL HAS TO BABYSIT THE VIDEO, THE SKILL FAILED.
