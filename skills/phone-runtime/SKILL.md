# Phone Runtime Skill

## Purpose
Operate the primary Android phone through the authorized Home Center -> Phone Hands -> Termux lane without creating connector storms, duplicate runtimes, or false completion claims.

## Authorized execution lane
Use Home Center `command_center.phone_hands.*` against `primary-phone`. Prefer bounded `phone_shell` actions for Termux work. Do not substitute desktop, local scratch, Codex, or another device as deployment proof.

## Long-running job discipline
Compilation, package builds, model downloads, installs, renders, and other expensive phone-side jobs must be launched once and then left alone.

- Do not repeatedly poll `phone_hands.get` while a long command is leased.
- One initial receipt that the phone leased the command is enough to prove execution began.
- Do useful parallel work while the phone is busy: documentation, app seam inspection, config preparation, tests, handoff creation.
- Recheck only after a meaningful interval or when another independent signal indicates completion.
- If a connector begins rate-limiting or returning stale state, stop polling immediately. Preserve the commandId and resume later from that receipt.
- Never kill a healthy long build merely because ChatGPT cannot see incremental stdout.

## Android Python / Pocket TTS notes
Primary phone is ARM64 Termux. Prefer Termux-native binary packages for heavy foundations before pip source builds.

Known-good foundation from 2026-08-11:
- Python 3.13.13
- `python-torch` 2.11.0 from Termux
- `python-numpy` 2.4.4
- `python-scipy` 1.18.0
- Pocket TTS 2.1.0 package installed
- `safetensors` 0.8.0 successfully built locally as `cp310-abi3-android_30_arm64_v8a` and installed
- `sentencepiece` requires native source build on Android/Termux because PyPI has no compatible Android wheel
- available native toolchain: clang 21.1.8, cmake 4.3.4, rust 1.96.0, cargo 1.96.0

For Pocket TTS dependency installation, avoid asking pip to resolve Torch: install the Termux Torch package first and install Pocket TTS with `--no-deps`, then satisfy Python dependencies explicitly. This prevents pip from chasing incompatible Linux wheels.

## Venice mobile speech seam
Do not replace Drive narration wholesale. In the Android Home Center/Venice app, keep speech roles distinct:
- `speakOperational()` is device/operational TTS.
- `speakRenderedResponse()` is the rendered conversational speech seam.
- Existing AudioTrack, audio focus, MediaSession, mute state, stop controls, and sequence cancellation should remain authoritative.
- Pocket TTS should be inserted behind rendered conversational speech as a local persistent service/client, not bolted into every speech path.

## Completion standard
Package installation is not deployment proof. Pocket TTS work is complete only after all are observed through Home Center:
1. dependencies import successfully on primary-phone;
2. Pocket TTS model/tokenizer loads;
3. a real utterance synthesizes locally;
4. audio plays audibly through the phone;
5. Venice rendered-response speech calls the local Pocket TTS path;
6. mobile build containing the wiring is deployed;
7. end-to-end Venice -> Pocket TTS -> phone playback is verified with receipts.

Always distinguish installed, importable, model-loaded, wired, deployed, and end-to-end proven states.
