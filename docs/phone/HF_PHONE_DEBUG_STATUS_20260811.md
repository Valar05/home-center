# HF Phone Debug Status - 2026-08-11

Status: phone-side HF/PocketTTS runtime debug completed; strict diagnostics source is merged but not yet deployed.

## Result

Hugging Face is not globally broken on the phone. The phone can import `huggingface_hub`, `torch`, `numpy`, `sentencepiece`, and `pocket_tts`, and it can generate PocketTTS audio locally in Termux.

The actual failure chain was:

1. `pocket_tts` import initially failed because `tqdm` was missing.
2. After installing `tqdm`, pip reported `huggingface_hub` dependency drift: missing `hf-xet` and `click` below the declared floor.
3. Installing `hf-xet` exposed an Android/Termux binary incompatibility: `hf_xet.abi3.so` failed to load with missing `PyExc_KeyError`.
4. Setting `HF_HUB_DISABLE_XET=1` avoided the broken Xet extension path and allowed `huggingface_hub` plus `pocket_tts` to import.
5. `pocket-tts --help` then failed through Typer/Rich because `markdown_it` was missing.
6. Installing `markdown-it-py` restored the PocketTTS CLI.
7. PocketTTS generated a WAV, but the raw output used bogus placeholder RIFF/data chunk sizes; repairing the header produced a valid WAV.

## Phone commands verified

- `huggingface_hub 1.27.0` imports with `HF_HUB_DISABLE_XET=1`.
- `pocket_tts 2.1.0` imports with `HF_HUB_DISABLE_XET=1`.
- `pocket-tts --help` works after installing `markdown-it-py`.
- `pocket-tts generate --help` works.
- `pocket-tts generate` produced `/data/data/com.termux/files/home/pockettts_canary_20260811.wav`.
- `fix-pockettts-wav-header` produced `/data/data/com.termux/files/home/pockettts_canary_20260811_fixed.wav`.

## Generated canary receipt

Raw PocketTTS output:

- Path: `/data/data/com.termux/files/home/pockettts_canary_20260811.wav`
- Bytes: `190124`
- SHA-256: `64099a2c69573d2be59d384c51a018ec2f8efec787cb51a6e2069eac8fa3b70f`
- Header issue: RIFF size `2000000036`, data size `2000000000`; Python `wave` read this as `1000000000` frames.

Fixed WAV:

- Path: `/data/data/com.termux/files/home/pockettts_canary_20260811_fixed.wav`
- Bytes: `190124`
- SHA-256: `02285f9ac44ca668c714efe08f081c893f1a46725aac3cc7a1d391cfe3a9dcf6`
- Format: mono, 24000 Hz, 16-bit PCM
- Frames: `95040`
- Duration: `3.96` seconds

## Durable phone-side repair

Persisted on `primary-phone`:

- Added `export HF_HUB_DISABLE_XET=1` to `/data/data/com.termux/files/home/.profile`.
- Added `export HF_HUB_DISABLE_XET=1` to `/data/data/com.termux/files/home/.bashrc`.
- Added `/data/data/com.termux/files/home/bin/pocket-tts-phone`, a wrapper that exports `HF_HUB_DISABLE_XET=1` and delegates to `pocket-tts`.
- Added `/data/data/com.termux/files/home/bin/fix-pockettts-wav-header`, a helper that rewrites truthful RIFF/data sizes for simple PocketTTS WAV output.

Fresh readback verified:

- Login shell reports `LOGIN_ENV_HF_HUB_DISABLE_XET=1`.
- `pocket-tts-phone` is on PATH.
- `fix-pockettts-wav-header` is on PATH.
- `pocket-tts-phone generate --help` succeeds.
- Corrected WAV readback reports mono, 24000 Hz, 95040 frames, 16-bit, 3.96 seconds.

## Strict diagnostics bridge state

PR #232 merged the strict read-only diagnostics source to `main` with focused local tests passing:

- `python3 tools/android_phone_diagnostics_test.py`: 10 tests passed.
- `node tools/phone_diagnostics_relay_test.mjs`: PASS.
- `node tools/phone_hands_relay_contract_test.mjs`: PASS.

However, the deployed Home Center bridge still reports source commit `222b3f08d824d10b4738219e84e8d914e2b74ead`, so the merged `phone_diagnostics_readonly` capability is not yet deployed/callable. GitHub Actions for the repo failed immediately with no useful logs in the inspected run set; direct phone shell debugging was used to finish the phone runtime task.

## Current ruling

For phone-first HF/PocketTTS work:

- Use `pocket-tts-phone`, not bare `pocket-tts`, unless the environment is known to include `HF_HUB_DISABLE_XET=1`.
- Treat Hugging Face Hub on Termux as usable through normal HTTP downloads with Xet disabled.
- Do not rely on the Android `hf-xet` wheel in this environment.
- After PocketTTS generation, run `fix-pockettts-wav-header` before using the WAV as an interoperable artifact.
- Playback and Drew's blinded perceptual acceptance remain separate from generation and file validity.
