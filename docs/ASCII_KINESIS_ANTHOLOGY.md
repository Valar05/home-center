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

The **human delivery artifact** is an actual openable self-contained `*.motion.html` attachment or repository-generated equivalent. It contains the assembled motion, raw selectable ASCII contact sheet, and raw JSON. The repository builder may generate that envelope rather than tracking a second giant copy of embedded media.

A convenience `contact-sheet.txt` may likewise be generated deterministically from the tracked source. The raw contact sheet remains durable because its literal text is embedded in the generated delivery envelope and reproducible from the tracked source.

Chat code blocks are not the delivery surface. Local scratch is not persistence proof.

## Backward compatibility law

The format may evolve aggressively but must remain backward compatible.

- New readers/builders MUST accept older anthology entry versions.
- New versions are additive by default.
- Existing UAPL 1 / UAT 1 sources remain interpretable without migration.
- Any previously delivered self-contained HTML artifact must continue to open without a network dependency.
- New fields may not make old required fields ambiguous.
- If a future representation cannot preserve an old field directly, it must provide a lossless adapter/read path rather than declaring the old entry obsolete.
- Existing experiments are immutable evidence; corrections are appended as new evidence or new versions.

The compatibility canary is the pre-existing UAPL Motion SPA v1 implementation. ASCII Kinesis does not need to mutate that implementation merely to add anthology capability.

## V2 swarm SPA contract

Starting with the 2026-09-07 swarm restart, every new mining specimen follows `docs/ASCII_KINESIS_SWARM_CONTRACT_V2.md`.

Its human-facing SPA has **exactly three primary tabs** in this order:

1. **ASCII** — complete literal selectable/copyable contact-sheet text with preserved alignment.
2. **JSON** — structured rig, timing, provenance, rights boundary, compatibility, and manifest/receipt data.
3. **VIDEO** — actual compiled MP4 generated solely from the abstract ASCII rig and timing through the Motion Dungeon production method.

Old v1 artifacts with a different tab layout remain valid. V2 is additive and never invalidates them.

For V2 mining runs, Drive studies and issue comments are supporting evidence only. The repository example is the commissioned product.

## Source / derivative law

ASCII source and structured pose data are motion authority. Contact sheets and videos are deterministic or inspectable presentations of that source.

A compiled video may interpolate or expose timing, but it may not invent a hidden joint, stance, gaze, contact, or semantic action that does not exist upstream.

For copyrighted sprite-sheet mining, source sprites remain evidence only. No source pixels, exact contours, palette, layout, tracing, redistribution, or close imitation enter the specimen.

## Delivery law

When Drew asks for "ASCII art" in the ASCII Kinesis / motion context, completion means an actual openable artifact backed by a durable repository entry, not prose describing what a website could contain.

For new V2 swarm examples, the exact acceptance surface is `ASCII | JSON | VIDEO` and the video is mandatory.

Repository persistence and user delivery are separate proof surfaces. A repository commit does not prove the user received an attachment; an attachment in chat does not prove the experiment is durable.

## Current anthology

- `001-backward-stairs` — backward stair descent, turn, and backward ascent; historical v1 specimen of diagonal hip shift as a candidate preparatory kinematic atom.

## Restarted swarm namespace

New V2 mining specimens use unique lane-scoped names such as:

`v2-strikes-001-<slug>`

`v2-locomotion-001-<slug>`

Each lane restarts at `001` without overwriting historical material or another lane's sequence.

## Parked next-system handle

`terminal-native ASCII animation/game engine`

The eventual extraction target is a terminal-native interactive engine driven by the same literal ASCII scene/rig/timing substrate. It is parked until repeated V2 specimens prove which engine primitives are actually shared.
