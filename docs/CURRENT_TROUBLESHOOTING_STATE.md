# Current Troubleshooting State

Last updated: 2026-06-26 18:43 America/Chicago

## Situation

Home Center is being moved from a local/admin-style prototype toward a portable, user-focused Android app for a blind user. The user-facing app must not expose setup chores, local proxy instructions, fake Drive status, or raw debug/admin surfaces. Provider setup belongs to the owner/developer side; the app should only ask for Google sign-in and then work.

The active branch is `netrunner-scaffold` in `/storage/emulated/0/Documents/GodotProjects/home-center`.

Remote:

```text
origin https://github.com/Valar05/home-center.git
```


## Latest Implementation Update

Updated after the red-build review:

- Android now has a direct `GoogleDriveClient` that uses `GoogleAuthUtil` and Drive REST, not Firebase sign-in and not GPT.
- The app requests `https://www.googleapis.com/auth/drive.metadata.readonly` for the direct diagnostic.
- The Home Center menu has a `Check Google Drive` action. It lists the first 5 real Drive files or reports the exact token/scope/HTTP failure.
- Gemini runtime model now comes from `BuildConfig.GEMINI_MODEL`; Gradle default is `gemini-2.0-flash`, matching orientation.
- Cartesia proxy `/tts` now closes HTTP responses explicitly and prints full tracebacks on stream failure.
- Android speech logs explicit stop reasons: `new_speech_request`, `user_stop`, `cartesia_error`, `stale_sequence`, and `stream_complete`.
- `tools/test_cartesia_proxy.sh` writes `home-center-cartesia-test.pcm` under `${TMPDIR:-/tmp}` because this Termux environment cannot write `/tmp` directly.

Validation passed for source, APK build, provider/proxy config, and local proxy PCM output. Manual installed-app Drive validation still requires installing the rebuilt APK and tapping `Check Google Drive`.

## Current Git State

The working tree currently contains uncommitted troubleshooting fixes after commit `8a852ed Add installed Home Center user-path smoke`.

Important changed files:

- `app/build.gradle`
- `app/src/main/java/com/dclar/homecenter/MainActivity.java`
- `app/src/main/java/com/dclar/homecenter/ChatSystemShape.java`
- `app/src/main/java/com/dclar/homecenter/OpenAiAgentClient.java`
- `functions/index.js`
- `tools/home_center_regression_tests.py`
- `tools/home_center_user_path_red_test.py`
- `tools/home_center_provider_smoke.py`
- `tools/visual_evidence/home_center_user_path_20260626_184218.json`

One older visual evidence file was removed:

- `tools/visual_evidence/home_center_user_path_20260626_181721.json`

Before committing, run:

```sh
git status --short
git diff --stat
```

## What Was Corrected

### Google Drive Scope

The prior assumption that Firebase sign-in was Google automation was wrong. Firebase sign-in only proves identity; it does not prove Drive access.

The direct Android diagnostic uses Drive metadata readonly scope so the app can list real existing Drive files without granting write access:

```text
https://www.googleapis.com/auth/drive.metadata.readonly
```

The regression harness now fails if `https://www.googleapis.com/auth/drive.file` appears in the Android sign-in code, because app-created-file-only access is not enough for troubleshooting real Drive visibility.

### Drive Status Must Be Probed, Not Hallucinated

Drive capability questions should not go to GPT and produce guesses such as "Home Center can read Google Drive if connected." They should route to a real provider probe.

Current route:

1. Android detects Drive/Docs status questions in `MainActivity.tryHandleLocalStatusQuestion`.
2. Android gets the Firebase ID token for the signed-in user.
3. Android calls `OpenAiAgentClient.checkGoogleDrive`.
4. The Firebase Function `googleDriveProbe` loads stored Google OAuth tokens and calls the Google Drive API.
5. The app answers one of these states:
   - Drive not connected.
   - Drive connected with full Drive access.
   - Drive connected, but scope is insufficient.
   - Probe failed with technical details.

The provider probe includes shared drives:

```js
supportsAllDrives: true
includeItemsFromAllDrives: true
```

### Cartesia Must Be Hosted, Not User-Started

The user should not be told to start a Cartesia proxy. Hosted provider smoke now checks that the Firebase `tts` endpoint returns real audio bytes.

Android playback now logs received and written audio byte counts using:

```text
cartesia_playback_complete receivedBytes=... writtenBytes=...
```

This distinguishes provider-audio success from Android playback failure.

### Installed-App Smoke Must Catch Stale APKs

The installed app path was misleading because source tests passed while the phone still ran an older APK. `tools/home_center_user_path_red_test.py` now requires a runtime version marker for:

```text
versionName=0.2.7 versionCode=11
```

If the installed app is stale, the smoke fails fast with:

```text
installedBuildIsStale
runtimeVersionMatches
installedBuildFreshEnoughForBehaviorAssertions
```

This is intentional. Do not treat source/provider green as installed-app green.

## Current Validation Results

These passed after the current changes:

```sh
node --check functions/index.js
python3 tools/home_center_provider_smoke.py
sh tools/run_regression_tests.sh
gradle assembleDebug --no-daemon
apksigner verify --verbose app/build/outputs/apk/debug/app-debug.apk
aapt dump badging app/build/outputs/apk/debug/app-debug.apk | sed -n '1,8p'
```

Observed provider smoke output:

```text
Home Center provider smoke: OK cartesiaBytes=148176 driveProbeUnauth=401
```

Observed APK metadata:

```text
package: name='com.dclar.homecenter' versionCode='11' versionName='0.2.7'
```

## Current Red State

The installed-app user-path smoke is still red because the phone is running a stale installed build, not because the rebuilt APK failed.

Latest evidence:

```text
tools/visual_evidence/home_center_user_path_20260626_184218.json
```

Key assertions from that evidence:

```json
{
  "chatViewLoads": true,
  "composerVisible": true,
  "defaultAdminControlsHidden": true,
  "runtimeVersionMatches": false,
  "installedBuildFreshEnoughForBehaviorAssertions": false,
  "staleInstall": true
}
```

Failures:

```text
installedBuildIsStale
runtimeVersionMatches
installedBuildFreshEnoughForBehaviorAssertions
```

Because the installed APK is stale, do not use old visible text from that run to judge the current source behavior.

## APK Export State

The rebuilt APK was exported to Android Downloads:

```text
/storage/emulated/0/Download/HomeCenter-debug.apk
/storage/emulated/0/Download/HomeCenter-0.2.7-v11-20260626-184353.apk
```

Both were approximately 6.1 MB at the time of export.

Termux could not silently install the APK:

- `pm install -r /storage/emulated/0/Download/HomeCenter-debug.apk` failed because Android package manager could not read the shared-storage file context.
- Copying to `/data/local/tmp/HomeCenter-debug.apk` failed because Termux could not write that path.

Current practical install path:

1. Open Android Files / Downloads.
2. Tap `HomeCenter-debug.apk` or `HomeCenter-0.2.7-v11-20260626-184353.apk`.
3. Approve package installer update.
4. Open Home Center.
5. Sign in with Google again so the app requests the new full Drive scope.
6. Rerun `python3 tools/home_center_user_path_red_test.py`.

## Provider Deployment State

Firebase Functions were deployed successfully to project:

```text
home-center-dclar
```

Health endpoint returned:

```json
{"ok":true,"service":"home-center-gateway"}
```

Deployed functions include `googleDriveProbe`.

## Commands For The Next Agent

Start here:

```sh
cd /storage/emulated/0/Documents/GodotProjects/home-center
git status --short
git diff --stat
```

Validate source and provider:

```sh
node --check functions/index.js
python3 tools/home_center_provider_smoke.py
sh tools/run_regression_tests.sh
```

Build/export APK:

```sh
gradle assembleDebug --no-daemon
apksigner verify --verbose app/build/outputs/apk/debug/app-debug.apk
aapt dump badging app/build/outputs/apk/debug/app-debug.apk | sed -n '1,8p'
cp app/build/outputs/apk/debug/app-debug.apk /storage/emulated/0/Download/HomeCenter-debug.apk
am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file:///storage/emulated/0/Download/HomeCenter-debug.apk >/dev/null 2>&1 || true
```

After manual install, validate installed app path:

```sh
python3 tools/home_center_user_path_red_test.py
```

Only call the build green when the installed-app smoke passes on version `0.2.7` / `11`.

## Troubleshooting Rules

- Do not tell the end user to start local proxies, configure APIs, or visit setup docs inside the app.
- Do not claim Google Drive works unless `googleDriveProbe` confirms it for the signed-in Firebase user.
- Do not use `drive.file`; this build needs a real Drive metadata diagnostic against existing cloud files, not app-created-file-only access.
- Do not treat unit/source tests as enough. The installed Android app path must be smoke-tested.
- If the smoke sees stale text, first verify the installed runtime version before changing prompts.
- Do not add visible debug markers to the chat UI; use logs and evidence files instead.
- The default app experience must remain chat-first and accessible.
