# ASCII Kinesis V2 Defense 001 — receipt

Status: RENDERED / STRUCTURALLY_TESTED / PENDING_REPO_PERSISTENCE

## Source
- The Spriters Resource — Cammy — *Super Street Fighter II: The New Challengers* — SNES — asset 5553
- https://www.spriters-resource.com/snes/supersf2/asset/5553/
- TSR metadata observed in Standard Chat: GIF, 1369×1209, 184.88 KB, uploader Lord Zymeth.

## Rights / evidence firewall
The entire sheet was treated as copyright-restricted evidence. No source pixels, palette, costume, face, exact silhouette, sheet layout, tracing, redistribution, or close imitation enters this repo example. Drew's work was not used. The shipped rig is an independently authored generic ASCII biped.

## Whole-sheet observation / inference split
OBSERVED: the whole sheet juxtaposes neutral/travel/action material with compact defensive-looking silhouettes, larger hit/knockdown/floor-level consequence silhouettes, and return-to-standing anchors; compact defense preserves facing and a readable base, while consequence poses produce larger root-height/torso-axis/support-spread changes. Source-authentic exposure timing was not measured.

INFERRED minimal-maximal principle: **guard and hit reaction fork at support authority**. Contact can compress a guard while support still owns the root. The sequence becomes a true hit reaction only when support authority breaks. Recovery begins at the first trustworthy new plant, before the torso necessarily looks fully upright.

UNKNOWN: source-authentic chronology, hitboxes/contact point, exact support foot, force magnitude, hit-stop duration, and source-authentic frame exposure.

## Decisive key timing
All timing is INFERRED using PoseLab V1 STREET_FIGHTER/CAPCOM. `1s/2s/4s` means ONES/TWOS/FOURS, never seconds.

- D001-K0 READY — FOURS — INFERRED
- D001-K1 BRACE — FOURS — INFERRED
- D001-K2 GUARD_CONTACT — ONES — INFERRED
- D001-K3 COMPRESSION_HOLD — TWOS — INFERRED
- D001-K4 SUPPORT_BREAK — ONES — INFERRED
- D001-K5 STAGGER_TRAVEL — TWOS — INFERRED
- D001-K6 RECOVERY_PLANT — ONES — INFERRED
- D001-K7 RESTACK — TWOS — INFERRED
- D001-K8 READY_REENTRY — FOURS — INFERRED

## Motion Dungeon compile
`AUTHORED ASCII KEYS -> EXPLICIT HOLDS/TIMING -> DETERMINISTIC CONNECTIVE MOTION -> ASCII-ONLY FRAME RENDER -> MP4 -> SPA`

Topology-safe connector rule: interpolate joint geometry only when `support_contact`, `contact_state`, and `root_state` are unchanged across adjacent decisive keys; otherwise hard-cut at the causal join. This prevents transitions from inventing support/contact/root state.

- Embedded MP4 SHA-256: `8b0cde408e9b3597b875beb37d2d52a62704f4ec93b636b4d7e595bf57c2eef9`
- Embedded MP4 bytes: `11653`
- semantic frames per loop: `24`
- compiled video frames: `96`
- ASCII sheet SHA-256: `b2c17db8202e639c6b5b465910b8795afe3803658987ebf6760ee77da77b3d9e`
- deterministic rebuild check: two successive local builds produced the identical MP4 hash above.

## Contract test boundary
The exact logic from `tools/test_ascii_kinesis_swarm_contract_v2.py` was executed locally against this new entry and passed. Repository-wide remote execution is not callable through the current Standard Chat GitHub write connector, so that broader execution boundary remains explicitly unclaimed.

## Correction hooks
KEEP / REJECT / EXAGGERATE / COMPRESS / RETIME / CHANGE SOURCE / PROMOTE / SPAWN VARIANT / FIX BLOCKER / RERUN
