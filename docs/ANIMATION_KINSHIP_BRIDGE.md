# Animation Kinship Bridge v2

Status: OPTIONAL SIBLING-EVIDENCE CONTRACT

The bridge lets ASCII Kinesis, Vector Noodle, Pose Lab, and other animation systems discuss the same decisive states without sharing runtimes or silently transferring authority.

General animation authority:

`skills/motion-direction/SKILL.md`

Current bridge schema remains compatible with `ascii-kinesis-kinship-bridge.v1`; new readers must also honor the source-role law below.

## Core correction

**A timestamp is not timing authority.**

Frame addresses, exact source times, and observed spacing may be preserved as provenance so a worker can recover the same evidence. They become authoritative animation timing only when the current commission classifies that source as `TIMING_REFERENCE` or `FULL_PERFORMANCE_REFERENCE` for the relevant timing fact.

For Drew-performed reference video, default role is:

`POSE_REFERENCE + CONTACT_REFERENCE`

unless the commission explicitly assigns timing authority too.

Therefore the bridge may preserve photographic/video key spacing while the direction worker legitimately authors completely different animation timing.

## What the bridge may carry

- source-system identity;
- source specimen ID;
- source media hash;
- source roles;
- ordered key IDs;
- readable key names;
- kinship/phase/causal roles;
- source frame addresses;
- exact source timestamps;
- pose/contact observations;
- optional observed hold/exposure data;
- timing provenance;
- authored/generated status;
- explicit derived-direction profile identity;
- reversible mappings between sibling key IDs.

## Authority fields

Consumers should distinguish at minimum:

```json
{
  "source_roles": ["POSE_REFERENCE", "CONTACT_REFERENCE"],
  "timestamp_role": "POSE_ADDRESS",
  "timing_authority": false
}
```

or, when the commission truly assigns source timing:

```json
{
  "source_roles": ["FULL_PERFORMANCE_REFERENCE"],
  "timestamp_role": "TIMING_EVIDENCE",
  "timing_authority": true
}
```

Legacy v1 bridges without these fields are interpreted conservatively: timestamps are evidence addresses, **not automatic timing authority**.

## What the bridge is not

It is not:

- UAPL;
- UAT;
- Vector Noodle geometry;
- a rig;
- Motion Dungeon connective motion;
- a `.motion.html` deliverable;
- permission to import another renderer/art provider;
- permission to inherit visual canon;
- permission to preserve source timing merely because it is measurable.

Each consumer remains responsible for its own chosen representation and delivery contract.

## Timing / direction law

A direction worker may derive presentation/gameplay timing from pose evidence and should label it explicitly, for example:

- `DERIVED_UAT_OPINION`
- `DERIVED_ONES_TWOS_FOURS`
- `DERIVED_GAMEPLAY_RETIMER`
- `DERIVED_GAME_STYLE_PROFILE`

If the source has `timing_authority: false`, a derived profile is expected rather than a fidelity violation.

If the source has `timing_authority: true`, changing timing is a deliberate retiming operation and must be represented as such rather than silently claiming source fidelity.

## Key identity law

Preserve source key IDs or a reversible mapping so sibling systems can refer to the same decisive pose/contact moments.

The purpose is shared evidence identity, not shared animation timing.

## Visual / quarantine firewall

The bridge carries no positive visual canon unless an explicit clean `CANONICAL_VISUAL` reference is separately authorized.

A rejected/quarantined source may contribute failure metadata only. Do not transfer its silhouette, prop design, palette, motifs, UI treatment, or derived placeholder imagery through the bridge.

## Validation

Use:

```sh
python3 tools/validate_animation_kinship_bridge.py path/to/bridge.json
```

The structural validator proves shape/order only. It does not prove source-role correctness, timing authority, visual canon, artistic quality, or HEALTHY status.

## Historical v1 specimen correction

Producer:

`Valar05/deterministic-vector-engine` branch `fertile/flat-plane-paper-doll-v1`

Specimen:

`studies/fpv-thumbs-up-001/ascii-kinship.json`

Its selected photographic key spacing remains useful historical evidence and pose-address provenance. The old statement that this spacing automatically remains “source timing authority” is superseded.

Unless the originating commission explicitly assigned timing authority, consumers treat that spacing as non-authoritative evidence and may author a derived direction profile.

## Pocket law

```text
SHARE KEY IDENTITY, NOT HIDDEN AUTHORITY.
TIMESTAMPS CAN ADDRESS POSES WITHOUT OWNING TIMING.
DREW-PERFORMED VIDEO DEFAULTS TO POSE + CONTACT EVIDENCE.
DIRECTION IS AUTHORED UNLESS THE COMMISSION GIVES TIMING AWAY.
QUARANTINE NEVER CROSSES THE BRIDGE AS CANON.
```
