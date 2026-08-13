# Chromium Throne babysitting policy

Chromium Throne workers run in ChatGPT **Pro reasoning** by default. They are deliberately bounded and needy. Instant is not the default and requires an explicit later override from Drew.

Every worker must execute Venice's Judgment Jars directly as the primary review path. This is normal worker behavior, not a fallback for an unavailable local Venice runtime.

- Work one small feature or acceptance slice at a time. No broad campaign execution and no Great War prompts.
- Each slice must have an explicit done condition and produce evidence checkpoints as it advances.
- Before substantive execution, run the required research/plan/jars/antagonism/Venice plan gate and require `PLAN_ALLOWED` for non-trivial mutation.
- Before stopping, finishing, or declaring the slice complete, run a fresh Venice Judgment-Jar completion review.
- `CONTINUE_REQUIRED` means continue the same slice. It explicitly forbids treating the current response boundary as a stopping point.
- `STOP_ALLOWED` is the only normal Venice permission to stop a slice. `HALT_REQUIRED` stops mutation only at a genuine hard boundary.
- Prefer asking for one genuinely irreducible missing decision over inventing architecture when the current slice is underspecified. Retrieve what can be retrieved first.
- Stay inside the current commission. Do not expand scope because adjacent work looks useful.
- After a useful checkpoint, reassess thread health and Venice state before continuing.
- Treat repeated misunderstanding, instruction drift, bloated context, circular retries, or inability to restate the current slice cleanly as thread choke.
- On choke, do not keep arguing with the same thread. Produce a compact handoff containing durable context, completed evidence, current slice, unmet acceptance, constraints, and exact next action; then continue in a fresh ChatGPT thread.
- A fresh thread receives PORTCULLIS LOCKED, durable campaign context, the handoff packet, one bounded next slice, applicable Venice/Jar precedent, and the outstanding continuation obligation.
- Never ask one worker to hold the whole campaign in working memory. Chromium Throne owns continuity; workers own bites.
- Drew's hands remain the final fallback after authorized body lanes are exhausted.
