# UAPL — Universal ASCII Pose Language v1

Status: OPTIONAL REPRESENTATION CONTRACT

UAPL is a deterministic ASCII pose representation for animation work that benefits from a compact machine-readable rig/pose source.

It is **not** a universal animation intake requirement.

General animation judgment, source roles, timing authority, representation selection, visual canon, quarantine, body completeness, props, and game-style retargeting are governed by:

`skills/motion-direction/SKILL.md`

When the current commission selects UAPL/ASCII as an authoritative representation, this document defines that representation.

## Governing law inside a selected UAPL lane

Once valid UAPL has been deliberately authored/selected for a specimen, the ASCII text is authoritative for the pose geometry and pose order it explicitly contains.

No downstream Vector Noodle, rig, contact sheet, timing profile, GIF, video, or 3D reconstruction may silently add missing semantic pose information to **that UAPL specimen**. Missing required UAPL state must be amended upstream or explicitly represented in a different authoritative layer.

This law does not mean:

- every animation must begin in UAPL;
- every performance reference should be reduced to ASCII;
- Vector Noodle must always be downstream of UAPL;
- source-video timing belongs in UAPL;
- UAPL may erase occlusion, anatomy, canonical visual identity, or another load-bearing fact merely to stay ASCII.

A vector-first or rig-first pose master may be the correct authoritative source when the commission requires information that UAPL v1 does not carry well. UAPL may then be an optional abstract projection/teaching surface rather than the origin.

## Source vs direction

UAPL owns only its explicit pose graph and pose order.

Timing/direction is separate.

A UAT profile may be pinned to a UAPL hash, but timing provenance still follows Motion Direction source-role law:

- `POSE_REFERENCE` timestamps may locate observed poses without authorizing source timing;
- `TIMING_REFERENCE` or `FULL_PERFORMANCE_REFERENCE` may establish observed timing when the commission assigns that role;
- otherwise UAT is a derived animation-direction opinion.

`POSES BEFORE TIMING` remains valid **inside a UAPL workflow**. It is not permission to force UAPL into every workflow.

## Tiered escalation when UAPL is selected

0. **Evidence / embodied observation** — video, live body, sprite sheet, drawing, verbal commission, or another bounded source.
1. **UAPL ASCII pose source** — named rig graph + integer XYZ joint coordinates + ordered semantic poses.
2. **ASCII contact sheet** — deterministic human-facing rendering of that UAPL.
3. **Vector Noodle** — deterministic projection when vector geometry purchases useful capability.
4. **Rig / metarig** — hierarchical realization when constraints/deformation/3D relationships are required.
5. **UAT timing profile** — separate direction/timing opinion pinned to the exact UAPL hash.
6. **GIF / video / runtime** — compiled presentation.

Escalation is optional and capability-driven. If a higher representation is already the commissioned/canonical source, do not demote it merely to satisfy this ladder.

## UAPL v1 grammar

Comments begin with `#`. Blank lines are ignored. Significant tokens are space-separated ASCII.

```text
UAPL 1
NAME <program-name>
AXES X=right Y=up Z=forward
RIG <rig-name>
JOINT <joint-id> ROOT
JOINT <joint-id> <parent-joint-id>
...
POSE <pose-name>
<joint-id> <integer-x> <integer-y> <integer-z>
...
ENDPOSE
...
ORDER <pose-name> <pose-name> ...
ENDUAPL
```

Rules:

- exactly one root joint;
- joint graph is acyclic;
- every pose defines every joint exactly once;
- coordinates are signed integers;
- every pose appears exactly once in `ORDER`;
- fixed axes: +X right, +Y up, +Z forward;
- comments/whitespace do not change canonical identity;
- canonical text is hashed with SHA-256.

## UAT v1 — timing opinion

UAT is separate from UAPL.

```text
UAT 1
SOURCE <uapl-sha256>
FPS 60
STEP guard 4
STEP load 2
STEP contact 1
STEP recoil 2
STEP settle 3
ENDUAT
```

A UAT profile whose `SOURCE` does not equal the current canonical UAPL hash rejects with `UAT_SOURCE_MISMATCH`.

Hash binding proves which pose source the timing opinion targets. It does **not** prove that the timing was observed from a video. Timing provenance must be recorded separately according to Motion Direction.

## Human legibility

The deterministic ASCII renderer may use:

- `+` root joint;
- `o` internal joint;
- `*` leaf/end-effector;
- `- | / \\` bones.

The contact sheet is an inspectable view, not a replacement for facts the representation cannot express.

## Machine contract

Reference implementation: `functions/uapl_pose_language.js`.

It exposes:

- `parseUapl`
- `canonicalUapl`
- `uaplHash`
- `renderAsciiPose`
- `renderAsciiContactSheet`
- `toVectorNoodle`
- `parseUat`
- `expandTiming`

No model call is part of those deterministic operations.

## Determinism requirements

For the same canonical UAPL input:

- canonical text is identical;
- SHA-256 is identical;
- ASCII contact sheet is identical;
- Vector Noodle projection is identical;
- malformed/incomplete UAPL rejects with typed errors.

For the same UAPL + UAT:

- expanded tick sequence is identical;
- stale timing rejects rather than silently targeting changed poses.

## Potholes

- Do not infer missing Z depth from a 2D drawing.
- Do not let timing mutate pose geometry.
- Do not add agent-only semantics downstream.
- Do not assume fewer poses are always better; delete only redundant states.
- Do not assume more dimensions are automatically better.
- Do not use UAPL as an excuse to delete a load-bearing arm, occlusion, grip, or other information the commission requires.
- Do not promote source-video timestamps into timing authority unless their source role says so.

## Pocket doctrine

```text
SELECT REPRESENTATION BY THE COMMISSION.
WHEN UAPL IS SELECTED: UAPL IS DETERMINISTIC POSE SOURCE.
POSE SOURCE != TIMING AUTHORITY.
POSES BEFORE TIMING INSIDE THE UAPL LANE.
EVERY ESCALATION MUST PURCHASE CAPABILITY.
NO HIDDEN SEMANTIC INVENTION.
```
