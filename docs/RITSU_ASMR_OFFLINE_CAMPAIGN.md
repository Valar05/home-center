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
