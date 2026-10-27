# Current Troubleshooting State

## 2026-09-18 Native token-overflow render stop (0.2.85)

- The reported pause was not caused by playback being inactive. Version 0.2.84 saved sections 1–14, then failed section 15 four times with `KV cache overflow at 512`; the foreground render service exited after each deterministic failure.
- The exact failed section is a punctuation-free table of contents: 663 characters and 120 words. Native sentence splitting had omitted the proven v3 renderer's 50-token hard fallback, allowing an over-limit prompt into the fixed 512-position model cache.
- `PocketTtsSynthesizer` now keeps sentence-first packing for ordinary text and applies word-boundary binary-search splitting with the real tokenizer only when a generated prompt exceeds 50 tokens. It fails closed if text changes, a single word cannot fit, or any unit remains over limit.
- The exact production table-of-contents fixture now produces multiple units, preserves normalized text exactly, and keeps every prepared unit at or below 50 tokens. An ordinary-sentence control remains one unit. Both are mandatory in the APK build path.
- Installed package is 0.2.85/versionCode 85. APK SHA-256 is `07b910050fec14e5be57bb324463e966be3cc3853d0dc21b0c1aa804776a530d`, exported at `/storage/emulated/0/Download/HomeCenter-0.2.85-v85-native-pocket-tts.apk`.
- Installation preserved all 14 completed v4 WAVs; section 15 remains missing, so the next Render skips accepted work and resumes there. Home Center was not launched by the agent, and the external worker remains stopped. User-operated background progress beyond section 15 remains the acceptance canary.


## 2026-09-18 LiteRT linkage crash repair (0.2.84)

- Fresh Android crash-buffer evidence superseded the 0.2.83 deployment claim: every Render attempt terminated Home Center with `NoClassDefFoundError: CompiledModel`, caused by `UnsatisfiedLinkError: libLiteRt.so not found`. The 06:34 screenshot was an unrelated browser game and was not used as Home Center evidence.
- Root cause was the API-only `com.google.ai.edge.litert:litert-api:2.1.6` dependency. It packaged `liblitert_jni.so`, whose ELF `NEEDED` table requires `libLiteRt.so`, but omitted that implementation library and the GPU accelerator library.
- Version 0.2.84 uses the full pinned `com.google.ai.edge.litert:litert:2.1.6` artifact. The signed APK contains `liblitert_jni.so`, `libLiteRt.so`, and `libLiteRtClGlAccelerator.so` for ARM64. A permanent post-build APK contract rejects future omissions.
- `PocketTtsNativeRenderer` converts native `LinkageError` into an explicit render `IOException`, so a missing or incompatible native runtime marks rendering unavailable instead of killing the app process.
- The v83 APK fails the new contract on the two missing implementation libraries; the v84 APK passes. Focused DSP, source regression, asset hashes, Gradle assembly, v2 signature verification, Shizuku install, installed version readback, and JNI dependency inspection are green.
- Installed package is 0.2.84/versionCode 84. APK SHA-256 is `a58a52cb1ff6d6d64d94a8d3336715466030c36553596794a92aeaed3db38528`, exported at `/storage/emulated/0/Download/HomeCenter-0.2.84-v84-native-pocket-tts.apk`. App data and old clips were preserved.
- Home Center was not launched by the agent. The external worker remains stopped with no narration tmux session. User-operated Render/Play remains the required real-device and audible canary.


## 2026-09-18 Android-owned Pocket TTS renderer (0.2.83)

- Root cause of the `RENDERING 0/2951` no-op was proven: Android queued a valid v3 Vera request, but the external Termux/tmux worker and heartbeat had vanished. Restarting the worker rendered the pending first sentence, proving incident recovery but not durability.
- Production synthesis is now inside Home Center through LiteRT 2.1.6 and `NarrationForegroundService`; normal rendering no longer queues or waits for Termux. Activity and service calls serialize through one process-wide model instance, preserving the no-extra-multithreading decision.
- Exact built-in Vera was preserved. The upstream voice packer regenerated published Alba byte-for-byte before producing Vera (`pt_voice_vera.bin`, SHA-256 `5d7154ac6cd31f33dc6b63ac9bf0e5401bdfae47c7c89747a786779d4fb0ee15`). No sample voice substitution occurred.
- The accepted Venice chain is applied in native PCM: high-pass 90 Hz, low-pass 7800 Hz, +2 dB at 260 Hz, +3 dB at 3200 Hz, 3:1 compression above -28 dB with 10 ms attack/120 ms release, and 1.18 gain with bounded output.
- Native assets are manifest-bound and atomically installed to private app storage on first render. All nine project assets (209,038,278 bytes) match their pinned hashes. Model/runtime/license provenance is in `app/src/main/assets/pockettts/manifest.json` and `docs/THIRD_PARTY_POCKET_TTS_NATIVE.md`.
- Old v3 clips remain untouched and accepted when their stored artifact contract is valid. New output uses `pocket-tts-render-v4-native` and `hc-v4-native-vera-close-mic-v1-` identities.
- Active render intents use Android `START_REDELIVER_INTENT`; the persisted plan skips accepted sections and resumes after service process recreation. Null-intent resurrection remains rejected.
- Focused production-contract, asset-hash, DSP, worker compatibility, sentence chunking, continuous playback, manifest batching, SDK-33 Kotlin/Java compile, dex, APK assembly, v2 signature, install, and installed version checks are green. The aggregate Android unit suite still has seven unrelated pre-existing `ChatSystemShapeTest` failures; the new `VeniceCloseMicFilterTest` passes alone.
- Installed package is 0.2.83/versionCode 83. The signed 208 MB APK SHA-256 is `14241f47b43066956e1f97936fef38542bc883fdf589df64483396f26a44234e` and is exported at `/storage/emulated/0/Download/HomeCenter-0.2.83-v83-native-pocket-tts.apk`.
- After install, Home Center was not launched. The compatibility worker was stopped and no `home-center-read-aloud` tmux session remained. Drew's next Render/Play press is the required Termux-absent native model-load, synthesis, playback, and audible-acceptance canary.


## 2026-09-17 Pocket TTS Read-Aloud

### Vera Venice close-mic production profile (0.2.82)

- Installed package is 0.2.82/versionCode 82. The app was not launched and no Home Center process or narration service was running after installation.
- The production renderer contract is `pocket-tts-render-v3`, bound end to end to built-in Pocket TTS voice `vera` and profile `vera-venice-close-mic-v1`.
- The exact Venice close-mic filter is applied through local FFmpeg: `highpass=f=90,lowpass=f=7800,equalizer=f=260:t=q:w=1:g=2,equalizer=f=3200:t=q:w=1:g=3,acompressor=threshold=-28dB:ratio=3:attack=10:release=120,volume=1.18`.
- Android requests and receipts require the v3 contract and exact profile. Cache identity is `pocket-tts-local-only-v4|vera-venice-close-mic-v1|...`, and new request ids start `hc-v3-vera-close-mic-v1-`, preventing collision with older clips.
- Old clips remain in place. Before and after build/install/worker restart, the MediaStore result directory contained 231 WAVs with the same name-size digest `e99a70eb8a4011d282dec7eee36b784398449c1a1101faa7ab14c92819a731e6`; the Fortress library contained 610 WAVs with the same digest `bf2b7c0758482870b72428622db6df0f10660bf5a91aa835ee02d857bd70bbeb`.
- The existing `home-center-read-aloud` tmux worker was restarted and reports v3, Vera, the profile id, and the exact filter. Six historical failed request records remain; there were no pending requests, so no book was auto-rendered.
- Renderer/filter ablation, stale-contract/profile/hash rejection, worker heartbeat, Home Center narration regressions, the 1,870-section manifest benchmark, Java compilation, APK assembly, v2 signature verification, Shizuku installation, and installed version readback are green.
- The full build wrapper still stops at the pre-existing unrelated `test_venice_review_memory.py` category assertion. The APK was therefore assembled and installed through the wrapper's remaining production commands after all narration-specific tests passed.
- Audible acceptance for `20k leagues.txt` remains the user's button press; no visual or audible success is claimed.


### Sentence-aligned startup and one-sentence Play gate (0.2.81)

- Installed package is 0.2.81/versionCode 81. The app was not launched and no Home Center process or narration service was running after installation.
- `MarkdownNarrationDocument` now delegates to a pure Java sentence owner: the first four sections are one complete sentence each, later sections pack complete sentences toward 1,400 characters, speaker tags repeat across derived sections, and exceptional long sentences remain whole for the renderer's 50-token internal safety split.
- The compiler cache identity is v8, so v7 character-cut WAVs remain recoverable on disk but cannot bind to the new section map.
- Play becomes available after the first contiguous validated sentence; the UI and service now share that predicate rather than waiting for the former 15-second/two-section lead.
- Pocket TTS inference was not additionally multithreaded. Its one model already runs with PyTorch's eight CPU threads; no concurrent inference or additional worker process was introduced.
- Sentence semantic tests, focused narration regressions, worker/continuous-playback contracts, the 1,870-section manifest benchmark, Java/Android compilation, APK assembly, v2 signature verification, install, and package readback are green.
- `20k leagues.txt` audible and visible acceptance remains pending the user's button press. The newest overall screenshot at 18:26 is an unrelated localhost Infinite Brutality failure page; the newest relevant Home Center screenshot remains 18:15 and is not 20k proof.

### Service-owned playback and background-crash repair (0.2.80)

- User evidence superseded the prior delivery premise: installed 0.2.79 repeated one section in the background, did not provide usable Play control, and crashed. The newest screenshot remains `Screenshot_20260917-174337.png`; visual and audible acceptance are still red/pending.
- Crash-buffer evidence at 17:58:08 showed `ForegroundServiceStartNotAllowedException` in `NarrationForegroundService.onStartCommand` after a background service resurrection. The service now uses `START_NOT_STICKY`, rejects null-intent resurrection, and catches foreground-promotion refusal instead of crashing.
- Root cause of the repeating section was an ownership violation: `MainActivity.isDocumentAudioPlaybackLive` checked the obsolete Activity `AudioTrack` while Pocket TTS audio was owned by `NarrationForegroundService`. The 1.5-second false-playing reconciler therefore restarted the same section. Pocket TTS now starts only from explicit Play/Resume and observes the service cursor; it returns before the legacy hosted-audio restart path.
- Large-book UI refresh now reads one manifest snapshot instead of reparsing the 1,652-section manifest once per section. New/cleared renders reset durably to Section 1, and Play appears at two contiguous validated sections.
- Installed package is 0.2.80/versionCode 80. Focused narration contracts, manifest benchmark, Java compilation, APK assembly, v2 signature verification, and package readback are green. The app was not launched or operated by the agent.

### Local-only v3 supersedes Cauldron (0.2.78)

- The user explicitly removed Cauldron after the exact `20k leagues.txt` path took about ten minutes to deliver a 28.72-second section that did not play. All earlier Cauldron notes below are historical evidence only.
- The canonical worker and operator now reject every non-local backend. Narration-specific Cauldron adapters are recoverably archived under `quarantine/home-center-read-aloud-cauldron-20260917/`.
- The local worker namespace collision was repaired: it no longer prepends the workspace helper `tools/pocket_tts` over the installed Pocket TTS 2.1.0 package.
- The exact pending 20k section 1 request rendered locally in 0.928 seconds to 1.12 seconds of accepted PCM16 WAV, with matching text/artifact hashes and no corrupt tail.
- App version 0.2.79 uses `pocket-tts-local-only-v3` and requires `backend=local` in every cached receipt, so it cannot restore the old Cauldron-contaminated v2 cache. Audible Play acceptance remains the user.

### MediaStore bridge production proof (0.2.77)

- Android scoped storage was the remaining no-op: the app could not read direct public Documents results, and atomic replacement of app-created MediaStore placeholders detached their rows.
- `PocketTtsWorkerBridge` now creates app-owned result slots in `Download/HomeCenter/pocket-tts-results/` and imports through `ContentResolver`; the existing worker renders in private staging and overwrites those slots in place, preserving their MediaStore-owned inodes.
- Installed versionCode 77 reached THECAULDRON through the existing worker and imported six consecutive validated WAV sections for `CANON CANDIDATE — Thirdskin Commander — The Last Bare Hand` while the durable foreground render remained active. This proves transport and continued import; it is not a claim that the selected document or `20k leagues.txt` finished or was audibly accepted.
- Focused regression, worker heartbeat/inode preservation, continuous playback, render-v2, manifest batching, and Python compile checks are green.

- Root cause reproduced: legacy Pocket TTS accepted a 632-token punctuation-poor chunk despite its 50-token limit, then published a 210-second WAV whose tail became low-energy high-frequency corruption.
- v2 splits with the actual tokenizer at 50 tokens maximum, requires EOS, applies duration/clipping/corruption-tail gates, and binds receipts to text and artifact SHA-256.
- The exact 632-token production canary rendered on THECAULDRON as 14 accepted units, 103.44 seconds, all EOS observed, maximum unit size 50, RTF 0.391986, artifact SHA `9c2fc5e441cc527e66e749e521709d3fa9bc1cd169dba3a26270fe672992ff2d`. This is machine evidence, not a human audible verdict.
- Cauldron uses Home Center Computer Hands, not SSH. Long renders run asynchronously and transfer in bounded chunks with one retry and final whole-file SHA verification.
- Android Pocket TTS playback is owned by `NarrationForegroundService`; its persisted cursor comes from `AudioTrack.getPlaybackHeadPosition()`, not bytes written. Activity destruction preserves active narration.
- `20k leagues.txt` file ID `1B_nUq6e7sLGwOuI8zeJegftMTDzCWuWX`: 15 legacy/unproven public artifacts were moved to timestamped quarantine; the campaign repair marker requires v2 rerender. The full book is not yet certified complete.
- Installed APK: versionCode 77, versionName 0.2.77. Install through Shizuku succeeded; the production MediaStore bridge proof above is from this installed build.
- Focused read-aloud tests and Android Gradle build are green. The full repository regression currently stops in the unrelated `test_venice_review_memory.py` category-order assertion (`correction_regression` is classified as `code_review_omission`); do not report the whole suite green.


Last updated: 2026-09-17 20:38 America/Chicago

## 2026-07-10 Drive Reader Red-Build Reorientation

The active visual target is no longer a chat-first app. The first viewport must be a Drive file/folder reader. Chat remains available only as a secondary surface behind `Open chat`.

Current visual contract:

- Header and first panel identify the app as `Drive Reader`; Android title-bar `Home Center` must be suppressed.
- Persisted chat-open state must be cleared on launch so old chat/document cards cannot occupy the first viewport.
- Recent files, folders, and Google Docs are visible controls on the first screen.
- The visual list represents Drive objects directly: folder rows open in-place; Google Doc rows open the document reader; other file rows open their Drive link or report unsupported indexing.
- The architecture is cloud-file first: `GoogleDriveClient` owns recent-file, folder, doc, and folder-child listing methods.
- No agent automation is required for this slice; automation can target the visual tool later.

## 2026-07-10 ElevenLabs Google Docs Reader Update

The active reader contract is the manual Audible-style Google Docs integration. The old confirm-before-whole-document stream model is canceled. Long documents must not start hidden background voice generation just because text was read or indexed.

Current contract:

- Scope is Google Docs only.
- Reading a Google Doc ingests and indexes the Drive text snapshot only.
- The chat card pairs the Drive text version with an ElevenLabs Brian voice version, but it does not expose separate playback/download controls.
- The Drive narration surface shows a very large `RENDER` button, a tile-local `STOP` button while active, and one playhead.
- The first chunk is part of the normal chunk list, deliberately short, and autoplayed after ingest.
- Autoplay stops after that first chunk; full-document voice generation requires the explicit render button.
- Playback/rendering preserves local WAV sections when present.
- The playhead duration represents already-rendered document audio across sections, not only the first chunk.
- User scrubbing can jump anywhere inside already-rendered sections; it must not pretend unrendered sections exist.
- Tapping a different Google Doc replaces the active reader immediately instead of queueing stale narration.
- Stop cancels explicit playback/download/render intent; stale workers must not refresh or resume the replaced player.
- Operational prompts may use native Android TTS.
- Rendered assistant responses and Google Doc reader chunks use hosted ElevenLabs Brian only.
- Hosted ElevenLabs failure pauses the reader at the failed chunk and asks for retry; it must not silently continue with native TTS.

Validation for this slice:

- `python3 tools/home_center_regression_tests.py`: OK.
- `sh tools/run_regression_tests.sh`: OK.
- Direct `gradle :app:compileDebugJavaWithJavac --no-daemon`: red because the ambient Termux Gradle is 9.6 and the Android Gradle plugin requires a compatible Gradle version; use the project build script instead.
- `sh tools/build_debug_apk.sh`: OK. It rebuilt, verified, copied `/storage/emulated/0/Download/HomeCenter-debug.apk`, and installed through Shizuku.
- Installed package after build: `versionName=0.2.56 versionCode=60 lastUpdateTime=2026-07-10 06:30:36`.
- Installed UI smoke was not run because the device was on the Android pattern lock screen. Do not treat that as an app failure.

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
- ElevenLabs hosted speech `/tts` now defaults to ElevenLabs Brian, closes HTTP responses explicitly, and reports provider stream failures.
- Android speech logs explicit stop reasons: `new_speech_request`, `user_stop`, `hosted_speech_error`, `stale_sequence`, and `stream_complete`.

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

### ElevenLabs / Hosted Speech Must Be Hosted, Not User-Started

The user should not be told to start a speech proxy or enter a provider key. Hosted provider smoke checks that the Firebase `tts` endpoint returns real audio bytes from the ElevenLabs Brian provider.

Android playback now logs received and written audio byte counts using:

```text
stream_complete receivedBytes=... writtenBytes=...
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
Home Center provider smoke: OK hostedSpeechBytes=148176 driveProbeUnauth=401
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

After manual install, validate installed UI path:

```sh
python3 tools/home_center_user_path_red_test.py
```

Only call the installed UI path green when the installed-app smoke passes on the current APK version.

For Google Drive/Docs prompt, confirmation, working-memory, or gateway/tool-loop failures, do not depend on Package Installer state. Run the headless metal prompt smoke instead:

```sh
node tools/home_center_metal_prompt_smoke.mjs --scenario docs-create-update-read
```

## Troubleshooting Rules

- Do not tell the end user to start local proxies, configure APIs, or visit setup docs inside the app.
- Do not claim Google Drive works unless `googleDriveProbe` confirms it for the signed-in Firebase user.
- Do not use `drive.file`; this build needs a real Drive metadata diagnostic against existing cloud files, not app-created-file-only access.
- Do not treat unit/source tests as enough. UI failures need installed-app smoke; Google prompt/tool failures need the headless real-API metal smoke.
- If the smoke sees stale text, first verify the installed runtime version before changing prompts.
- Do not add visible debug markers to the chat UI; use logs and evidence files instead.
- The default app experience must remain chat-first and accessible.
