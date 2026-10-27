# Single-Image Displacement Animation

Use this skill when one beautiful authored image should move without being redrawn into a sequence.

## Core law

**ONE IMAGE. ONE DUTY. ONE LAW OF CHANGE.**

Do not begin by cutting the character into parts or generating multiple near-identical images. Preserve one appearance-authority image and animate it through deterministic deformation.

This method exists specifically to avoid:
- identity drift;
- costume/detail crawl;
- redraw jitter;
- independent-frame inconsistency;
- unnecessary keyframe burden.

## Architecture

```text
SEMANTIC STATE
      ↓
one appearance-authority image
      ↓
lawful displacement / local deformation
      ↓
visible samples
      ↓
timing / exposure compiler
      ↓
playback / export
```

Keep these concepts separate:
- **semantic state**: what the motion means;
- **visible frame**: one sampled deformation state;
- **exposure**: how long that visible state is held.

A visible frame is not automatically a new semantic key.

## Historical Belly doctrine

Recovered Belly work used whole-sprite local-UV displacement rather than skeleton animation as the first move. A historical implementation used sinusoidal/cosinusoidal deformation over time across the whole sprite cell.

The reusable principle is not the old engine or shader language. The reusable principle is:

- deform the same authored pixels;
- preserve the image's visual identity;
- let a small number of parameters create breathing, pressure, sway, recoil, settling, or material response;
- do not decompose unless independent control clearly pays for the extra complexity.

In the current browser-first world, implement the same law with Canvas 2D meshes, WebGL/Three.js geometry, displacement maps, UV warps, or equivalent deterministic deformation.

## Good uses

Use single-image displacement for:
- idle pressure / breathing;
- cloth or membrane response;
- subtle loaded stance;
- recoil residue;
- secondary settling;
- environmental sway;
- expressive material motion where the pose itself does not change enough to justify another authored key.

## Not for articulated pose replacement

Single-image displacement is not a substitute for a genuinely different pose.

If the hand, arm, head, pelvis, or weapon must occupy a materially different place, use a second authored key or a contact-sheet key. Then use connective deformation between those keys.

Do not ask displacement to invent a new pose it does not have enough image evidence to represent.

## Contact-sheet relationship

When multiple real semantic poses are needed:
1. extract or author the real keys;
2. assemble them into one source contact sheet;
3. retarget/generate the target character as one whole contact sheet;
4. keep those authored keys exact;
5. use single-image displacement locally inside a key or true displacement morphing between adjacent authored keys.

Never generate six independent images for a six-frame contact sheet.

## Two-key relationship

For two authored endpoints:

```text
AUTHORED A
   ↓
connective singular-anatomy displacement
   ↓
AUTHORED B
```

The bridge may inherit this skill's deformation ideas, but must obey endpoint correspondences and anatomy singularity.

No:
- alpha crossfades;
- pixel voting;
- double hands;
- ghost silhouettes;
- duplicated faces;
- duplicated weapons.

## Acceptance

A successful single-image displacement animation:
- still looks like the exact authored image;
- visibly moves;
- has no texture boil;
- has no identity drift;
- keeps world anchors stable when required;
- exposes motion through deformation rather than redraw;
- remains reversible and deterministic;
- looks good in playback, not just as stills.

## Failure signs

Reject immediately if:
- the image only flickers;
- the silhouette barely changes when pose change was required;
- feet drift without authored motion;
- details crawl;
- body parts duplicate;
- the method is actually a crossfade;
- the technique becomes more complicated than adding the missing authored key.

## Production heuristic

Start with the cheapest lawful motion:

1. one beautiful image;
2. one displacement law;
3. one timing law;
4. inspect playback;
5. add another authored key only when the first image cannot physically represent the needed pose.

The point is to get maximum expressive motion from minimum authored imagery without lying about what is authored versus procedural.
