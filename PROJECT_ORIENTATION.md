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

## Secrets

Do not commit TickTick tokens, Firebase service account files, keystores, or `app/google-services.json`.

## Validation

```sh
sh tools/build_debug_apk.sh
sh tools/check_no_secrets.sh
```

## Deployment

Use `sh tools/build_debug_apk.sh` for the phone APK and `sh tools/deploy_firebase.sh <firebase-project-id>` for Firestore rules/indexes. See `docs/DEPLOYMENT.md`.
