# Home Center Orientation

Home Center is a Java Android app built directly with Gradle from Termux. It is not a Godot project.

## Entry Points

- App id: `com.dclar.homecenter`
- Activity: `app/src/main/java/com/dclar/homecenter/MainActivity.java`
- Voice parser: `app/src/main/java/com/dclar/homecenter/CommandParser.java`
- Home Center sync client: `app/src/main/java/com/dclar/homecenter/HomeTaskClient.java`
- Legacy TickTick client: `app/src/main/java/com/dclar/homecenter/TickTickClient.java`

## Build

Use SDK 33 on this phone. Newer SDK resources have failed with the Termux ARM64 toolchain, so keep compatible dependency pins unless the local Android SDK/aapt2 setup changes.

For the slice-one chat UI and Cartesia proxy, add the config to `local.properties`:

- `GEMINI_API_KEY=...`
- `GEMINI_MODEL=gemini-2.0-flash` or another model you want to target
- `CARTESIA_PROXY_BASE_URL=http://localhost:8787` if you want a nondefault proxy endpoint

```sh
gradle assembleDebug --no-daemon
```

## Secrets

Do not commit TickTick tokens, Firebase service account files, keystores, or `app/google-services.json`.

## Validation

```sh
gradle assembleDebug --no-daemon
apksigner verify --verbose app/build/outputs/apk/debug/app-debug.apk
aapt dump badging app/build/outputs/apk/debug/app-debug.apk | sed -n '1,20p'
sh tools/check_no_secrets.sh
```

## Deployment

Use `sh tools/build_debug_apk.sh` for the phone APK and `sh tools/deploy_firebase.sh <firebase-project-id>` for Firestore rules/indexes. See `docs/DEPLOYMENT.md`.
