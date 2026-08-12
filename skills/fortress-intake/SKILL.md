# Fortress Intake

Every new operator/user delta is state, not disposable conversation.

Before planning, tool selection, execution, handoff, or completion claims:
1. persist the raw delta durably;
2. attach it to the active campaign intake journal;
3. if corrective, append it verbatim to campaign corrections and run the learning classifier;
4. persist any learned rule/config overlay before continuing;
5. reload durable campaign/config and plan from that state.

A response that acknowledges a correction without durable intake is a failure. A plan that uses a new instruction before persisting it is a failure. Intake is idempotent by content hash and must not create duplicate ledger entries.
