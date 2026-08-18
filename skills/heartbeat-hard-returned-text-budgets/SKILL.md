# Heartbeat Hard Returned Text Budgets

Use this skill when a heartbeat surface claims a maximum number of Unicode code points for routine speech or visible text.

## Canonical wounds

A maximum returned budget includes every character the projection adds. If a helper takes `N` source code points and then appends `…`, it returns `N + 1` code points and has violated its own contract.

A second wound exists even after that arithmetic is repaired: a code-point-safe cut can still split one user-perceived character. Combining sequences, emoji modifiers, ZWJ emoji, and regional-indicator flags are extended grapheme clusters, not bags of independently disposable code points.

These are not cosmetic defects. Routine TalkBack, collapsed summaries, interrupted-refresh status speech, and native Button labels are bounded operator surfaces. Their resource limit must describe the returned projection, and the retained prefix must not amputate a grapheme cluster.

## One plain projection law

Use `HeartbeatPlainTextBudget.boundedWithEllipsis(...)` for routine/plain heartbeat projections that need a simple ellipsis.

The invariant is:

- returned code points are always `<= maxCodePoints`;
- if truncation is needed and the budget is positive, the ellipsis consumes part of that same budget;
- a one-code-point positive budget returns one ellipsis;
- the retained prefix ends only at a Unicode extended-grapheme-cluster boundary;
- if the next whole grapheme plus the ellipsis cannot fit, that grapheme is omitted rather than split;
- the canonical Candidate/Node/Frame source or evidence field is never rewritten;
- exact or under-budget text passes through unchanged.

The current pure source uses the platform regex extended-grapheme matcher `\X` to walk whole clusters while continuing to account the public resource contract in Unicode code points. Do not replace it with Java 17 `BreakIterator` and assume equivalent behavior: this skill requires the actual extended-grapheme contract, not merely a code-point or legacy character boundary.

Do not copy the old `prefix(max) + ellipsis` pattern into another helper, including scene-level interruption/status projection helpers.

## Plain speech is not explicit evidence

Do **not** route routine/compact speech through `HeartbeatInvisibleSemanticControlPolicy` merely because its explicit evidence projection already knows how to reserve suffix space.

Those are different surfaces:

- compact focus speech: plain text, hard returned budget, grapheme-safe retained prefix;
- collapsed label speech: plain text, hard returned budget, grapheme-safe retained prefix;
- interrupted-refresh visible pulse id / safe boundary speech: plain text, hard returned budget while exact Frame evidence remains untouched;
- native visible Button label: plain text, hard returned budget, grapheme-safe retained prefix;
- selected explicit evidence detail: collision-safe invisible-control markers, separately hard-bounded after expansion.

Cross-pollinate the resource invariant, not the presentation semantics.

## Current source consumers

After the 2000 grapheme-boundary repair:

- `HeartbeatSkillPolicy` compact label/consequence speech: YES / SOURCE WIRING;
- `HeartbeatFrameAccessibility` collapsed per-light label: YES / SOURCE WIRING;
- `HeartbeatOverlayViewModel` visible per-light label: YES / SOURCE WIRING;
- `HeartbeatSceneGraph.Frame.interruptedRefreshDescription()` safe pulse-id/boundary projections: YES / SOURCE WIRING;
- one shared plain-text hard-budget helper: YES / SOURCE;
- whole-grapheme retained prefix inside the same code-point budget: YES / SOURCE;
- exact `Frame.visiblePulseId` / `Frame.refreshBoundary` mutation: NO BY DESIGN;
- canonical Candidate/Node source-field mutation: NO BY DESIGN;
- explicit evidence marker projection changed: NO / ORDERED DARK;
- Android/JVM test execution of the new grapheme fixtures: NO unless separately evidenced;
- runtime TalkBack / native UI observation: NO;
- deployed / callable / executed / delivered / accepted: NO.

## Regression doctrine

Pin these independently:

1. Returned projection never exceeds the requested code-point budget, including ellipsis.
2. Supplementary Unicode such as swans is not split.
3. Combining-mark sequences remain whole.
4. Emoji modifier sequences remain whole.
5. ZWJ emoji sequences remain whole.
6. Regional-indicator flags remain whole.
7. A one-code-point positive budget returns one bounded ellipsis; zero returns empty.
8. If a whole next grapheme cannot coexist with the ellipsis inside the budget, return the preceding whole graphemes plus ellipsis rather than a partial grapheme.
9. Exact and under-budget values pass through byte-for-byte/UTF-16-code-unit-for-code-unit unchanged.
10. Compact focused consequence speech reserves one code point for the ellipsis.
11. Collapsed labels reserve one code point for the ellipsis.
12. Native visible labels reserve one code point for the ellipsis before state framing.
13. Interrupted-refresh pulse-id and safe boundary projections reserve one code point for ellipsis while exact Frame evidence stays unchanged.
14. Explicit evidence-detail projection remains a separate authority and routine speech does not start naming invisible Unicode markers.
15. Regression source is not TESTED evidence until an authorized execution lane actually runs it.

## Architecture / P0 firewall

This skill is a pure projection/resource-budget rule. It owns no parser, scene graph renderer, overlay controller, state store, transport, Phone Hands action, primary-phone command, recovery daemon, Nightcore, Pocket TTS, Chromium, Context Organ action, physical acceptance, or P0 coordination.
