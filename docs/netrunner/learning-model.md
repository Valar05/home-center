# Netrunner Learning Model

Netrunner learns by observing real human web sessions before it attempts full automation.

## Core rule

Record first. Extract patterns second. Automate third.

A browser that cannot learn is just another automation tool. A browser that records, validates, and promotes discoveries becomes shared infrastructure.

## Episode

An episode is one attempted web task.

Examples:

- User compares three pool clarifiers.
- User cancels a subscription.
- User downloads a bill.
- User hides a modal and completes a form.

Episode fields should include:

- user intent
- site origin
- device class
- accessibility mode
- steps observed
- DOM snapshots or compact DOM summaries
- element interactions
- user corrections
- applied element commands
- DevTools inspection events
- result
- sensitive-field redaction report

## Discovery

A discovery is a reusable claim extracted from one or more episodes.

Examples:

- This site hides checkout totals behind an expanded order summary.
- This modal can be dismissed by hiding a fixed overlay and restoring body scroll.
- The useful price is the unit price near the selected fulfillment option, not the sponsored tile price.
- The real button has role `button` and text `Continue`; the fake ad button is visually similar but in a sponsored container.

## Promotion pipeline

Discovery states:

1. observed - captured from one episode.
2. candidate - normalized into a reusable claim.
3. tested - confirmed in additional sessions or test harnesses.
4. trusted - safe to suggest automatically.
5. deprecated - known stale, broken, or unsafe.

## Trust rules

- One user session cannot globally rewrite behavior.
- User-specific preferences remain personal unless explicitly generalized.
- Sensitive content is never promoted.
- Repeated failures demote discoveries.
- Risky workflows require stronger evidence.

## Element commands as learning events

When a user long-presses an element and chooses `Hide this annoyance`, Netrunner should record:

- selector candidates
- visual bounds
- element role
- text label
- z-index / fixed positioning hints
- whether page scroll was blocked
- whether the user later undid the action
- whether task success improved afterward

This turns accessibility repairs into reusable anti-hostility playbooks.

## DevTools inspection as learning events

Netrunner should include a first-class DevTools-style inspector, not as a developer-only afterthought.

When the user inspects an element, record:

- DOM path
- accessible name
- ARIA role
- computed visibility
- bounding box
- box model measurements
- selector candidates
- nearest useful heading/landmark
- whether it appears to be an overlay, modal, form control, product card, nav item, ad, or decoration

The inspector should help both humans and agents understand why an element matters.

## Discovery distillation prompt

After each episode, the cloud brain should ask:

What did this session teach us that would help the next user accomplish the same kind of task faster, more safely, or with less visual friction?
