# ASCII Kinesis V2 Airborne 001 — Receipt

Status: VERIFIED
Experiment: `v2-airborne-001-air-task-rides-root-arc`
Lane: `airborne` — JUMP / AIRBORNE / LANDING / VERTICAL FORCE
Minimal-maximal unit: **AIR TASK RIDES THE ROOT ARC** — a local airborne pose/task change may alter limb organization while the authored ballistic root arc continues; it must not manufacture a second vertical launch.

## Source / whole-sheet evidence

- Source: The Spriters Resource — **X**, *Mega Man Xtreme 2*, Game Boy / GBC, asset `501`.
- Page: `https://www.spriters-resource.com/game_boy_gbc/mmxtreme2/asset/501/`
- Exact source bytes resolved through Home Center -> primary-phone from TSR asset URL: PNG `550x405`, `63,428` bytes, SHA-256 `2eaa11669c3b44c61b2dff1ff97fb81a358da45e16b194c9d92076a3569f4f22`.
- Whole-sheet boundary: the entire static sheet was treated as a pose corpus, including grounded/low-body, travel, airborne, task/arm-cannon, recovery/return, and effect families. The sheet is not assumed to be a chronological timeline.
- Rights firewall: copyrighted commercial-game sprite art was used only as evidence for critical motion analysis. No source pixels, palette, contours, sprite layout, tracing, redistributed frame, or close character-specific imitation enters this experiment. Drew work used: **false**.

## Evidence split

OBSERVED from the whole sheet:
- both grounded/low-body and clearly airborne compact/extended pose families exist;
- facing remains readable across airborne local limb reorganizations;
- airborne-compatible upper-body task changes coexist with non-task airborne organizations;
- grounded recovery/return families coexist with airborne families;
- the static PNG establishes no source-authentic exposure duration.

INFERRED for the abstract specimen:
- one transferable causal sequence: LOAD -> LAUNCH -> RISE -> APEX_READ -> AERIAL_TASK_CHANGE -> DESCENT_OPEN -> PRECONTACT -> CONTACT -> LAND_COMPRESSION -> REBOUND -> RETURN_STABLE;
- the aerial task rides a single root arc and creates no second vertical impulse;
- contact and compression are separate authored keys;
- all cadence uses PoseLab V1 `STREET_FIGHTER/CAPCOM` because source timing is unavailable.

UNKNOWN:
- exact in-game frame exposures and ordering of every source-sheet drawing;
- whether every visually adjacent source drawing belongs to the same runtime animation clip.

## Decisive-key timing

| Key | Role | Timing | Provenance |
| --- | --- | --- | --- |
| A001-K0 LOAD | crouch/load | FOURS | INFERRED |
| A001-K1 LAUNCH | support break / impulse | ONES | INFERRED |
| A001-K2 RISE | upward root travel | TWOS | INFERRED |
| A001-K3 APEX_READ | apex/hang-time readability | FOURS | INFERRED |
| A001-K4 AERIAL_TASK_CHANGE | local airborne task change | TWOS | INFERRED |
| A001-K5 DESCENT_OPEN | downward root travel | TWOS | INFERRED |
| A001-K6 PRECONTACT | prepare impact; no early contact | TWOS | INFERRED |
| A001-K7 CONTACT | first ground reacquisition | ONES | INFERRED |
| A001-K8 LAND_COMPRESSION | force absorption | FOURS | INFERRED |
| A001-K9 REBOUND | supported recovery | TWOS | INFERRED |
| A001-K10 RETURN_STABLE | return-to-state | FOURS | INFERRED |

`1s/2s/4s` normalization: ONES/TWOS/FOURS, never seconds. OBSERVED timing keys: **none**.

## Artifact / Motion Dungeon

Repository path: `experiments/ascii-kinesis/v2-airborne-001-air-task-rides-root-arc/`
Artifact ship commit: `6f9df326c9376326274e3844429353a3003fd750`
SPA: `air-task-rides-root-arc.motion.html` with exactly `ASCII | JSON | VIDEO`.
ASCII: complete literal selectable/copyable `<pre>` contact sheet; ligatures disabled; whitespace preserved.
JSON: rig, keys, timing, evidence split, source/rights, compatibility, manifest/media identity.
VIDEO: embedded H.264 MP4 compiled solely from abstract ASCII rig coordinates and explicit holds; source sprite pixels used: **false**.
Embedded media SHA-256: `8101962c3feef935d48c43305accd32704fddf31c4cd3f618d7a383fc7a21554`
Embedded media bytes: `14,250`; `960x540`; `24 fps`; `108` frames; `4.5s` compiled loop envelope.
ASCII sheet SHA-256: `1ace5032a86f478d46beb3a087287f3e28227f58577a08d2730ea5b7b283a154`
Builder: `python3 build.py`.

The tracked standalone `.mp4` is LFS-managed in GitHub; the self-contained tracked SPA embeds the real 14,250-byte MP4 inline, which is the commissioned playback surface.

## Verification / boundaries

Exact GitHub readback at ship commit `6f9df326c9376326274e3844429353a3003fd750` confirmed the new directory and exactly these six files: builder, manifest, motion JSON, receipt, tracked `.motion.html`, and tracked `.mp4`. Manifest readback confirmed V2 format, exact primary tabs `ASCII | JSON | VIDEO`, literal ASCII text, embedded MP4 packaging, source-art exclusion, whole-sheet source identity/hash, 11 authored keys, and media SHA-256 `8101962c3feef935d48c43305accd32704fddf31c4cd3f618d7a383fc7a21554`. SPA readback confirmed the three tab controls, `<pre>` ASCII surface, disabled ligatures, preserved whitespace, and an inline `data:video/mp4;base64,...` source.

Phone-side reconstruction QA: builder completed; `ffprobe` reported H.264 `960x540`, `24/1`, `108` frames, `4.500000s`; full `ffmpeg` decode to null succeeded; extracted embedded MP4 SHA matched `motion.json` at `8101962c3feef935d48c43305accd32704fddf31c4cd3f618d7a383fc7a21554`.

Repo-wide `tools/test_ascii_kinesis_swarm_contract_v2.py` was callable and was run. It returned RC=1 on an unrelated pre-existing specimen: `v2-defense-001-guard-support-fork: expected exactly one tracked *.motion.html SPA`. This is the exact test boundary; it is not a failure of this new airborne entry. No source-evidence blocker remains for this specimen.

Issue receipt: `Valar05/home-center#343` is the durable campaign receipt surface for this verified run.

Correction hooks: `KEEP`, `REJECT`, `EXAGGERATE`, `COMPRESS`, `RETIME`, `CHANGE SOURCE`, `PROMOTE`, `SPAWN VARIANT`, `FIX BLOCKER`, `RERUN`.
