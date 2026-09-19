# Termux Clean-Slate Architecture

Status: canonical phone-runtime policy

## Purpose

Termux is a maintenance shell, not an always-on application surface. Background Home Center durability must be quiet, deterministic, and self-healing. Clean-slate means **no visible or competing resurrection machinery**, not “no watchdogs.”

A watchdog that prevents Drew from becoming command transport is part of the intended runtime when it is narrow, invisible, and evidence-backed.

## Preserved lanes

### Phone Hands relay watchdog

The canonical production watchdog is `tools/phone_hands_watchdog.sh`, installed by `tools/install_phone_hands_watchdog.sh`.

It may use:
- one resident Termux watchdog loop started by Termux:Boot;
- one persisted Termux JobScheduler trigger as a backstop if Android kills that loop.

Those are launch triggers for **the same watchdog implementation**, not competing supervisors. Both must share the same run lock, inspect the same relay heartbeat/source identity, and route recovery through `tools/home_center_phone_relay_recover.sh`.

The production watchdog must:
- keep the Home Center background relay alive without Drew touching Termux;
- protect a bounded in-flight Phone Hands command from premature restart;
- recover an absent or stale idle relay through the canonical recovery primitive;
- fail closed on ambiguous duplicate relay processes;
- never require Shizuku/rish for baseline relay health or recovery;
- never acquire a global Termux wake lock;
- never create a persistent Termux notification;
- never launch Android settings or resurrect the operator overlay.

Manual `home_center_phone_relay_recover.sh` execution is break-glass maintenance, not the normal operating procedure.

### SSH

`sshd` supervised by `fortress-sshd-guardian` is the independent break-glass maintenance lane. It may remain quietly listening on its configured port. It must not require a persistent notification, overlay, or global Termux wake lock.

## Retired architecture

The following legacy patterns remain retired:

- multiple independent watchdog/daemon implementations competing to own the same relay;
- watchdogs that select the Firebase/Command Center server module instead of the Python phone relay;
- separate PID-file truths that can create duplicate relay processes;
- independent restart implementations instead of the canonical relay recovery script;
- `termux-wake-lock` from health/watchdog loops;
- persistent Home Center/Phone Hands Termux notifications;
- notification buttons that launch operator shell commands;
- automatic operator-overlay restart/rebuild or silent `SYSTEM_ALERT_WINDOW` restoration;
- recovery code that turns visible UI back on merely because a background service failed.

The status-menu and operator-overlay resurrection experiments remain opt-in archaeology unless separately recommissioned. The canonical Phone Hands relay watchdog is **not** legacy and must not be disabled by default.

## Explicit decommissioning contract

`tools/decommission_termux_legacy.sh` remains a reversible cleanup tool for an explicitly requested cleanout. It may stop the canonical watchdog when the user is intentionally decommissioning the Termux runtime, but it is not a production installer path and must never be invoked merely because the watchdog installer runs.

A decommission pass must:
1. archive Home Center state and Termux:Boot entries under `/sdcard/Fortress-Graveyard/Termux/` before mutation;
2. capture before/after process and JobScheduler receipts;
3. stop the explicitly targeted Home Center supervisors;
4. remove targeted Home Center-owned boot entries and persisted jobs;
5. remove known persistent legacy notifications and release leaked global wake locks;
6. preserve `sshd` and `fortress-sshd-guardian` unless the user explicitly decommissions them too;
7. report `CLEAN_SLATE_PENDING_OBSERVATION`, never runtime acceptance from source changes alone.

## Acceptance

Implementation acceptance and phone-runtime acceptance remain separate.

Implementation passes when:
- `node tools/termux_clean_slate_policy_test.mjs` reports `TERMUX_CLEAN_SLATE_POLICY=PASS`;
- `python tools/test_phone_hands_watchdog_contract.py` reports PASS.

Production phone-runtime acceptance requires fresh physical evidence that:
- the canonical watchdog loop is alive;
- persisted JobScheduler 6405 points to the same watchdog binary;
- no persistent Home Center/Phone Hands Termux notification or global wake lock exists;
- no visible overlay/settings surface is resurrected by watchdog health checks;
- a bounded in-flight command is protected rather than killed;
- deliberately terminating the relay causes the same watchdog to invoke canonical recovery and Home Center resumes with a new current-source relay heartbeat;
- SSH guardian/sshd remain available as independent break-glass maintenance.

Do not report repository state, scheduled-task existence, or stale device registry state as phone-runtime acceptance evidence.
