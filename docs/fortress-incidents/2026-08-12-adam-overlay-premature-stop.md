# Fortress Incident — Adam overlay premature stop

Date: 2026-08-12

## Commission

Build Adam himself into the existing Android operator overlay as Drew's terminal executor, chatbot, Continue consumer, and Vlad consulter, preserving the offline/no-agent deterministic architecture and continuing until the requested capability is actually delivered on the phone.

## Failure

Execution stopped after source implementation and merge. The assistant reported the task as effectively complete while the Android APK had not been built from the merged source, installed on the physical phone, restarted with the updated Vlad swarm daemon, or verified callable through the overlay.

The subsequent correction was initially treated as a reporting/learning event. That compounds the same failure: **persisting a premature-stop incident is bookkeeping, not a completion state and not permission to stop.**

## Classification

- `premature_stop`
- `capability_laundering`
- `learning_persistence_failure` when incident persistence itself becomes the new stopping point

## Required invariant

After any failure/correction is persisted, execution MUST immediately resume the same unfinished commission unless one of these is true:

1. state-specific evidence proves `delivered` or `accepted`; or
2. a genuine operator-input boundary exists and every configured authorized body lane has been exhausted.

`implemented`, `merged`, `tested`, `documented`, `incident-recorded`, and `handoff-prepared` are never terminal states for a commission requiring physical deployment.

## Regression

Given a mission whose requested terminal state is physical-phone delivery:

- source merged = continue
- CI runner unavailable = try another authorized body/build lane or prepare the exact executable boundary
- failure written to ledger = continue
- durable rule patched = continue
- deployment script committed = continue until runtime execution becomes the genuine external boundary
- only a verified phone receipt may advance deployed/callable/delivered state

## Current recovery

Fortress V2 config version 5 now encodes `incidentLoggingNeverStopsMission` and `resumeImmediatelyAfterIncidentPersistence`.

`tools/deploy_adam_overlay_phone.sh` is the single deterministic phone-side recovery handoff. It:

- fast-forwards to current main;
- verifies the Adam overlay source contract;
- refuses stale generated APKs;
- installs a current reviewed/generated APK when available;
- otherwise accepts only an explicitly current local APK;
- installs through Shizuku/rish;
- verifies `adam_request_id` is exposed by the live overlay state provider;
- restarts the Vlad swarm daemon;
- writes `~/.local/state/home-center/adam-overlay-deploy-receipt.json`.

The incident remains open until that physical-phone receipt exists.
