# ASCII Kinesis V2 — Airborne 007 — Landing Pays Vertical Debt

Status: QUALITY_PASS_PENDING_REPO
Lane: JUMP / AIRBORNE / LANDING / VERTICAL FORCE
Repo path: `experiments/ascii-kinesis/v2-airborne-007-landing-pays-vertical-debt/`
Ship commit: PENDING

## Minimal-maximal unit

**LANDING PAYS VERTICAL DEBT BEFORE GROUND SPEED RE-ENTERS.**
One complete forward jump keeps horizontal intent legible through the arc, but the root cannot resume full ground-travel spacing until first contact, landing compression, and a small grounded rebound have visibly paid the remaining downward-speed cost.

## Source / rights

- The Spriters Resource asset 154243 — Sonic — Sonic Advance 2 — Game Boy Advance
- Source: https://www.spriters-resource.com/game_boy_advance/sonicadv2/asset/154243/
- Complete sheet: 1268×1348 PNG, 312.74 KB, uploaded by IceisNice.
- Whole-sheet evidence mode: fresh Standard Chat whole-sheet visual inspection plus source-page Jump preview / family notes.
- No source pixels, palette, character contour, costume, exact silhouette, frame layout, tracing, redistribution, or close imitation enter this specimen. Drew work was not used.

## Timing

Every decisive key is INFERRED / STREET_FIGHTER-CAPCOM. `1s/2s/4s` means ONES/TWOS/FOURS, never seconds.

- A007-K0 READY_STRIDE — FOURS / INFERRED
- A007-K1 CROUCH_LOAD — FOURS / INFERRED
- A007-K2 LAUNCH — ONES / INFERRED
- A007-K3 RISE — TWOS / INFERRED
- A007-K4 APEX_HANG — FOURS / INFERRED
- A007-K5 AIR_COMPACT — TWOS / INFERRED
- A007-K6 DESCENT_OPEN — TWOS / INFERRED
- A007-K7 PRECONTACT — TWOS / INFERRED
- A007-K8 CONTACT — ONES / INFERRED
- A007-K9 LAND_COMPRESSION — FOURS / INFERRED
- A007-K10 REBOUND_RESTACK — TWOS / INFERRED
- A007-K11 GROUND_REENTRY — TWOS / INFERRED
- A007-K12 RETURN_STRIDE — FOURS / INFERRED

## Quality gates

Tango: SATISFIED after three inspections. Iteration 1 corrected ambiguous planted-foot/support truth at ground re-entry; iteration 2 inspected the rerendered full arc and landing window and found no material defect; iteration 3 re-inspected final encoded LOAD/APEX/LAND_COMPRESSION frames at 480×270 and found no material readability regression. Silhouette, load transfer, contact/support, follow-through, recovery, carried cost, arc decisiveness, and connector discipline all PASS.

Noodle Queen: PASS after final Tango. Visible reasons: specific vertical-debt idea; distinct load/apex/contact/compression/rebound silhouettes; support acquisition does not magically erase downward speed; grounded rebound never becomes a fake second jump; horizontal intent resumes only after visible recovery cost; no decorative/source-style/interpolation theater remained.

## Persistence

Repository readback: PENDING
Issue #343 receipt: PENDING
Contract test: candidate-local PASS using exact fetched `tools/test_ascii_kinesis_swarm_contract_v2.py` against this complete five-file candidate. Fresh GitHub main readback confirms the repository-wide first boundary remains pre-existing `v2-airborne-005-side-support-gates-second-impulse`, which has no `*.motion.html`; a global run would stop there before reaching 007.
Correction hooks: KEEP / REJECT / EXAGGERATE / COMPRESS / RETIME / CHANGE SOURCE / PROMOTE / SPAWN VARIANT / FIX BLOCKER / RERUN

## Media inspection

ffprobe: H.264, 480×270, yuv420p, 24 fps, 80 frames, 3.333333 s. Media SHA-256 `071201641fe85b243403b7287a24572a61109f9d035a8c65735869d4faa672a1`; 18,192 bytes. Actual rendered motion inspected before approval.
