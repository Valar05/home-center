# Home Center Orientation

For the live troubleshooting handoff, read `docs/CURRENT_TROUBLESHOOTING_STATE.md` before changing code. It records the current Drive/ElevenLabs/APK install state and the latest red/green evidence.

Home Center is a Java Android app built directly with Gradle from Termux. It is not a Godot project.


## Doctrine

Read [docs/HOME_CENTER_DOCTRINE.md](docs/HOME_CENTER_DOCTRINE.md#L1) before changing product direction, agent behavior, memory, research, writing, life-organization, provider-tool, Netrunner, or skill/simulation behavior. This repo-local doctrine is the source of truth; do not require Agent Closet, Drive, web search, or remote docs to recover Home Center's purpose.

Read [docs/ENGINEERING_TOOLING.md](docs/ENGINEERING_TOOLING.md#L1) before changing engineering-memory, repository-orientation, artifact-catalog, prompt-library, workflow, tool-registry, agent-registry, or state-graph behavior.

## Entry Points

- App id: `com.dclar.homecenter`
- Activity: `app/src/main/java/com/dclar/homecenter/MainActivity.java`
- Voice parser: `app/src/main/java/com/dclar/homecenter/CommandParser.java`
- Home Center sync client: `app/src/main/java/com/dclar/homecenter/HomeTaskClient.java`
- Legacy TickTick client: `app/src/main/java/com/dclar/homecenter/TickTickClient.java`

## Build

Use SDK 33 on this phone. Newer SDK resources have failed with the Termux ARM64 toolchain, so keep compatible dependency pins unless the local Android SDK/aapt2 setup changes.

For the chat UI and hosted ElevenLabs gateway, add the config to `local.properties`:

- `GEMINI_API_KEY=...`
- `GEMINI_MODEL=gemini-2.0-flash` or another model you want to target
- `AGENT_GATEWAY_BASE_URL=https://us-central1-home-center-dclar.cloudfunctions.net` or another hosted gateway base URL

```sh
sh tools/build_debug_apk.sh
```

This script builds, verifies, copies to Downloads, and installs through Shizuku. Use direct Gradle only for compile-only diagnostics.

## Pocket TTS Drive reader

Home Center read-aloud is Pocket TTS-only and Android-owned. Version 0.2.83 uses the native contract `pocket-tts-render-v4-native`: `NarrationForegroundService` owns the render plan, one serialized LiteRT Pocket TTS model, exact built-in voice `vera`, Venice close-mic PCM processing, atomic section publication, playback, audio focus, MediaSession, notification, wake lock, and process-death intent redelivery. Production rendering must work with Termux and every read-aloud tmux session stopped.

The pinned native runtime assets live under `app/src/main/assets/pockettts/` with exact hashes and provenance in `manifest.json`. The runtime source is `john-rocky/LiteRT-Models` commit `b669b3c04e09295e629f4cbe6111c8e94202b9d7`; converted graphs are pinned to `mlboydaisuke/Pocket-TTS-LiteRT` revision `66c9d2fb05fc44cc69cb14c15cff9574c4381788`; Vera is Kyutai's published preset. `docs/THIRD_PARTY_POCKET_TTS_NATIVE.md` carries attribution and licenses.

`MainActivity` remains a controller/observer and must not reclaim the Pocket TTS track or synthesize concurrently. Playback becomes available after the first contiguous validated sentence. Render sections are sentence-aligned; the model's 50-token split is only the internal safety bound for an exceptional long sentence.

Old v3 worker clips and manifests remain in place and readable when their artifact receipt is valid. New native requests use the separate `hc-v4-native-vera-close-mic-v1-` namespace and v4 receipts, so they cannot overwrite or impersonate old results.

The Termux operator is now a compatibility and diagnostic lane only:

```sh
sh tools/home_center_read_aloud.sh start local
sh tools/home_center_read_aloud.sh status
sh tools/home_center_read_aloud.sh doctor
sh tools/home_center_read_aloud.sh repair --file-id DRIVE_FILE_ID
sh tools/home_center_read_aloud.sh benchmark
sh tools/home_center_read_aloud.sh receipts
```

It must never be an automatic production fallback. Home Center narration never imports, calls, or falls back to Cauldron. Existing Render, Play, Pause, and Stop controls remain unchanged. Do not claim a whole book rendered until every section is accepted, and do not claim audible acceptance without Drew's real listen.

## Secrets

Do not commit TickTick tokens, Firebase service account files, keystores, or `app/google-services.json`.

## Validation

```sh
sh tools/build_debug_apk.sh
sh tools/check_no_secrets.sh
```

## Deployment

Use `sh tools/build_debug_apk.sh` for the phone APK and `sh tools/deploy_firebase.sh <firebase-project-id>` for Firestore rules/indexes. See `docs/DEPLOYMENT.md`.
