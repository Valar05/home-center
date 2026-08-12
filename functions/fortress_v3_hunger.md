# Fortress V3 — Hunger / Hyperbolic / Extend

## Hunger
The system must keep working when the model is forgetful, lazy, context-starved, or wrong. Automatic update means state changes are captured by runtime mechanics, not by the model remembering to write them down. The user must not serve as state synchronization middleware.

## Hyperbolic
Assume every conversational omission compounds. Assume multiple campaigns are active, names overlap, connectors fail, bodies exist but routing is hidden, receipts arrive out of order, and inference confidently guesses wrong. Therefore raw events are append-only truth; active campaign changes are explicit events; receipts advance only named boundaries; model classifications are advisory until converted into typed events; reconstruction from the log must deterministically yield the same next action.

## Extend
The event log becomes the single durable source for campaigns, corrections, capabilities, failures and receipts. Derived ledger/config are projections, disposable and rebuildable. The operator surface should append events and ask the reducer for the next action. New Home Center capability is justified only if existing tools cannot provide one atomic append/read event operation with receipt semantics.

## Non-goals
- no new agent framework
- no model-owned mutable ledger
- no regex-selected current campaign
- no hidden substitution of phone/desktop/GitHub lanes
- no conversational-only corrections
