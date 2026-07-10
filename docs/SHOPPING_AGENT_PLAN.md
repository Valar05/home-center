# Home Center Shopping Agent Plan

## Decision

Bake cart automation into Home Center as a native Android-first shopping assistant, not as a separate web product. The feature extends the existing Home Center shopping-list, hosted speech, Firebase sync, local logging, and command parsing systems.

The product shape is:

> A voice-first household shopping copilot that can turn a shared list into a cart, show the browser state, focus the exact thing it is working on, magnify blocked elements, and pause for human checkpoints instead of attempting to bypass bot prevention.

## Why It Belongs In Home Center

Home Center already owns the household command surface:

- Family voice commands.
- Shared shopping lists.
- Shopping preferences and SKU mappings.
- hosted speech output through the local proxy.
- Firebase-backed household state.
- TickTick fallback behavior.
- Local diagnostic logs.

A standalone cart bot would become yet another cursed sidecar goblin. The better leverage move is to make shopping automation one Home Center capability, then reuse its accessibility primitives elsewhere.

## Non-Goals

This system must not become CAPTCHA bypass software.

Do not implement:

- CAPTCHA solving.
- Cloudflare / Turnstile evasion.
- Bot-prevention circumvention.
- Unattended purchases.
- Hidden checkout finalization.
- Payment submission without explicit human action.

The correct behavior is to pause, focus the required element, magnify it, narrate what is needed, and resume after the human completes the checkpoint.

## User Experience

### Main Shopping Flow

Example command:

```text
build walmart cart for shopping
```

Expected behavior:

1. Load the active Home Center shopping list.
2. Resolve list items through preferences, SKU mappings, and store memory.
3. Open a shopping session.
4. Search for missing products.
5. Add approved products to cart.
6. Pause for login, verification, checkout approval, or ambiguous choices.
7. Narrate useful milestones through hosted speech.
8. Log each meaningful action locally.

### Chat + Browser Surface

The shopping module needs a split surface:

- Chat / command transcript.
- Embedded browser view or browser session preview.
- Current task state.
- Blocker panel.
- Human action buttons.
- Resume / stop controls.

The agent should narrate meaningful state changes, not every mechanical click.

Good narration:

```text
I found three milk options. I need you to choose one.
```

Bad narration:

```text
I clicked a div. I waited 500 milliseconds. I clicked another div.
```

No one wants a play-by-play from the DOM mines.

## Browser Strategy

### Android-First Constraint

Home Center is a native Android app. A direct Playwright-in-app architecture is not the first move.

Recommended staged approach:

1. Android WebView pilot for known store flows.
2. Accessibility/focus overlay inside the Home Center UI.
3. Optional Termux/local browser automation bridge for richer Playwright-style control.
4. Later cloud/desktop agent runner only if needed.

### MVP Browser Layer

Use an Android WebView session when possible:

- User-visible.
- Same device.
- Human can intervene naturally.
- Fits Home Center's phone-first accessibility mission.

If WebView blocks too much functionality, introduce a local automation bridge:

```text
Home Center Android app
  -> local bridge API
    -> browser automation runtime
      -> persistent store sessions
```

The bridge can run under Termux initially, matching the existing hosted gateway pattern.

## Agent Model

Split the system into planner and executor.

### Planner

Inputs:

- User goal.
- Active list items.
- Store preferences.
- SKU mappings.
- Site memory.
- Browser state summary.
- Visible text / accessibility structure.
- Current screenshot or view snapshot if available.

Outputs:

- Next action.
- Target element.
- Confidence.
- Reason.
- Human checkpoint request if blocked.

### Executor

The executor does not reason. It only performs allowed actions:

- Navigate.
- Click.
- Type.
- Scroll.
- Focus.
- Wait.
- Ask human.
- Stop.

Reasoning and execution should stay separate so failures are debuggable.

## Element Focus System

Every agent action should have a visible focus target when possible.

Focus overlay should show:

- Target element outline.
- Action label.
- Confidence.
- Short reason.
- Blocker state when applicable.

Example:

```text
Target: Add to cart
Action: Click
Confidence: 92%
Reason: Product card button for selected item.
```

This makes the agent inspectable. The user should never wonder where the little shopping gremlin is poking.

## Dynamic Magnifier

When the agent needs help, magnify the relevant area.

Use cases:

- Cloudflare / human verification.
- Login button.
- Password manager prompt.
- Product ambiguity.
- Substitution modal.
- Checkout confirmation.
- Payment approval.
- Delivery time picker.

Magnifier requirements:

- Can attach to a known DOM element or screen region.
- Enlarges text and buttons.
- Can be pinned.
- Can be dismissed.
- Works with keyboard / switch style focus.
- Supports spoken explanation through hosted speech.
- Does not cover the thing the user needs to press unless pinned aside.

## Hosted Speech Integration

Home Center already has hosted speech through the Home Center gateway. The shopping agent should reuse that path.

Voice output priorities:

- Blocker explanation.
- Product choice prompts.
- Confirmation prompts.
- Progress milestones.
- Errors that require human attention.

Examples:

```text
I need your help. Walmart is asking for human verification. I focused and magnified the checkbox.
```

```text
I found organic and regular bananas. The regular option is cheaper and matches the default preference.
```

Voice must be interruptible. Shopping mode should never trap the user in a talking toaster sermon.

## Site Memory

Site memory can begin as local markdown or JSON assets and later move to Firestore-backed household memory.

Candidate local path:

```text
app/src/main/assets/site-memory/walmart.md
```

Candidate Firestore path:

```text
households/{householdId}/siteMemory/{storeId}
```

Each site memory record should include:

- Store name.
- Known URLs.
- Search behavior.
- Cart behavior.
- Login behavior.
- Known blockers.
- Human checkpoint notes.
- Preferred selectors or accessibility labels.
- Last verified date.

Example:

```md
# Walmart

Search URL:
https://www.walmart.com/search?q={query}

Known behaviors:
- Add-to-cart may open a side panel.
- Checkout can require login.
- Human verification must be completed by the user.

Human checkpoints:
- Login.
- Bot verification.
- Payment.
- Final order placement.
```

## Safety Levels

### Read Only

Can browse and describe products. Cannot modify carts.

### Cart Mode

Can search, add items, remove items, and update quantities. Cannot purchase.

### Checkout Assist

Can reach checkout and help fill non-payment fields where user has explicitly allowed it. Cannot submit payment or place order.

### Final Approval

Human only. The system may highlight and explain, but the user must perform final order placement.

## Data Model Additions

### ShoppingSession

```json
{
  "sessionId": "uuid",
  "storeId": "walmart",
  "listId": "shopping",
  "status": "active | blocked | complete | cancelled | failed",
  "currentGoal": "Add active shopping list items to Walmart cart",
  "blockedReason": null,
  "createdAt": "timestamp",
  "updatedAt": "timestamp"
}
```

### CartCandidate

```json
{
  "listItemId": "eggs",
  "query": "eggs",
  "title": "Great Value Large White Eggs, 18 Count",
  "price": "$3.42",
  "storeSku": "12345",
  "confidence": 0.88,
  "requiresUserChoice": false
}
```

### AgentActionLog

```json
{
  "timestamp": "timestamp",
  "sessionId": "uuid",
  "action": "click",
  "targetLabel": "Add to cart",
  "result": "success | failed | blocked",
  "reason": "Matched preferred SKU for eggs"
}
```

## MVP Acceptance Criteria

The first complete slice is done when:

1. Home Center has a documented shopping-agent module plan.
2. `build walmart cart for shopping` routes to a shopping-agent intent instead of being a dead-end command.
3. Shopping mode can display a dedicated blocked state.
4. Blocked state includes a reason, a resume action, and spoken hosted speech narration.
5. The UI has a reusable focus/magnifier component stub, even if early targeting is manual.
6. The agent never attempts to bypass CAPTCHA, Cloudflare, login, payment, or final purchase.
7. Regression tests cover command parsing and at least one blocked-checkpoint response.

## Implementation Milestones

### Milestone 1: Contract and Routing

- Add this plan.
- Add command parser contract for `build {store} cart for {list}`.
- Add shopping-agent status enum.
- Add failure-matrix test cases.

### Milestone 2: Blocked-State UX

- Add shopping session screen/state.
- Add blocker panel.
- Add Resume and Stop buttons.
- Add hosted speech narration for blocker messages.

### Milestone 3: Focus + Magnifier Primitive

- Add reusable focus target model.
- Add magnifier view stub.
- Support manual target metadata first.
- Later attach to WebView regions.

### Milestone 4: WebView Pilot

- Open Walmart search pages inside Home Center.
- Maintain visible session.
- Let the user intervene manually.
- Detect simple milestones by page URL/title/text where possible.

### Milestone 5: Local Automation Bridge

- Add optional Termux bridge service.
- Expose browser observation/action endpoints.
- Keep all anti-bot and checkout steps human-gated.

## Reusable Discovery

This is not just cart automation. This is a reusable pattern for Home Center:

> A human-in-the-loop browser copilot for household chores, with voice narration, visible focus, magnified blockers, and durable site memory.

Future modules can reuse the same shell for:

- Appointment portals.
- Pharmacy refill portals.
- School lunch portals.
- Utility bill sites.
- Medical forms.
- Any web chore that currently punishes blind users and tired households for existing.
