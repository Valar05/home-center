# Ritsu ASMR Offline v1: THECAULDRON Pocket whisper campaign

## Commission
Use the **existing** Ritsu Pocket TTS whisper state on THECAULDRON, controlled from the owner's Termux phone via the installed `cauldron` SSH command. Do not replace TTS, touch the live Ritsu worker, or send audio into the live phone queue.

## Exact source
- Phone: `tools/campaigns/ritsu_asmr_phone.py`
- Windows: `tools/campaigns/ritsu_asmr_windows.py`
- Tests: `tools/campaigns/test_ritsu_asmr_offline.py`
- Voice: approved whisper state SHA-256 `B99EB2E16612E8B8C3E3A96F74BD631676CC79071779537FD94C564DB5796BE5`
- Engine: existing `http://127.0.0.1:10205/tts` Pocket repertoire service, loopback only.
- Transport: installed Termux `cauldron` command, authenticated SSH with Windows PowerShell EncodedCommand. No alternate SSH login or shell agent.
- Windows output: `%LOCALAPPDATA%\RitsuASMR\runs\<episode>\<episode>.wav`, plus transcript, progress, logs and receipt.
- Phone output: `~/.local/state/ritsu-asmr/latest.txt`, also best-effort Termux clipboard.

## Operator (Termux)
The phone repository must contain the exact committed scripts. Do not overwrite dirty worktrees.

```bash
python3 ~/storage/documents/GodotProjects/home-center/tools/campaigns/ritsu_asmr_phone.py doctor
python3 ~/storage/documents/GodotProjects/home-center/tools/campaigns/ritsu_asmr_phone.py start
python3 ~/storage/documents/GodotProjects/home-center/tools/campaigns/ritsu_asmr_phone.py status
python3 ~/storage/documents/GodotProjects/home-center/tools/campaigns/ritsu_asmr_phone.py receipts
```

For an authored transcript on the phone (UTF-8, paragraphs separated by blank lines):

```bash
python3 ~/storage/documents/GodotProjects/home-center/tools/campaigns/ritsu_asmr_phone.py start --episode RITSU_ASMR_E01 --input ~/storage/downloads/ritsu_episode01.txt
```

Further verbs: `stop` requests cooperative cancellation between passages, and `resume` restarts a stopped or failed run after confirming the preceding detached worker is no longer active. Never blindly resume a run still marked launched/rendering.

## Semantics and acceptance
- `doctor` confirms localhost Pocket model loaded and approved whisper hash. It does not synthesize.
- `start` launches an isolated Windows process and returns promptly; it does not wait for completion.
- `status` returns latest Windows run status; it is not a verified live heartbeat.
- `receipts` is available only after the entire WAV is assembled and measured.
- The initial no-input canary is short, not a fifteen-minute episode.
- An entire coherent passage is at most 450 characters. Deliberate stage directions `[Pause]`, `[Long gentle pause]`, `[Final long gentle silence]`, or `[Pause:1500]` become silence, not speech.
- It refuses to mechanically split overly long passages, reuse corrupt cache, overwrite output, or substitute a voice.
- Existing episode IDs lock transcript SHA-256. Avoid changing input behind an existing ID.

## Current exclusions and open gates
This v1 is a **Windows-render / phone-controlled** implementation. The completed WAV remains on THECAULDRON. Downloading it to Android and uploading/verifying it in Drive are **not yet implemented**. Neither audio playback nor human HEARD has been verified. No foley/mixing layers other than silence are implemented. Stop is cooperative, not a fully proven process-tree kill. Phone notification integration and physical process-isolation acceptance are also open. Do not label this production-ready or the fifteen-minute campaign complete until those are addressed.

## Failure doctrine
- If `cauldron` is absent or SSH authentication fails: block, no alternate transport.
- If HTTPS pinned source cannot be fetched on Windows: block, do not run floating HEAD source.
- If Python/Pocket service/voice state absent: block, no downloads of another model.
- If a previous worker is ambiguous: block a duplicate launch.
- If an individual WAV fails: retain existing verified segments and report the exact stage.
- Preserve Pocket voice assets, Windows and Android worktrees, authentication keys, and live phone queue unchanged.

## 2026-11-10 Pocket listener recovery
Observed on physical Termux -> existing cauldron SSH -> THECAULDRON: doctor reached Windows but `127.0.0.1:10205` refused connections (WinError 10061). Phone SSH return must not be mistaken for Pocket service readiness.

Before asking the existing watchdog to do anything, run `python3 tools/campaigns/ritsu_asmr_phone.py inspect`. This only examines the existing named Windows task `Ritsu Pocket Repertoire Watchdog`, its last result, process identities and listening port. If the task exists, is Ready, no listener and no matching Pocket/supervisor processes exist, `python3 tools/campaigns/ritsu_asmr_phone.py recover` asks **that same pre-existing scheduled task** to start. It does not install, patch, kill, replace or manually launch TTS. If task is running, absent or evidence ambiguous, recovery fails closed. The recovery then waits a bounded period for the original Pocket `/health` endpoint and exact approved whisper voice SHA. A task scheduling receipt alone never proves the server loaded. The **first next command** is `inspect`, not `recover`, to learn which branch applies.

## 2026-11-17: scheduled render and verified phone retrieval
Physical evidence: the user released the existing Pocket maintenance sentinel; Pocket health returned the exact approved whisper SHA and 24 kHz. An initial canary launch through SSH returned PID 21552, then no worker process or completion receipt remained after disconnect. The cause is consistent with session-owned child termination but was not independently confirmed.
The updated launcher stages renderer source in a SHA-specific Windows code directory. A per-episode `RitsuASMR-Offline-<episode>` scheduled task uses the current interactive Windows account (limited run level; no password or SYSTEM). It requires a logged-in account. Resume checks task and exact worker process state before accepting the existing episode. Status explicitly reports abandonment, heartbeat age, task state and worker PIDs. Stop requests the specific task to halt and verifies worker absence; if unconfirmed, it blocks rather than killing unrelated processes. Source and transcript digests remain pinned. The WAV is fetched only through existing Cauldron, into Android Downloads/RitsuASMR, with byte count, full SHA256 and PCM verification before publication. Failed transfers preserve partial files and currently require operator reconciliation before retry. Neither a scheduling receipt nor a delivered file is audible acceptance.

First run on Termux: update with LFS smudge disabled, run test_ritsu_asmr_offline.py, then ritsu_asmr_phone.py resume for the existing default canary. Use status, then fetch only after rendered_not_delivered. Tests and live Task Scheduler registration/stop, retrieval and listening require real runtime evidence. The full episode and Home Center audio archive are not yet delivered.

## Outbound Taildrop delivery
The physical canary rendered 3/3 segments, 14.14 seconds, 678764 bytes, SHA256 507f86d4b8123d017c95667da4148517868c3ad5b1ee5184f02fa256132ebd50. Drew confirmed the repaired SSH transfer worked but was unacceptably slow. He authorized Taildrop outbound. Rendering, inbound controls, and receipt query still use the existing Cauldron SSH command. Preferred delivery is now explicit `drop`; `verify` checks the actual Android file. `fetch` remains an explicit verified SSH fallback, never automatically substituted.

`drop` validates the original WAV on THECAULDRON, then requires the previously known Pixel hostname and tailnet IP to match one online peer before sending through the existing Tailscale CLI. No new network listener, credential or firewall changes. Windows persists an attempt record before send and a separate success record after send; a repeated drop returns its previous success rather than creating duplicates. An ambiguous attempt blocks and only explicit `drop --resend` retries (after checking the phone). Send success is not proof of phone receipt. Tailscale Android may require accepting/saving the transfer to Downloads; `verify --received PATH` can select the exact newly received copy. A verified pre-existing SSH copy does not prove Taildrop delivery, so select the actual incoming file for the first canary. The SSH receipt is the digest authority. Neither verification nor send is HEARD. Phone acceptance, live send latency, and full episode/archive remain open.
