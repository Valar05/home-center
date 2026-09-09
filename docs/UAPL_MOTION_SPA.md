# UAPL Motion SPA v1

Status: UAPL / ASCII DELIVERY SPECIALIZATION

## Scope

The UAPL Motion SPA is the canonical **human-facing delivery envelope for a selected UAPL/ASCII animation lane**.

It is not the universal delivery surface for all animation work and it does not decide whether a commission should use ASCII, Vector Noodle, a rig, or another representation.

General animation authority lives in:

`skills/motion-direction/SKILL.md`

ASCII/UAPL specialization lives in:

`skills/ascii-kinesis/SKILL.md`

When UAPL is selected, this SPA packages its source, timing opinion, and playback into one self-contained inspectable HTML file.

## Representation relationship

For a UAPL-selected specimen:

```text
BOUNDED EVIDENCE
-> UAPL ASCII POSE SOURCE
-> DETERMINISTIC ASCII CONTACT SHEET
-> optional VECTOR NOODLE / RIG if useful
-> UAT DIRECTION/TIMING OPINION
-> GIF / VIDEO PLAYBACK
-> UAPL MOTION SPA DELIVERY ENVELOPE
```

The SPA is presentation/inspection. It does not promote itself above the selected pose source or Motion Direction source-role law.

A video timestamp may be pose provenance without becoming UAT timing authority.

## Generic offline/mobile shell

The SPA shell is lineage-neutral. It must not inherit visual identity, prop design, motifs, palette, or other imagery from a previous artifact merely because that artifact once used a useful browser layout.

Required interaction properties:

- one self-contained `<!doctype html>` file;
- `<meta charset="utf-8">`;
- `width=device-width,initial-scale=1,viewport-fit=cover,user-scalable=no`;
- `100dvh` shell with safe-area handling;
- no accidental page-level scrolling;
- horizontally scrollable control rows when needed;
- 44px-or-larger touch controls;
- `aria-pressed`, focus-visible, and `aria-live` where applicable;
- no external scripts, stylesheets, fonts, or network fetches;
- deterministic runtime markers for QA.

These are interface requirements only. They authorize **zero visual-art inheritance** from any shovel, character, previous SPA, or quarantined artifact.

## Required views for v1 UAPL Motion SPA

A canonical v1 `.motion.html` contains four inspection views.

### Poses

Shows every load-bearing UAPL pose as literal ASCII in responsive pose cards.

On narrow screens, cards may reflow vertically. Characters inside one pose may never wrap, reorder, substitute, or rasterize.

The canonical horizontal contact-sheet text remains embedded for deterministic readback.

### Timing

Shows UAT as human-readable data and preserves canonical text.

Timing is an opinion pinned to the UAPL SHA-256. Its provenance must distinguish observed timing from derived direction according to Motion Direction.

### GIF

Contains an actual GIF compiled from the same selected pose source + timing/direction state used for this UAPL specimen.

The GIF is embedded as `data:image/gif;base64,...` so the file remains offline/self-contained.

PNG, screenshot, poster, or an image merely containing ASCII does not satisfy this slot.

### Source

Shows canonical UAPL and canonical UAT as literal selectable text plus source-role/timing-provenance facts sufficient to prevent `VIDEO_TIMING_LEAK`.

## ASCII legibility

Use:

```css
font-family: ui-monospace, SFMono-Regular, Menlo, Consolas,
             "Liberation Mono", "Courier New", monospace;
font-variant-ligatures: none;
white-space: pre;
word-break: normal;
overflow: auto;
```

Presentation may reflow around pose cards. Characters inside a pose may not reflow.

## Machine identity

The root carries:

- `data-uapl-motion-spa="1"`;
- `data-uapl-sha256`;
- `data-gif-sha256`.

The page exposes:

```js
window.__UAPL_MOTION_SPA__
window.__UAPL_MOTION_SPA_READY__ === true
```

These are QA/readback surfaces, not aesthetic acceptance or motion authority.

## Canonical implementation

`functions/uapl_motion_spa.js`

Primary entry point:

```js
buildMotionSpa({
  uaplText,
  uatText,
  gifDataUri,
  title,
})
```

The builder:

1. parses/canonicalizes UAPL;
2. verifies UAT source hash;
3. renders deterministic literal-ASCII poses/contact sheet;
4. verifies genuine GIF87a/GIF89a bytes;
5. hashes GIF bytes;
6. emits byte-deterministic offline HTML for identical inputs.

The builder cannot prove that the selected representation, timing direction, body completeness, prop shape, visual canon, or artistic result is good. Those remain Motion Direction + human visual-review responsibilities.

## Completion for this specialization

A complete UAPL Motion SPA package contains:

1. literal UAPL pose source;
2. deterministic literal-ASCII contact sheet;
3. UAT timing/direction opinion with provenance;
4. actual explanatory GIF;
5. one self-contained UAPL Motion SPA containing them.

This completion contract applies only when the commission selected the UAPL/ASCII lane. A vector-first animation is not incomplete merely because it does not emit this SPA.

## Quarantine guard

Do not use old SPA art, prop silhouettes, backgrounds, palettes, or decorative elements as a design source unless the current commission explicitly names that clean lineage as canonical.

Rejected/quarantined SPA imagery may remain historical evidence only.

## Boundary

This file does not own representation selection, general animation timing, game-style direction, scheduling, worker cadence, queue ownership, or artistic acceptance.
