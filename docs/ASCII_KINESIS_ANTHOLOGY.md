# ASCII Kinesis Anthology

## Purpose

ASCII Kinesis is an anthology of embodied-motion experiments. Each experiment keeps its own durable source, structured data, compiled media, build path, provenance boundary, and receipt. Reusable lessons are promoted separately from specimens.

This extends, but does not replace, the existing UAPL lineage:

`PAPER / EMBODIED OBSERVATION -> UAPL -> ASCII CONTACT SHEET -> VECTOR NOODLE -> UAT -> GIF/VIDEO -> MOTION SPA`

The existing UAPL Motion SPA v1 remains a valid artifact forever. New anthology entries wrap the same source-first law with richer experiment metadata and may use MP4 instead of GIF.

## Anthology law

Every experiment gets one durable directory under:

`experiments/ascii-kinesis/<entry>/`

A specimen is evidence, not generalized doctrine. Generalized learnings live in `docs/ASCII_KINESIS_GENERALIZED_LEARNINGS.md` and cite the experiments that support them.

Do not overwrite old experiments to make a new theory look cleaner. Append a new experiment or new manifest version.

## Repository specimen vs delivery artifact

The durable repository is the reconstruction and provenance home. A current experiment directory tracks enough material to reproduce and inspect the commissioned artifact without the original chat:

1. raw structured motion JSON;
2. authoritative UAPL pose source where a rig/pose model is used;
3. UAT timing opinion when timing is modeled;
4. actual compiled motion media (`.gif`, `.mp4`, or a later backward-compatible media type);
5. manifest with schema/version, source-evidence boundary, status, compatibility policy, and candidate learnings;
6. deterministic build/reconstruction source;
7. human-readable experiment README.

The **human delivery artifact** is an actual openable self-contained `*.motion.html` attachment. It contains the assembled animation/video, raw selectable ASCII contact sheet, raw JSON, source, and manifest. The repository builder may generate that envelope rather than tracking a second copy of a large embedded-media file.

A convenience `contact-sheet.txt` may likewise be generated deterministically from the tracked source. The raw contact sheet remains durable because its literal text is embedded in the generated delivery envelope and reproducible from the tracked source.

Chat code blocks are not the delivery surface. Local scratch is not persistence proof.

## Backward compatibility law

The format may evolve aggressively but must remain backward compatible.

- New readers/builders MUST accept older anthology entry versions.
- New versions are additive by default.
- Existing UAPL 1 / UAT 1 sources remain interpretable without migration.
- Any previously delivered self-contained HTML artifact must continue to open without a network dependency.
- New views or richer JSON may not make old required fields ambiguous.
- If a future representation cannot preserve an old field directly, it must provide a lossless adapter/read path rather than declaring the old entry obsolete.
- Existing experiments are immutable evidence; corrections are appended as new evidence or new versions.

The compatibility canary is the pre-existing UAPL Motion SPA v1 implementation. ASCII Kinesis does not need to mutate that implementation merely to add anthology capability.

## Source / derivative law

ASCII source and structured pose data are motion authority. Contact sheets and videos are deterministic or inspectable presentations of that source.

A compiled video may interpolate or expose timing, but it may not invent a hidden joint, stance, gaze, contact, or semantic action that does not exist upstream.

## Delivery law

When Drew asks for "ASCII art" in the ASCII Kinesis / motion context, completion means an actual openable attachment bundle, not prose describing what a website could contain.

At minimum the human-facing SPA must expose:

- animation/video;
- raw ASCII contact sheet;
- raw JSON;
- source/manifest.

Repository persistence and user delivery are separate proof surfaces. A repository commit does not prove the user received an attachment; an attachment in chat does not prove the experiment is durable.

## Current anthology

- `001-backward-stairs` — backward stair descent, turn, and backward ascent; first explicit specimen of diagonal hip shift as a candidate preparatory kinematic atom.
