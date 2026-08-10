# Android Autonomous Voice Node

Status: implemented in repository; deployment requires live phone acceptance.

## Mission

Make the Android phone a self-contained Home Center node. The desktop is optional.

Local path:

`microphone -> ears -> Vlad the Impalementer (VAD) -> local LLM executive -> Phone Hands -> Android -> TTS`

Remote path remains:

`Home Center/authorized peer -> Tailscale -> Phone Hands -> Android`

The local executive imports the same Phone Hands observation/action implementation directly. It does **not** enable raw shell and does not weaken the remote tailnet-only ingress policy.

## Components

- `tools/android_phone_hands_bridge.py` — Android body through Shizuku/rish.
- `tools/android_phone_local_executive.py` — bounded local planner, maximum six actions by default.
- `tools/android_phone_voice_assistant.py` — wake/listen/execute/speak loop.
- `tools/setup_android_phone_autonomous_node.sh` — one-shot Termux bootstrap.

## Local model

Default: `Qwen/Qwen2.5-0.5B-Instruct-GGUF`, Q4_K_M, served only on `127.0.0.1:8790` by `llama-server`.

The model is intentionally tiny. It is an executive/reflex brain, not the canonical large Venice personality. It receives current UI evidence and may emit only the Phone Hands allowlisted actions.

## Voice

Wake word defaults to `venice` and is configurable with `HC_PHONE_WAKE_WORD`.

Bootstrap ears use `termux-speech-to-text`; speech output uses `termux-tts-speak`. These require the Termux:API companion app plus microphone permission.

Offline adapters can replace both without changing the executive contract:

- `HC_PHONE_STT_CMD`: command template containing `{wav}` and printing transcript.
- `HC_PHONE_VLAD_CMD`: Vlad the Impalementer VAD command containing `{wav}`; exit 0 means speech.
- `HC_PHONE_TTS_CMD`: TTS command template containing `{text}`.

Sherpa-ONNX is the preferred later offline speech organ because it supports Android arm64, ASR, TTS, VAD, keyword spotting, and speaker verification.

## Install on phone

From the clean phone-hands worktree:

```sh
git fetch origin
git checkout feature/android-phone-autonomous-voice-node
chmod +x tools/setup_android_phone_autonomous_node.sh
bash tools/setup_android_phone_autonomous_node.sh
```

The installer:

1. installs `python`, `curl`, `jq`, `termux-api`, and `llama-cpp`;
2. downloads the official Qwen 0.5B Q4_K_M GGUF into Home Center's local model directory;
3. verifies Shizuku/rish;
4. creates `home-center-phone-brain`, `home-center-phone-ask`, and `home-center-phone-voice` launchers;
5. starts `llama-server` on loopback only;
6. asks the local executive to observe the foreground app without taking action.

## Use

Text/reflex test:

```sh
home-center-phone-ask 'Go home, then tell me what you see.'
```

Voice assistant:

```sh
home-center-phone-voice
```

Example spoken request:

`Venice, go home and open Spotify.`

## Safety boundary

The local model may use only:

- tap
- swipe
- text
- keyevent
- home
- back
- recents
- launch
- force_stop

Raw Android shell is not in its action vocabulary. The prompt additionally prohibits autonomous purchases, account-security changes, destructive deletion, permission escalation, messaging other people, and privacy-sensitive capture without explicit user instruction.

## Acceptance criteria

Do not report the autonomous node as deployed until all are observed on the physical phone:

1. `curl http://127.0.0.1:8790/health` succeeds with desktop powered off/unavailable.
2. `home-center-phone-ask 'Observe only and name the foreground app'` returns a correct answer from fresh Phone Hands evidence.
3. Local executive performs `home`, observes the changed foreground state, and stops.
4. `home-center-phone-voice` hears a wake-word command and speaks a response.
5. Voice command causes one harmless UI mutation and fresh readback confirms it.
6. Raw shell remains disabled for the local executive.
7. Existing remote Phone Hands remains tailnet-only and bearer-authenticated.

Only after those seven checks is the phone a deployed autonomous voice node.
