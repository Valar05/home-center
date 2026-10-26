# Pocket ASMR campaign (2026-10-26)

Status: **Git-authored prototype, NOT installed or field tested on THECAULDRON**. Do not confuse the live Ritsu phone-relay sender with an offline WAV renderer.

## Command on THECAULDRON (after pinned Git deployment and configuring an actual offline renderer)

```text
pocket init
pocket doctor
pocket asmr asmr.txt
pocket asmr asmr.txt --voice amused
pocket status JOB_ID
pocket path JOB_ID
```

Default voice: `whisper`. Allowed: normal, whisper, amused, happy, somber, upset (somber alias mapping belongs to existing voice runtime).

`pocket.cmd` is the Windows command entrypoint, `pocket.py` is the durable queued job runner. Put the campaign folder on PATH or install the command as appropriate through a reviewed pinned campaign. Jobs are launched detached, written under `%USERPROFILE%/PocketASMR/jobs/JOB_ID`. A job has `status.json`, `transcript.txt`, `worker.log`, `render.log` and on successful completion `audio.wav`. No success is claimed without an actual wave-readable WAV, duration, bytes and SHA-256. `status` remains usable after terminal disconnect. Idempotent job IDs are unique and outputs are never overwritten.

**Renderer gate:** Run `pocket init`, then configure `%USERPROFILE%/PocketASMR/renderer.json` with a `renderer_argv` *array* for the EXISTING verified offline Pocket TTS CLI. Supported placeholders: `{text}` input filename, `{wav}` target audio, `{voice}` approved profile. This intentionally does NOT guess that the existing `ritsu_say.py` supports offline file rendering; current proof indicates it handles live relay tickets. Until the correct local offline interface is inspected, `pocket doctor` returns BLOCKED and no render is started. No substitute TTS, no arbitrary shell interpolation, no model restarts.

## Phone retrieval, no SFTP browsing

Install `pocket-phone.sh` as a shell command `pocket` on Termux via the Git-authored campaign, configure `POCKET_CAULDRON_HOST` to the **existing** SSH host / address, and optionally `POCKET_REMOTE_DIR` (defaults to `C:/Users/dclar/PocketASMR`). Then:

```sh
pocket pull JOB_ID
```

It uses existing SSH credentials and `scp` internally, pulling directly into `~/storage/downloads/ritsu-asmr-JOB_ID.wav`; there is no manual SFTP wizard. The command refuses overwrite and checks that a nonempty file arrived. This transfer is **proposed but not yet device verified**; Windows OpenSSH path mapping and the actual phone SSH host must be tested. The underlying audio job can run on THECAULDRON while the phone is disconnected.

## Important remaining acceptance gates

1. Read exact deployed Windows Pocket local API / renderer behavior and set `renderer_argv` to a proved WAV-producing command.
2. Git pin and install without changing active Warm voice worker, maintenance lock or phone relay.
3. Submit a short test transcript; observe detached process, then completed status and valid real WAV.
4. Pull by the Termux alias, verify bytes and hash against the Windows receipt, open in a player and confirm audio heard in earbuds.
5. Verify failures, rerun/recovery and long 15-minute transcript. Measure duration; 15 minutes is a target, not inferred from words.

Drive campaign transcript: https://docs.google.com/document/d/1nA1D7b22Glql1Lx0V8JPfKy9FmR6Rn9QnZ_GJxnsHsQ/edit
