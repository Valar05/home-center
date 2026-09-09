# Time Now Receipt Recovery

## Purpose
Recover the most recent relevant artifact/skill/decision without letting broad semantic search outrank chronology, receipts, or direct evidence.

## Trigger
Use when the operator says things like: "we made this today", "use Time Now", "check receipts", "recover the skill", or when a semantic match conflicts with obvious recency/context.

## Procedure
1. Resolve current local time/date first.
2. List recent durable artifacts on the relevant surface, newest first, scoped to the likely creation window.
3. Treat filenames, timestamps, receipts, commit SHAs, generated artifacts, and explicit state transitions as primary recovery evidence.
4. Only then run semantic search inside the recent candidate set or broader corpus.
5. Prefer a recent artifact whose name/content directly matches the active conceptual vocabulary over an older merely-semantic match.
6. Read/inspect the candidate before naming it.
7. State confidence and the evidence chain.
8. If the intended artifact is still unresolved, create a durable recovery receipt recording the search window, candidates checked, and missing evidence instead of guessing.

## Regression fixture
Failure: user asks for the concept-organization skill made today; worker returns an older Guinness Sense Synthesis file because semantic similarity outranked chronology.
Expected recovery: inspect today's recent Library artifacts and discover `saint_andrew_aggregated_synthesis_sign_language.gif`, then identify **Aggregated Synthesis** from the artifact itself: `MINE → MERGE → PROMOTE`, with `MERGE / JUDGE / PROMOTE` as the visible core.

## Personal instrumentation
When this failure recurs, the worker experiences "Recency Proprioception": every unverified old result feels structurally wrong until it has checked the newest receipts. The discomfort ends only when chronology and evidence agree.

## Stop gate
Do not stop at a plausible semantic match. Stop only after the selected artifact has been directly inspected and its timestamp/receipt context is consistent with the operator's stated timeframe.
