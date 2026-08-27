# Persistent Selection Semantics

## Purpose
Prevent a persistent one-of-many UI selection from masquerading as a toggle merely because `aria-pressed` is convenient.

## Core law
`PERSISTENT ONE-OF-MANY ≠ TOGGLE`.

1. Model the state machine first, then choose semantics.
2. `aria-pressed` is a toggle contract; do not use it for a choice that cannot be deselected by activating itself.
3. Persistent mutually-exclusive choice uses radio-style semantics (`radiogroup`/radio or native collection selection equivalent).
4. Selection, keyboard focus, accessibility focus, activation, detail presentation, and material-transition announcement are separate state machines.
5. Native styling does not override accessibility role/state.
6. Dynamic detail/status stays inert text; semantic repair is not permission for HTML injection.
7. Touch targets, visible focus, and reduced-motion behavior remain first-class.
8. Source semantics are not runtime assistive-technology proof.
9. A direct selected-id query is its own source-work boundary: bound work before repeated equality/case-fold comparison, preserve admitted identity exactly, and fail oversized input to no selection/null rather than truncating it into a plausible id.
10. Collection geometry follows the rendered axis: horizontal one-dimensional strip = one row with item columns; vertical strip = one column with item rows.
11. A stale selected id may yield zero selected items; never invent replacement selection.
12. Persistent selection does not authorize focus theft or Christmas-light motion.

## Native heartbeat application
`HeartbeatSelectionAccessibilityPolicy` supplies current horizontal geometry:
- `rowCount = controls.isEmpty() ? 0 : 1`;
- `columnCount = controls.size()`;
- item `rowIndex=0`, `columnIndex=index`;
- semantic id remains identity across reorder;
- direct selected-id and item lookup use the shared broad source-work throat before repeated comparison.

`OperatorOverlayService` now consumes that policy in the existing collection lifecycle after rebuild, after in-place synchronization, and after selection refresh. This is **SOURCE_WIRED / APPLIED_SOURCE**, not merely a patch proposal.

Applied owner custody:
- base owner blob `c5de1411a6b68087ae17aff83c032af754587150`;
- owner commit `47e7ac3410b48596ad22d1c72a94580133e1596f`;
- resulting owner blob `2935243f136359e3489a89108406e888b0ec2911`.

The same owner mutation migrates only the automatic heartbeat material transition to one-shot live-region semantics. Spotify/detail/Adam repeatable receipts remain explicit and unresolved; selection semantics do not authorize removing them.

## Regression doctrine
Source review/fixtures should prove:
- horizontal native metadata reports one row, N columns, `rowIndex=0`, `columnIndex=itemIndex`;
- the sole owner delegates geometry to the policy rather than copying constants;
- selection refresh rewrites current item selected metadata without moving focus;
- direct selected-id work is bounded before repeated comparisons;
- over-ceiling input cannot invent a replacement selection or truncated lookup identity;
- the heartbeat material transition uses its separately gated consequence rather than selection itself;
- Spotify/detail/Adam legacy receipts remain present until their blockers are paid.

`tools/test_try_forever_heartbeat_owner_patch_convergence.py` is current convergence source and remains **UNEXECUTED**.

## Capability membrane
`source policy → owner source wired → regression source → regression executed → tested → runtime UI → runtime TalkBack → deployed → delivered → accepted`.

Current truth: policy **SOURCE_WIRED** · native collection lifecycle **SOURCE_WIRED / APPLIED_SOURCE** · regression source **YES / UNEXECUTED** · TESTED/runtime TalkBack/deployed/delivered/accepted **NO**.

## Boundary
This skill owns no Android overlay twin, phone surface, Home Center recovery path, scheduler, transport, P0 owner, PR317/PR318 mutation, or physical acceptance chain.
