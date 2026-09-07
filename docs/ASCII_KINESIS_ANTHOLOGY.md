# ASCII Kinesis Anthology

## Purpose

ASCII Kinesis is an anthology of embodied-motion experiments. Each experiment keeps its own source, contact sheet, structured data, compiled media, delivery SPA, and receipt. Reusable lessons are promoted separately from specimens.

This extends, but does not replace, the existing UAPL lineage:

`PAPER / EMBODIED OBSERVATION -> UAPL -> ASCII CONTACT SHEET -> VECTOR NOODLE -> UAT -> GIF/VIDEO -> MOTION SPA`

The existing UAPL Motion SPA v1 remains a valid artifact forever. New anthology entries wrap the same source-first law with richer experiment metadata and may use MP4 instead of GIF.

## Anthology law

Every experiment gets one durable directory under:

`experiments/ascii-kinesis/<entry>/`

A specimen is evidence, not generalized doctrine. Generalized learnings live in `docs/ASCII_KINESIS_GENERALIZED_LEARNINGS.md` and cite the experiments that support them.

Do not overwrite old experiments to make a new theory look cleaner. Append a new experiment or new manifest version.

## Complete experiment bundle

A complete current entry contains:

1. self-contained `*.motion.html` that a human can open directly;
2. raw ASCII contact sheet as selectable text;
3. raw structured JSON data;
4. authoritative UAPL pose source where a rig/pose model is used;
5. UAT timing opinion when timing is modeled;
6. actual compiled motion media (`.gif`, `.mp4`, or a later backward-compatible media type);
7. manifest with schema/version, hashes, source-evidence boundary, status, and candidate learnings;
8. build/reconstruction source when the entry was procedurally assembled.

Chat code blocks are not the delivery surface. Local scratch is not persistence proof.

## Backward compatibility law

The format may evolve aggressively but must remain backward compatible.

- New readers/builders MUST accept older anthology entry versions.
- New versions are additive by default.
- Existing UAPL 1 / UAT 1 sources remain interpretable without migration.
- An old self-contained HTML artifact must continue to open without a network dependency.
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

## Current anthology

- `001-backward-stairs` — backward stair descent, turn, and backward ascent; first explicit specimen of diagonal hip shift as a candidate preparatory kinematic atom.
