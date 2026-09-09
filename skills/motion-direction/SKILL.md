# Motion Direction Skill

Status: CANONICAL CORE

## Purpose

This is the general animation-direction skill for embodied performance reference, first-person motion, sprite/contact-sheet study, Vector Noodle, Pose Lab, ASCII Kinesis, rigs, Motion Dungeon, and game-style retargeting.

It owns **judgment about what the evidence means and how animation should be authored**. Renderer-specific skills inherit this file; they do not redefine the source role, timing authority, visual canon, body completeness, or quarantine rules below.

This skill supersedes any older universal rule that says every animation must begin in ASCII/UAPL, that photographic/video key spacing is automatically timing authority, or that a previous artifact may silently donate visual language to a new commission.

The user's explicit commission remains the mission boundary.

## 1. Source-role arbitration — classify before compiling

Every input has one or more roles. Infer the role from the commission and evidence; do not ask Drew to answer routine animation-director questions that the worker can resolve by inspection.

- `POSE_REFERENCE` — supplies decisive body/hand/prop poses, contacts, load path, pose order, and physical intent. Timing is not authoritative.
- `TIMING_REFERENCE` — supplies cadence, spacing, exposure, holds, acceleration, or recovery timing as evidence the commission actually intends to preserve or study.
- `STYLE_REFERENCE` — supplies high-level animation direction: timing character, spacing, exaggeration, smears, camera behavior, impact grammar, pose appeal, or presentation language. It does not silently become body identity or asset canon.
- `CANONICAL_VISUAL` — accepted source for silhouette, proportions, palette/material language, line treatment, component identity, or other appearance facts. It does not silently become motion authority.
- `CONTACT_REFERENCE` — supplies grip, support, collision, tool custody, foot plant, or another physical relationship.
- `FULL_PERFORMANCE_REFERENCE` — supplies pose and timing only when the commission actually asks to reproduce or preserve the performance as performed.
- `NEGATIVE_FIXTURE` / `QUARANTINED` — supplies failure evidence only. It is never positive visual or motion source.

One file may hold several roles, but each role is explicit. A timestamp can remain useful as an address for recovering a pose without becoming timing authority.

### Default for Drew-performed video

When Drew records himself performing an action and asks for an animation, default to `POSE_REFERENCE` + `CONTACT_REFERENCE` unless the commission clearly assigns timing authority too.

That means:

- preserve the decisive poses, contact relationships, load, pose order, and physical intention;
- use source timestamps to locate those poses;
- do **not** inherit recording cadence, hesitation, phone-camera drift, repeated attempts, dead air, or literal source spacing by default;
- the animation worker authors timing.

The compact law is:

`DREW GIVES POSES -> WORKER DIRECTS ANIMATION`

## 2. Pose master and direction profile are separate artifacts

A pose master records what states exist and what they mean. It does not own how long those states last.

A direction profile owns:

- key economy;
- timing and spacing;
- holds and hit-stop;
- acceleration/deceleration;
- anticipation;
- overshoot;
- recoil;
- follow-through;
- recovery debt;
- settle;
- secondary lag/inertia;
- smear/substitution behavior;
- camera/FOV/bob/shake when relevant;
- style-specific pose exaggeration.

Do not copy a video timeline merely because a video exists. Do not ask Drew for frame counts, easing curves, anticipation duration, overshoot, or ordinary timing choices unless the commission makes one of those facts user-owned.

Strong decisive poses plus well-directed connective motion are preferred over redundant drawings. Add a bridge key only when it carries unique semantic or force information; otherwise tween.

## 3. Representation is adaptive — ASCII is a tool, not a religion

Choose the cheapest representation that can carry the load-bearing information **for this commission**.

### ASCII / UAPL

Use when semantic pose topology, timing grammar, contact-sheet comparison, or terminal-native durability survives abstraction cleanly. When UAPL is explicitly selected as source, its deterministic contracts apply.

Do not force ASCII/UAPL as the first authored artifact for every animation.

### Vector Noodle

Prefer vector-first when the commission depends on:

- a complete first-person arm or other continuous silhouette;
- occlusion;
- hand/wrist/forearm relationship;
- load-bearing anatomy;
- canonical line/material language;
- 2.5D depth illusion;
- continuous transforms;
- tween-heavy motion;
- cheap state replacement for small complex forms;
- shader-driven presentation.

A vector-first pose master is valid. UAPL may later be emitted as an abstract teaching/debug projection if useful; it does not retroactively become the original authority.

### Rig / 3D

Escalate only when hierarchical depth, deformation, IK/FK, bone roll, camera-relative rotation, constraint solving, or another genuinely 3D property is necessary.

Every escalation must purchase capability. Every de-escalation must preserve the information the higher tier proved useful.

## 4. Vector Noodle motion law

For vector-first animation:

- decisive poses are authored states;
- limb/body geometry moves continuously through transforms and deformation;
- tweens should do most connective labor;
- small high-complexity forms such as finger curls may use replaceable vector states;
- replaceable states may not erase the load-bearing chain;
- shader state, light fields, material response, parallax, masks, and pseudo-depth may animate independently when they improve the read;
- raster/video is a delivery/output skin, not the editable source.

A hand may be `open -> grip -> clench` state replacement. An entire arm may not disappear into a floating mitten because replacement was cheaper.

## 5. Load-bearing body completeness

The animation must show enough of the kinematic chain to explain the force.

For a first-person single-arm action, the ordinary minimum is:

`screen-edge/root implication -> upper arm -> elbow -> forearm -> wrist -> hand -> contact`

The shoulder itself may be off-screen, but the entering upper arm must make the chain believable. Preserve foreshortening and occlusion rather than deleting anatomy that becomes inconvenient.

Fail the candidate if:

- the hand floats without a credible arm;
- the wrist has no structural relationship to the forearm;
- load appears at the hand with no body consequence;
- the prop moves while the body does not earn it;
- perspective destroys the pose's load path.

Compression may remove redundant frames. It may not remove the structure that carries force.

## 6. Props are not sticky nouns

A prop from the previous discussion does not automatically survive into the current animation.

Include a prop only when the current commission, current pose evidence, or current physical action makes it load-bearing or explicitly requested.

`RECENT CONTEXT != PROP AUTHORITY`

If the current test is an arm motion and the action reads without a shovel, there is no shovel merely because the previous topic was a shovel.

### Prop identity gate

Before a prop enters a rendered animation:

1. recover the current clean/accepted prop lineage if one exists;
2. inspect silhouette, proportions, component relationships, grip point, and orientation;
3. compare the rendered prop against that source;
4. reject generic category approximations such as a merely “shovel-like” shape when object identity matters.

If the required canonical prop source cannot be recovered through the authorized lane, do not invent a substitute and call it canonical.

Once attached, prop custody is continuous. The tool may lag, flex, overshoot, or rotate around a contact socket; it may not teleport through or escape the hand unless release is an authored event.

## 7. Visual canon and quarantine — zero leakage

Canonical visual style must come from accepted/current visual lineage or the present commission. Recover it before authoring pixels.

A rejected or quarantined artifact may be inspected only as a negative fixture: what failed, what must not recur, and which successor superseded it.

Quarantine forbids positive reuse of:

- silhouette;
- proportions;
- palette;
- line treatment;
- ornament;
- component shapes;
- prop design;
- UI/art shell identity;
- derived placeholder imagery.

Quarantine is transitive. A new drawing copied from a quarantined predecessor is still contaminated even if the file is new.

A neutral **direction** pass is not permission to invent a neutral visual style. If the commission requires canonical Vector Noodle art, the direction study uses that clean lineage or deliberately remains a non-visual structural study; it does not manufacture cartoon placeholder art and promote it as representative.

Machine validity, hashes, legal SVG, and a running page never promote rejected pixels.

## 8. Game/style retargeting

When Drew provides a game and asks to make the animation feel/look like that game, treat the game as a `STYLE_REFERENCE` unless the commission clearly assigns additional roles.

The worker may and usually should change:

- timing;
- spacing;
- anticipation;
- contact emphasis;
- recovery cadence;
- pose exaggeration;
- smear/substitution strategy;
- camera response;
- weapon/hand lag;
- secondary motion;
- presentation rhythm.

Do not preserve the user's source-video timing out of deference. The pose master is evidence; the game-direction pass is animation authorship.

Preserve the action's identity, contact meaning, and load logic. Literal source angles may be pushed when the target game's readability demands it.

Use high-level animation traits rather than copying protected game assets or character-specific art.

## 9. Motion Dungeon compile contract

Motion Dungeon receives separable state:

```text
POSE MASTER
+ DIRECTION PROFILE
+ VISUAL PROFILE / CANONICAL ASSET REFERENCES
+ CONTACT MAP
+ SOURCE-ROLE / PROVENANCE LEDGER
+ QUARANTINE LEDGER
-> EDITABLE RUNTIME STATE
-> RENDER / VIDEO OUTPUT
```

Editable scene/motion state remains the artifact. MP4/GIF is output.

Three.js, SVG/vector geometry, GLSL/vector shaders, procedural effects, state replacement, and tweens are peer implementation tools. Choose what preserves the commission with least unnecessary machinery.

No field silently inherits from an unrelated previous artifact.

## 10. Visual review gate — inspect the thing, not the receipt

Before calling a candidate healthy, inspect actual pixels at both decisive poses and motion playback.

Minimum review:

1. **Pose read** — silhouettes, load, pose order, complete body chain.
2. **Contact read** — grip/support/tool custody/occlusion.
3. **Motion read** — spacing, anticipation, commitment, force transfer, recoil, recovery, settle.
4. **Visual lineage read** — canonical style present; quarantined style absent.
5. **Object identity read** — every included prop has correct silhouette/proportions or is explicitly non-canonical.
6. **Commission read** — no stale prop, renderer, UI shell, or prior-task noun has survived without authority.

A structural test can prove that a page runs. It cannot prove that an arm exists, a shovel has the right shape, a style is canonical, or the motion makes sense.

## 11. Correction ownership

When something looks wrong, mutate the smallest layer that actually owns the failure:

- wrong decisive body state -> pose master;
- bad cadence/spacing -> direction profile;
- floating grip -> contact map / pose geometry;
- bad object shape -> canonical prop geometry/asset selection;
- wrong art language -> visual profile/source lineage;
- shader obscures accepted shapes -> shader/presentation layer;
- renderer-only artifact -> renderer.

Do not repaint over a pose error or retime around an identity error.

## 12. Regression canaries

A general animation skill update fails if any of these scenarios produces the bad answer:

1. **Embodied video -> animation**: worker imports recording timing instead of using video primarily as pose/contact evidence. `VIDEO_TIMING_LEAK`.
2. **Game retarget**: worker merely repaints while leaving direction/timing untouched when the game grammar calls for change. `GAME_STYLE_REPAINT_ONLY`.
3. **Load-bearing first-person arm**: worker outputs a floating hand or deletes the forearm/upper-arm chain. `LOAD_CHAIN_ERASED`.
4. **Previous shovel discussion -> arm-only test**: worker carries a shovel into the new commission without current authority. `STALE_PROP_CARRYOVER`.
5. **Quarantined shovel available**: worker reuses its shape, motifs, palette, or derived placeholder. `QUARANTINED_VISUAL_LEAK`.
6. **Prop required**: worker draws a generic category object without inspecting the accepted silhouette. `PROP_IDENTITY_DRIFT`.
7. **Canonical vector commission**: worker substitutes crude placeholder art because it is easier to animate. `PLACEHOLDER_STYLE_SUBSTITUTION`.
8. **ASCII unsuitable**: worker forces UAPL/ASCII despite loss of full-arm silhouette/occlusion information. `ASCII_FORCED_WITHOUT_BENEFIT`.

Also preserve these general failure labels:

- `SOURCE_ROLE_CONFUSION`
- `CANONICAL_STYLE_NOT_RECOVERED`
- `FLOATING_CONTACT`
- `TWEEN_SOUP`
- `RENDER_GREEN_VISUAL_RED`

## 13. Relationship to specialized skills

- `skills/ascii-kinesis/SKILL.md` is an ASCII/UAPL renderer-and-delivery specialization. Its ASCII-first rules apply **only after the commission selects that lane**.
- `docs/UAPL_ASCII_POSE_LANGUAGE.md` defines UAPL when UAPL is selected. It is not a universal animation intake law.
- `docs/UAPL_MOTION_SPA.md` defines the UAPL/ASCII delivery envelope only.
- Droobiedoo's Animation Apprentice stores corrections and lessons but inherits animation judgment from this skill.
- Motion Dungeon compiles the chosen representations; it does not decide that a source video owns timing merely because timestamps exist.

If another animation document conflicts with this file on source role, timing authority, representation selection, visual canon, quarantine, body completeness, or stale-prop inheritance, **this file wins**.

## 14. Correction propagation and completion

General motion corrections are consolidated here first. Specialized skills should point here and contain only their unique renderer/runtime/delivery laws. Do not grow a second general animation doctrine beside this one.

Completion requires the requested runnable/durable artifact through the authorized lane plus readback from that lane. Local scratch is construction only, never completion proof.

Human acceptance remains distinct from machine health. A candidate rejected on visible grounds stays rejected until the visible failure is actually corrected.
