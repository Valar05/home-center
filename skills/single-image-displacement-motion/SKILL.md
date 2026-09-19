# Single-Image Displacement Motion

Status: DURABLE ANIMATION TECHNIQUE

## Purpose

Use this skill when one strong source image should remain the appearance authority while motion is created by deforming that same image rather than redrawing the subject frame by frame.

This is the "beautiful single image -> morph/displace animation" technique recovered from Drew's prior animation work. It is especially useful for subtle idles, breathing, loaded stances, recoil, cloth response, membrane flex, sways, and other motions where preserving appearance matters more than generating new drawings.

The central law is:

`ONE IMAGE OWNS APPEARANCE; DISPLACEMENT OWNS MOTION.`

## Core idea

Start with one accepted hero image or one accepted keyframe. Treat its pixels as the visual authority. Motion is created by moving regions of those pixels through space with masks, local warps, meshes, displacement fields, articulated transforms, or layered deformation.

Do not solve subtle motion by asking an image model to redraw the character repeatedly. That creates costume drift, face drift, silhouette crawl, prop drift, and texture boil.

The result should look like the same illustration moving.

## Suitable use cases

Prefer this method when:
- the visual style is dense, painterly, graphic, fleshpunk, watercolor, or otherwise expensive to redraw consistently;
- the motion is subtle enough that the same underlying image can plausibly carry it;
- the user wants a stylized interpolation rather than literal skeletal realism;
- a hero image is already strong and should remain visually canonical;
- the desired motion is deformation-heavy: breath, crouch compression, recoil, recovery, cloth lag, membrane tension, root sway, head/torso parallax;
- a small number of true authored extrema exist and the connective motion can be procedural.

## Single-image mode

When only one authored image is available:
1. lock it as appearance authority;
2. identify world anchors, usually planted feet or another support/contact point;
3. segment the image into deformation regions;
4. define the motion as changes in those regions, not as a repaint;
5. deform the original pixels through time;
6. preserve identity-critical regions by using bounded deformation;
7. inspect playback for actual movement, not texture flicker.

Typical regions:
- planted foot / support foot;
- free foot / lower leg;
- pelvis;
- torso / ribcage;
- head / face;
- upper arms / forearms / hands;
- weapon or prop;
- secondary cloth;
- hoses, straps, canisters, membranes, hair, tails, or other delayed structures.

## Two-authored-key extension

When two genuine authored images exist, such as a standing key and a crouched key:
- Key A and Key B are sacred exact endpoints;
- the two images may differ substantially in pose;
- procedural deformation carries the transition between them;
- the bridge must visibly change pose;
- the bridge is not an authored key and must not be presented as one.

Pattern:

`AUTHORED A -> DISPLACEMENT / DEFORMATION -> AUTHORED B`

Optional recovery:

`AUTHORED B -> DEFORMATION -> AUTHORED A`

This is useful when the user can simply pose for or author the meaningful extremes.

## Displacement is not crossfade

A crossfade changes opacity between two pictures. That is not this technique.

FAIL if:
- both bodies are visible at once;
- edges appear as a ghost halo;
- limbs dissolve instead of travelling;
- the subject flickers while staying in the same pose;
- only texture changes while anatomy remains static;
- the feet drift despite being planted;
- the result looks like one image fading into another.

PASS requires:
- one coherent body at every intermediate time;
- visible pose change;
- singular anatomy and props;
- world anchors that remain stable when required;
- spatial movement of regions rather than alpha mixing.

## Deformation methods

Use the cheapest method that preserves the intended movement.

### Region transforms
Translate, rotate, scale, and shear bounded body regions around explicit pivots. Good for graphic stylization and small pose changes.

### Mesh warp
Attach a 2D control mesh to the image and move mesh vertices. Good for larger torso, limb, or cloth deformation while preserving local texture.

### Landmark-guided warp
Use corresponding anatomical landmarks across two authored extrema and deform one state toward the other. Good when two strong keys differ substantially.

### Displacement field
Drive local pixel offsets with a field, map, or procedural function. Good for breathing, membrane flex, cloth pulse, organic motion, and controlled distortion.

### Layered hybrid
Use articulated region transforms for the body and separate displacement fields for cloth, membranes, hoses, and other secondary structures. This is usually the strongest production form.

## Anchors and custody

World anchors are explicit.

For a grounded character:
- planted feet are world anchors unless an authored key moves them;
- pelvis and torso move relative to those anchors;
- free limbs may travel;
- props follow their custody relationship;
- cloth and secondary structures may lag but may not detach.

For a held prop:
- attach it to the owning hand/holster/socket;
- do not independently drift it because the body deforms.

## Loaded-standing-still motion

For Drew's Ryu-like loaded stance:
- keep the feet stable;
- let the pelvis drop and shift;
- compress the knees and hips;
- allow the torso to counterbalance;
- let head movement remain quieter than pelvis/torso motion;
- apply delayed secondary motion after the body;
- do not turn the result into a generic vertical breathing bob.

"Crouch body" means the body must actually compress between support anchors. It is not enough to scale the whole image or slide the feet.

## Contact sheets

Contact sheets remain the authored source unit.

When source video exists:
1. extract the actual decisive frames;
2. keep full-body evidence, especially feet/hands/props;
3. assemble one contact sheet;
4. use that full sheet directly as the reference for any character retargeting;
5. generate target keys as one contact sheet, never independent images;
6. only after the authored keys are approved should displacement/deformation create connective motion.

Do not allow procedural cleverness to replace the user's real keyframes.

## Playback gate

Still images can hide failure. Playback is mandatory.

Reject if:
- motion is visually static;
- only edges shimmer;
- feet float;
- secondary detail moves more than the body;
- the character appears to melt;
- the destination pose is never actually reached;
- the motion reads as crossfade, smear, or camera motion instead of body motion.

The visible animation must prove that the body changes state.

## Pose Lab use

Pose Lab should expose:
- authored endpoints separately from procedural frames;
- source contact sheet;
- world-anchor controls;
- displacement/warp controls;
- playback;
- frame/contact-sheet/GIF/JSON export;
- labels that distinguish `authored` from `procedural`.

Exports must preserve the exact authored endpoint pixels.

## Correction ownership

When the result is wrong:
- wrong endpoint pose -> fix authored key;
- static body -> increase real articulated deformation;
- foot drift -> fix world anchors;
- ghosting -> remove alpha blend / crossfade;
- melting anatomy -> improve region boundaries or mesh topology;
- jittering detail -> reduce redraw and preserve source pixels;
- bad rhythm -> retime after the spatial motion is correct;
- weak secondary motion -> add delayed deformation only after the primary body motion reads.

Do not solve a spatial failure with timing alone.

## Compact doctrine

`CONTACT SHEET GIVES TRUE KEYS.`

`SINGLE IMAGE GIVES APPEARANCE.`

`DISPLACEMENT GIVES CONNECTIVE MOTION.`

`PLAYBACK DECIDES WHETHER IT WORKED.`
