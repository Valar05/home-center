# Pocket TTS resurrection — phone relay stale-path fault

Observed 2026-09-06 after manual relay recovery from `/storage/emulated/0/Documents/GodotProjects/_sorting_bin/20260903-venice-quarantine/projects/home-center`.

- Home Center device heartbeat became fresh and `phone_shell` command `phc_1ea43c94-3995-4c69-b7e3-31a5abf8b0d5` was leased by `device:primary-phone`.
- The command failed before executing Pocket doctor with: `operator overlay state is unreadable; refusing remote phone control`.
- `operator_overlay_status` completed and reported package `com.homecenter.operatoroverlay` installed but `stateReadable:false`, `controlEnabled:false`, error `operator state provider returned an incomplete row`.
- `operator_overlay_start` successfully launched `com.homecenter.operatoroverlay/.MainActivity` but the state remained unreadable.
- Current GitHub `tools/android_phone_home_center_relay.py` dispatches `TERMUX_SHELL_ACTIONS` before `overlay_control_gate()`, so the recovered phone checkout is stale relative to current source.

Deterministic classification: `F005_STALE_PHONE_RELAY_OVERLAY_GATES_PHONE_SHELL`.

Required transition: update only the phone relay implementation from reviewed current GitHub source, restart the relay, prove a fresh heartbeat, then rerun `fortress_read_aloud.py --doctor`. No Pocket TTS reinstall is justified before that transition passes.
