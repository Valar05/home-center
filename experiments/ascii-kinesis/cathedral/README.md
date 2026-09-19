# ASCII Kinesis Cathedral

A browser-native monument to the ASCII Kinesis anthology and the Belly of Defiance motion grammar.

The Cathedral does not replace the specimen archive. It sits above it and makes the archive legible as one system:

EVIDENCE -> SEMANTIC CONTACT FRAME -> EXPRESSIVE BODY -> CONSEQUENCE -> RECOVERY

## What it is

- A full-screen Canvas motion viewer for ASCII Kinesis motion.v2 specimens.
- A semantic adapter that reads multiple specimen dialects: joint maps, point maps, raw ASCII poses, and relationship-first records.
- A Belly of Defiance phase lens: LOAD -> COMMIT -> HIT -> CONSEQUENCE -> RECOVERY.
- A truth overlay that can show the authoritative ASCII/contact pose over the rendered body.
- A corpus nave with lane filtering and text search.
- A motion lint surface for missing timing, unreadable contact, recovery reset, and other semantic problems.
- A local motion.json loader for specimens outside the curated index.
- Keyboard, touch, reduced-motion, and screen-reader affordances.

## Doctrine

Beauty may decorate Kinesis.
Beauty may exaggerate Kinesis.
Beauty may not contradict Kinesis.

ASCII is not the final art. It is the load-bearing contact truth.

The finished body may change material, line, anatomy, costume, deformation, camera, and secondary motion. It must preserve the semantic sentence of the decisive frame: support, contact, root, facing, load, custody, and consequence.

## Important corpus boundary

The anthology contains historical evidence, rejected fixtures, repair successors, and later specimens. The Cathedral treats unclassified corpus entries as EVIDENCE, not automatic positive taste authority. Existing rejection-debt and taste-reset rules remain intact.

## Run

Serve the repository over HTTP and open:

experiments/ascii-kinesis/cathedral/index.html

No build step and no external runtime dependency are required.

The page includes a fallback demonstration, but live corpus loading uses relative motion.json files and therefore needs an HTTP origin rather than a file:// URL.

## Controls

- Space: play / pause
- Left / Right: previous / next decisive key
- Home / End: first / last key
- T: truth overlay
- A: ASCII pane
- F: force / support annotations
- R: restart current specimen

## Architecture

index.html
cathedral.css
cathedral-core.js
specimens.js
cathedral.js

The Canvas renderer is intentionally downstream from the semantic adapter. Renderer changes cannot silently redefine contact truth.

## Cathedral acceptance

A useful Cathedral must prove all of these at once:

1. A real persisted ASCII Kinesis motion.json loads from the repository.
2. The current decisive key remains readable as literal text or reconstructed semantic ASCII.
3. Belly phase classification is visible and traceable to the key's causal role.
4. A beautiful body can be rendered without hiding support/contact truth.
5. Truth overlay can expose divergence rather than merely decorating the render.
6. Historical specimens remain evidence rather than being silently promoted to current taste canon.
