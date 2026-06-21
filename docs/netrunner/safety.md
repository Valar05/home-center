# Netrunner Safety Model

Netrunner is allowed to make hostile websites more usable. It is not allowed to quietly take irreversible actions.

## Confirmation gates

Require explicit user confirmation before:

- purchases
- recurring billing
- account deletion
- password changes
- sending messages
- submitting medical, legal, financial, or government forms
- changing privacy/security settings
- accepting contracts or terms
- installing software

## Sensitive data redaction

Never store raw values from:

- password fields
- payment fields
- tokens or API keys
- medical identifiers
- government identifiers
- private messages
- authentication codes
- address/contact fields unless explicitly needed and stored in personal profile vault

## Element Command Mode safety

Friendly element commands may alter local display, but should not permanently change remote site data.

Allowed local commands:

- hide this annoyance
- make this bigger
- read this
- explain this
- pin this
- undo last page change
- restore page display

Risky commands require confirmation:

- click this
- submit this
- buy this
- send this
- delete this
- unsubscribe
- change account setting

## DOM override rules

Temporary DOM/CSS overrides are allowed for accessibility and visual cleanup.

Examples:

- hide fixed overlays
- restore body scrolling
- enlarge text
- increase contrast
- isolate a selected product card
- remove visual clutter from the local rendering

Netrunner must maintain an undo stack for every local override.

## Shared learning safety

A local action can become a shared candidate only after redaction and normalization.

Never promote:

- user secrets
- user account state
- private form values
- payment details
- exact personal messages
- health/legal/financial content

## Automation safety ladder

1. Observe human action.
2. Highlight likely target.
3. Suggest action.
4. Ask permission to act.
5. Act under confirmation gate.
6. Stop before irreversible action unless explicitly approved.

Full automation comes last, not first.
