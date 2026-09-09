# Fortress Intake

Every new operator/user delta is state, not disposable conversation.

Before planning, tool selection, execution, handoff, or completion claims:
1. persist the raw delta durably;
2. attach it to the active campaign intake journal;
3. run the aggressive Chekhov admission pass: any object, organism, device, body, environment, system, or prop with violent use, threat, affordance, intention, imagination, opinion, coercion, defense, or meaningful refusal becomes a Chekhov candidate;
4. pass every admitted candidate through `tools/chekhov_kinesis_engine.py` (or the identical `chekhov-kinesis/v1` service transform) before downstream kinetic/Story-Simulator reasoning; preserve `unknown` mechanics rather than inventing them;
5. if corrective, append the delta verbatim to campaign corrections and run the learning classifier;
6. persist any learned rule/config overlay before continuing;
7. reload durable campaign/config and plan from that state.

Automated conversation-mining and backfill jobs use the same Chekhov admission law. They may over-admit. When a miner has already admitted an item, it must preserve that decision as `chekhov: true` plus the triggering excerpt/source refs; the deterministic kinesis pass sorts evidence states and mechanics later.

A response that acknowledges a correction without durable intake is a failure. A plan that uses a new instruction before persisting it is a failure. Intake is idempotent by content hash and must not create duplicate ledger entries. A Chekhov candidate is not canon merely because it was admitted.
