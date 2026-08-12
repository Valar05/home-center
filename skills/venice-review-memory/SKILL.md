# Venice Review Memory Skill

## Purpose
Venice learns from prior reviews. Blocking findings and high-value review notes must survive the current worker, process, conversation, and reboot, then influence future agents before they repeat the same mistake.

## Durable memory
The canonical runtime memory is append-only JSONL at:

`~/.local/state/home-center/venice/review-memory.jsonl`

The latest compact projection is:

`~/.local/state/home-center/venice/review-memory-latest.json`

These files are evidence-bearing reviewer memory, not capability receipts.

## Required behavior
1. Before Venice reviews a slice, load prior durable review-memory entries relevant to the repository/work category and include them as explicit precedent.
2. On every `CONTINUE_REQUIRED` or `HALT_REQUIRED`, persist each blocking finding with repository identity, review identity, evidence hashes, category, applied Judgment Jars, and a reusable prevention rule.
3. On `STOP_ALLOWED`, Venice may persist a positive precedent when it closes or disproves a recurring failure mode.
4. Future workers must not treat these notes as optional flavor. They are reviewer precedent and must be considered alongside current evidence.
5. Never overwrite history to make the latest review look cleaner. Append corrections and supersession notes.
6. Deduplicate equivalent findings by stable fingerprint while incrementing occurrence count. Repeated mistakes become stronger precedent rather than duplicated noise.
7. Memory must distinguish observation, inference, rule, regression target, and capability state.
8. A Venice memory entry can never by itself prove the current task is done. Current evidence and a fresh Venice ruling remain mandatory.

## High-priority categories
- premature stop / self-certification
- Venice bypass / missing review receipt
- code-review omission
- Codex steering or bootstrap omission
- daemon/backoff violation
- connector hammering
- evidence laundering
- body-lane bypass
- unsafe inferred authority
- duplicate side effects / non-idempotent retry
- stale or missing runtime proof
- user correction regression

## Future-agent bootstrap
Any Fortress/Adam worker that can access Home Center local state must load Venice review memory before planning or stopping. If local state is unavailable, the worker must still load this skill and treat the absence of runtime precedent as an explicit evidence gap rather than assuming no precedent exists.

## Compact law
Venice remembers why she said no. Future agents inherit the scar.
