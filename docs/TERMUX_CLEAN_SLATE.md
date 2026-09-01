# Termux Clean-Slate Architecture

Status: canonical phone-runtime policy

## Purpose

Termux is a maintenance shell, not an always-on application surface. Background Home Center features must not create visible terminal activities, persistent Termux notifications, global Termux wake locks, or multiple overlapping resurrection mechanisms.

## Preserved lane

`sshd` supervised by `fortress-sshd-guardian` is the break-glass maintenance lane. It may remain installed and quietly listening on the configured SSH port. It must not require a persistent notification, overlay, or global Termux wake lock.

## Retired architecture

The following legacy patterns are retired by default:

- Termux:Boot + persisted Termux JobScheduler + permanent watchdog loop for the same worker.
- `termux-wake-lock` from health/watchdog loops.
- Persistent Home Center/Phone Hands Termux notifications.
- Termux notification buttons that launch `bash -l -c` operator commands.
- Automatic operator-overlay restart/rebuild or silent `SYSTEM_ALERT_WINDOW` restoration.
- Recovery code that turns visible UI back on merely because a background service failed.

Archaeology may explicitly opt into old implementations with the dedicated `HC_ENABLE_LEGACY_*` environment variables. Production/default behavior must remain retired.

## Decommissioning contract

`tools/decommission_termux_legacy.sh` is the reversible cleanup entrypoint. It must:

1. Archive Home Center state and Termux:Boot entries under `/sdcard/Fortress-Graveyard/Termux/` before mutation.
2. Capture before/after process and JobScheduler receipts.
3. Stop known legacy Home Center/Phone Hands supervisors.
4. Remove Home Center-owned Termux:Boot resurrection entries.
5. Cancel the known persisted legacy watchdog job.
6. Remove known persistent legacy notifications.
7. Release the leaked global Termux wake lock.
8. Disable the operator overlay when authorized Android shell access is available, without uninstalling the APK.
9. Preserve `sshd` and `fortress-sshd-guardian`.
10. Report `CLEAN_SLATE_PENDING_OBSERVATION`; source changes or a cleanup receipt alone are not proof that visible black Termux boxes have stopped on the physical phone.

## Acceptance

Implementation acceptance and phone-runtime acceptance are separate.

Implementation passes when `node tools/termux_clean_slate_policy_test.mjs` reports `TERMUX_CLEAN_SLATE_POLICY=PASS`.

Phone-runtime acceptance requires fresh physical-device evidence after decommissioning:

- no recurring visible Termux activities during the observation window;
- no Home Center/Phone Hands persistent Termux notifications;
- no leaked Termux global wake lock;
- retired boot/job/watchdog surfaces absent;
- operator overlay disabled;
- SSH guardian/sshd still available as break-glass maintenance.

Do not report project source, repository state, or stale device registry state as phone-runtime acceptance evidence.
