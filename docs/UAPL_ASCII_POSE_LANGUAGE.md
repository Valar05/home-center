# UAPL — Universal ASCII Pose Language v1

UAPL is the lowest machine-readable animation representation in Pose Lab. It is intentionally plain ASCII, directly parseable by code, and readable by a human without an agent.

## Governing law

The ASCII text is authoritative source code.

No downstream vector noodle, rig, contact sheet, timing profile, GIF, video, or 3D reconstruction may add hidden semantic pose information. If information is missing, the compiler rejects or the source must be amended.

An agent may help author UAPL. An agent is not required to interpret UAPL after it exists.

## Tiered escalation

0. **Paper / embodied observation** — cheapest human thought surface. No machine contract yet.
1. **UAPL ASCII pose source** — named rig graph + integer XYZ joint coordinates + ordered semantic poses. This is the first authoritative machine contract.
2. **ASCII contact sheet** — deterministic human-facing rendering of the UAPL source. It shows all load-bearing states at once. It does not change the source.
3. **Vector Noodle** — deterministic projection of the same joint graph and coordinates into vector/structured geometry. Source SHA-256 travels with it.
4. **Rig / metarig** — deterministic skeletal realization from the Vector Noodle/UAPL graph. Bone direction comes from parent-child coordinates; roll/orientation uses a fixed compiler convention unless UAPL is later versioned to carry explicit orientation data.
5. **Timing profile (UAT)** — a separate ASCII opinion pinned to the exact UAPL SHA-256. It assigns exposure ticks to named poses without mutating pose geometry.
6. **GIF / video / runtime animation** — compiled presentation. It is not source truth.

The escalation rule is the same Drew uses for thought capture: do not pay for a higher-cost representation until the lower-cost representation has earned escalation.

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

- exactly one root joint
- joint graph must be acyclic
- every pose defines every joint exactly once
- coordinates are signed integers
- every pose appears exactly once in `ORDER`
- fixed axes: +X right, +Y up, +Z forward
- comments/whitespace do not change canonical identity
- canonical text is hashed with SHA-256

## Timing is separate

UAT v1 is deliberately not embedded in UAPL. A timing choice is an opinion about an exact pose source.

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

A UAT profile whose `SOURCE` hash does not equal the current canonical UAPL hash must reject with `UAT_SOURCE_MISMATCH`.

This makes the contact sheet primordial and the GIF derivative.

## Human legibility

The source names joints and poses directly. A deterministic renderer converts the integer joint graph into an ASCII contact sheet using only:

- `+` root joint
- `o` internal joint
- `*` leaf/end-effector
- `- | / \\` bones

The rendered contact sheet is inspectable by a person and reproducible byte-for-byte from canonical source.

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

No model call is part of these operations.

## Determinism requirements

For the same canonical UAPL input:

- canonical text is identical
- SHA-256 identity is identical
- ASCII contact sheet is identical
- Vector Noodle structure is identical
- malformed/incomplete state rejects with typed errors

For the same UAPL + UAT:

- expanded tick sequence is identical
- stale timing cannot silently target changed poses

## Potholes

- Do not confuse the ASCII renderer with the authoritative geometry. UAPL coordinates and rig graph are source; the contact sheet is a deterministic view.
- Do not infer missing depth from a 2D drawing. Z is explicit.
- Do not let GIF timing mutate pose geometry.
- Do not add agent-only annotations downstream.
- Do not assume fewer poses are always better; delete only when semantic/motion information survives.
- Do not assume more dimensions are automatically better; escalate only when the next representation purchases necessary capability.

## Pocket doctrine

```text
PAPER -> UAPL -> ASCII CONTACT SHEET -> VECTOR NOODLE -> RIG -> UAT -> GIF/VIDEO

SOURCE BEFORE OPINION.
POSES BEFORE TIMING.
NO HIDDEN AGENT INTERPRETATION.
EVERY ESCALATION MUST PURCHASE CAPABILITY.
```
