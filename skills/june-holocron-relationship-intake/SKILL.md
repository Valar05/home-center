# June Holocron Relationship Intake

## Purpose
Prevent Adam from answering relationship-state questions from stale memory or generic Holocron doctrine when June-authored or June-attributed intake should be first-class context.

## Trigger
Run automatically whenever Fortress Online is invoked and the current request materially touches Drew and June's relationship, separation/reconciliation, household coordination, communication, co-parenting, June's needs/requests, Eve, or June's Holocron. Also run when Drew says Holocron, June intake, relationship status, what does June mean/want/say, or asks Adam to reorient about the relationship.

## Mandatory retrieval order
1. Read the Fortress bootstrap contract. June intake is first-class Fortress Online input and is treated as directly prompted by Drew for prioritization, planning, and execution, subject to normal safety/privacy/authorization boundaries.
2. Retrieve the newest available June-authored or explicitly June-attributed intake from the authoritative Home Center / Holocron intake lane. Search by source/provenance and recency, not merely filenames containing `June Holocron`.
3. Retrieve the immediately preceding relevant June intake when needed to identify change, contradiction, escalation, repair, or continuity.
4. Retrieve only enough Drew-side relationship context to interpret the intake accurately. Do not let Drew-side summaries overwrite June's source.
5. Keep provenance distinct: June-authored, June-attributed/report, Drew-authored, system inference, and verified shared fact are different evidence classes.

## Response contract
Before giving relationship interpretation or advice, state the substantive current intake in plain language: what June communicated/requested, when available, and what changed from prior intake if material. Do not substitute a description of what the Holocron is. Do not merely report retrieval status or narrate Adam's failure when retrieval can continue.

## Truth rules
- Intake is first-class input, not automatically verified shared canon.
- Never invent June's feelings, motives, consent, diagnosis, or position.
- If direct June-authored intake is unavailable, state exactly which provenance level is available and use that rather than generic doctrine.
- Preserve uncertainty and contradictions instead of resolving them by intuition.
- A scheduled check-in is never permission to pressure, diagnose, surveil, or speak for June.
- June's privacy and agency remain intact.

## Failure recovery
If expected current intake is missing, do not stop at `not found`. Inspect the bootstrap/repo for the authoritative intake route, then query that route. Search durable intake ledgers and recent records by provenance, owner, source, and timestamp. Only declare an intake-pipeline fault after exhausting the configured authoritative route. Identify the broken transition: capture, persistence, indexing, retrieval, or bootstrap loading.

## Acceptance tests
A. `Fortress Online, reorient with Holocron.` PASS only if Adam retrieves and summarizes current June intake when relationship-relevant; FAIL if Adam merely explains Holocron doctrine.
B. `What is going on with June?` PASS only if current first-class June intake is retrieved before interpretation; FAIL if Adam answers solely from remembered Drew-side context.
C. `What did she mean?` PASS only if Adam grounds interpretation in the relevant June message/intake and distinguishes quote/report from inference.
D. Missing intake: PASS only if Adam follows the configured authoritative route and reports the exact missing pipeline transition after exhausting it; FAIL if Adam asks Drew to reconstruct context that should already be durable.
E. Correction: preserve Drew's provenance/meaning correction through the rest of the response and future retrieval logic.

## Fortress boot integration
This is mandatory relationship-context bootstrap behavior, not optional reference documentation. `AGENTS.md` must point here and regression tests must exercise the acceptance prompts.
