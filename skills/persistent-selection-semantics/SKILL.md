# Persistent Selection Semantics

## Purpose

Prevent a persistent one-of-many UI selection from masquerading as a toggle merely because `aria-pressed` is convenient.

## Trigger

Use when a DOM/source specimen or native-inspired UI exposes multiple mutually exclusive choices and activating the already-selected choice does **not** switch it off.

## Law

1. Model the state machine first, then choose semantics.
2. A control with `aria-pressed` is a toggle contract: activation can change pressed ↔ not pressed. Do not use it for a persistent choice that cannot be deselected by activating itself.
3. A persistent one-of-many choice belongs to a radio-style contract: one selected item, `aria-checked`, a radio-group owner, and deterministic keyboard navigation.
4. For custom radio controls, keep one item in the tab sequence and move that tab stop with the selected item. Arrow keys move/select within the group; Home/End may select the first/last item.
5. Selection state, focus state, activation state, and application consequence are separate. Do not infer one from another.
6. Native `button` styling may be reused, but styling does not override the exposed accessibility role/state machine.
7. Use `textContent` or equivalent inert text projection for dynamic status/detail; selection repair is not permission to introduce HTML injection.
8. Keep touch targets and visible focus first-class. Reduced-motion behavior remains independent.
9. A source specimen is not runtime accessibility proof. Source, test, runtime assistive-tech behavior, deployment, delivery, and acceptance remain separate states.
10. Correct a recurring semantic failure at the reusable rule, not only at the latest specimen. Filename or art direction does not reset the contract.

## Regression doctrine

Source review or fixtures should prove:

- the group exposes one persistent-selection owner (`radiogroup` or native equivalent);
- each choice exposes radio selection state (`aria-checked` or native equivalent), not toggle state;
- exactly one selected item is the active tab stop;
- clicking an already-selected item does not create an impossible toggle contract;
- arrow navigation changes both focus and selected item deterministically;
- Home/End boundaries are deterministic when implemented;
- dynamic status text remains inert text;
- touch/focus visibility remains intact.

## Current scar

`docs/try-forever/heartbeat-swan-veil-semantic-scar-source.html` previously used persistent one-of-many `button[aria-pressed]` controls. The repaired source uses a radio group, `role=radio` + `aria-checked`, roving `tabindex`, and arrow/Home/End navigation. That is source semantics only; browser/screen-reader runtime behavior remains unproven until executed.

## Boundary

This skill owns no Android overlay controller, phone surface, Home Center recovery path, scheduler, transport, P0 owner, or physical acceptance chain.
