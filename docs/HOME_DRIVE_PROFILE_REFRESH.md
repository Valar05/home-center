# Home Drive Profile Refresh

Home Drive speaker profiles are durable cross-document defaults. The Android app can ingest speakers while narrating a document, and this repo also has a scheduled refresh lane for exported Drive text/JSON so starter profiles keep up without manual review.

## Commands

Start the durable refresh loop in tmux:

```sh
sh tools/home_drive_profile_refresh_tmux.sh start
```

Check status and recent logs:

```sh
sh tools/home_drive_profile_refresh_tmux.sh status
```

Run one refresh pass without tmux:

```sh
sh tools/home_drive_profile_refresh_tmux.sh once
```

Attach or stop the durable session:

```sh
sh tools/home_drive_profile_refresh_tmux.sh attach
sh tools/home_drive_profile_refresh_tmux.sh stop
```

## Refresh Contract

The loop watches `generated/home_drive_voice_profiles/drive_exports` for `.txt`, `.md`, and `.json` exports. JSON may be a Home Center Drive read payload with `name`, `fileId`, and `text`. Each pass runs:

```sh
python3 tools/home_drive_speaker_profile_scan.py generated/home_drive_voice_profiles/drive_exports --merge
```

Outputs:

- Registry merge target: `app/src/main/assets/home_drive_character_voice_registry.md`
- Latest scan report: `generated/home_drive_voice_profiles/latest_refresh_profiles.md`
- Scheduler log: `generated/home_drive_voice_profiles/refresh.log`

Defaults are deliberately overrideable through environment variables:

- `HOME_DRIVE_PROFILE_REFRESH_INTERVAL_SECONDS`, default `21600`
- `HOME_DRIVE_PROFILE_SCAN_INPUT`, default `generated/home_drive_voice_profiles/drive_exports`
- `HOME_DRIVE_PROFILE_REFRESH_OUTPUT`, default `generated/home_drive_voice_profiles/latest_refresh_profiles.md`
- `HOME_DRIVE_PROFILE_REGISTRY`, default `app/src/main/assets/home_drive_character_voice_registry.md`
- `HOME_DRIVE_PROFILE_GATEWAY`, default Home Center Firebase gateway
- `HOME_DRIVE_PROFILE_TMUX_SESSION`, default `home-drive-profile-refresh`

The scanner trusts structured cues only: `[voice:id]`, `[speaker:name]`, and uppercase speaker headings like `LEXEN:`. Katie - Friendly Fixer remains the Drive Narrate fallback narrator voice for Vacation-style first-person renders. Voice catalog lookup is metadata-only; if the catalog is unavailable, the scan still completes with stable defaults and records the warning in the report.

## General scheduler entrypoint

The durable tmux surface is now shared across Home Center jobs:

```sh
sh tools/home_center_scheduler_tmux.sh start
sh tools/home_center_scheduler_tmux.sh once home-drive-profile-refresh
```

`tools/home_drive_profile_refresh_tmux.sh` remains as a compatibility wrapper.
