# ASCII Kinesis Skill

## Purpose

Use this skill for commissions that ask for ASCII art or ASCII animation as a durable motion artifact, especially when Drew references ASCII Kinesis, Vector Noodle, Embodied Kinesis, Pose Lab, contact sheets, or an experiment anthology.

This skill is cumulative with `skills/fortress-core/SKILL.md` and the UAPL contracts in `docs/UAPL_ASCII_POSE_LANGUAGE.md` and `docs/UAPL_MOTION_SPA.md`.

## Commission meaning

In this context, "make ASCII art" does NOT mean paste a code block into chat.

The commissioned delivery surface is an actual openable artifact, normally a self-contained SPA attachment, backed by persistent repository source.

A complete motion experiment includes:

1. an openable self-contained `.motion.html` delivered to the user;
2. raw selectable ASCII contact sheet;
3. raw structured JSON motion/experiment data;
4. UAPL/UAT source when applicable;
5. actual compiled motion media (GIF or MP4 is acceptable unless the user specifies one);
6. manifest/receipt;
7. repository persistence under the ASCII Kinesis anthology.

The SPA is what the human opens. The raw ASCII/JSON/UAPL are what future machines and humans can inspect. The media is compiled presentation.

The repository does **not** have to track a second giant copy of an embedded-media HTML envelope when it already tracks the raw source, structured data, compiled media, manifest, and a deterministic builder that regenerates the exact delivery class. Repository reconstruction proof and user attachment delivery are separate acceptance surfaces.

## Anthology rule

Each experiment gets its own immutable evidence directory:

`experiments/ascii-kinesis/<entry>/`

Do not turn a new experiment into a rewrite of an old specimen.

Generalized learnings belong in `docs/ASCII_KINESIS_GENERALIZED_LEARNINGS.md` and must cite supporting experiment IDs. One attractive specimen is evidence for a candidate learning, not automatic doctrine.

## Backward compatibility

ASCII Kinesis may evolve its envelope and structured data, but it is always backward compatible.

- Preserve existing UAPL 1 / UAT 1 semantics.
- Existing UAPL Motion SPA v1 artifacts remain valid.
- New entry readers must continue to accept old manifest versions.
- Prefer additive fields/views/media support over destructive schema replacement.
- Never require network access to open an already-complete self-contained experiment SPA.
- Never rewrite an old entry merely to satisfy the newest format.
- Previously delivered artifacts remain valid even when a newer repository version changes how equivalent envelopes are reconstructed.

## Source-before-presentation law

The raw ASCII/pose source is authoritative. Contact sheet, vector noodle, animation, video, and SPA may reveal or interpolate that source but may not silently invent motion semantics.

If a source video or embodied observation is private/user-supplied, persist the derived experiment and provenance boundary, not the raw private video, unless the user explicitly commissions source-video persistence.

## Default SPA views

Current anthology entries expose at least:

- **Animation** — actual assembled GIF/MP4/runtime playback;
- **ASCII contact sheet** — literal selectable characters;
- **Raw JSON** — structured rig, pose, timing, evidence, and compatibility data;
- **Source** — UAPL/UAT plus manifest.

Views may expand in later versions while older entries remain readable.

## Completion gate

Do not stop after source generation or a pasted code sample.

DONE for an ASCII Kinesis experiment requires:

- the requested artifact exists as a user-openable attachment;
- raw ASCII contact sheet exists in the delivery artifact and/or reproducible derivative;
- raw structured data exists;
- assembled media exists;
- the experiment reconstruction source and provenance exist in the persistent repository anthology;
- the skill/format compatibility rules remain intact;
- repository readback proves the exact durable entry/skill files exist;
- human acceptance remains distinct from machine completion.

Local scratch is useful for construction only and is never completion proof.
