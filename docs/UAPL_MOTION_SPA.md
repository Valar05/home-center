# UAPL Motion SPA v1

## Canonical role

The UAPL Motion SPA is the canonical **user-facing delivery envelope** for an animation-understanding worker.

It does not replace UAPL, UAT, or the GIF. It packages them into one self-contained HTML file that preserves literal ASCII and displays correctly across modern desktop and mobile browsers without relying on ChatGPT code-block layout.

The representation stack remains:

```text
EVIDENCE
-> UAPL ASCII SOURCE
-> DETERMINISTIC ASCII CONTACT SHEET
-> VECTOR NOODLE, only if useful
-> RIG / METARIG, only if useful
-> UAT TIMING PROFILE
-> GIF / VIDEO / RUNTIME PLAYBACK
-> UAPL MOTION SPA DELIVERY ENVELOPE
```

The SPA is a delivery compilation. Motion truth still lives upstream in UAPL.

## Shovel-derived shell

The mobile/display treatment is intentionally inherited from the accepted shovel SPA pattern:

- one self-contained `<!doctype html>` file;
- `<meta charset="utf-8">`;
- `width=device-width,initial-scale=1,viewport-fit=cover,user-scalable=no`;
- `100dvh` shell;
- safe-area insets;
- no page-level accidental scrolling;
- horizontally scrollable control rows;
- 44px-or-larger touch controls;
- `aria-pressed`, focus-visible, and `aria-live` state;
- no external scripts, stylesheets, fonts, or network fetches;
- deterministic non-visible runtime markers for QA.

The animation version changes the workspace semantics: ASCII must remain selectable literal text, never a raster approximation.

## Required views

A canonical `.motion.html` file contains four views.

### Poses

Default view. Shows every load-bearing pose as literal ASCII characters in responsive pose cards.

On narrow screens, cards may reflow vertically. Characters inside a pose may never wrap, reorder, substitute, or rasterize.

The exact canonical horizontal contact-sheet text is also embedded for deterministic readback.

### Timing

Shows the UAT timing profile as a human-readable table and preserves its exact canonical text.

Timing remains an opinion pinned to the UAPL source SHA-256.

### GIF

Contains an **actual GIF** compiled from the same motion source and timing opinion.

The GIF is embedded as a `data:image/gif;base64,...` URI so the HTML remains a single offline file.

A PNG, screenshot, video poster, or image containing ASCII does not satisfy this slot.

### Source

Shows canonical UAPL and canonical UAT as literal selectable text.

## ASCII legibility contract

The SPA renderer must use:

```css
font-family: ui-monospace, SFMono-Regular, Menlo, Consolas,
             "Liberation Mono", "Courier New", monospace;
font-variant-ligatures: none;
white-space: pre;
word-break: normal;
overflow: auto;
```

The default responsive view uses per-pose cards instead of forcing the entire horizontal contact sheet to shrink to phone width. The user may inspect the canonical horizontal strip separately.

Presentation reflow is allowed. Character reflow is not.

## Machine identity

The root element carries:

- `data-uapl-motion-spa="1"`;
- `data-uapl-sha256`;
- `data-gif-sha256`.

The page also exposes:

```js
window.__UAPL_MOTION_SPA__
window.__UAPL_MOTION_SPA_READY__ === true
```

This is a QA/readback surface, not motion authority.

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

1. parses and canonicalizes UAPL;
2. verifies UAT against the exact UAPL SHA-256;
3. renders deterministic literal-ASCII poses and contact sheet;
4. verifies that the embedded binary is genuinely GIF87a/GIF89a;
5. hashes the GIF bytes;
6. emits one byte-deterministic offline HTML file.

Same UAPL + same UAT + same GIF + same title must produce byte-identical HTML.

## Worker completion rule

A motion worker is not complete after emitting raw ASCII alone.

The complete teaching package is:

```text
1. UAPL pose source
2. deterministic ASCII contact sheet
3. UAT timing sheet
4. actual explanatory GIF
5. one self-contained UAPL Motion SPA containing all of the above
```

The SPA is the object a human opens. The UAPL is the object code reads.

## Boundary

This contract does not define worker scheduling, cadence, queue ownership, leasing, retries, or swarm dispatch. Those remain outside this artifact layer.
