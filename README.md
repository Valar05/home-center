# Home Center

Home Center is a native Android pilot app for family voice commands. The current slice keeps Google Assistant as the outer launcher: say `Hey Google, open Home Center`, tap the large Talk button, then use Home Center commands.

Primary target for this slice:

- `add eggs to shopping list` adds `eggs` to the shared Home Center `shopping` list.
- `read shopping list` loads active items and reads the first one.
- `next`, `previous`, and `done` advance through the active readback list or mark the current Home Center task complete.
- TickTick remains as a masked legacy fallback when Firebase sync is not configured or not signed in.


## Doctrine

Home Center's repo-local product doctrine lives in `docs/HOME_CENTER_DOCTRINE.md`. Read it before changing agent behavior, memory, research, writing, life-organization, Netrunner, provider tools, or skill/simulation features. The app should not depend on a web request or external doctrine store to know its own purpose.

## Build

```sh
cd /storage/emulated/0/Documents/GodotProjects/home-center
gradle assembleDebug --no-daemon
```

The debug APK is written to:

```text
app/build/outputs/apk/debug/app-debug.apk
```

A user-installable copy is published to:

```text
/storage/emulated/0/Download/HomeCenter-debug.apk
```

This Termux build compiles with SDK 33 because the local ARM64 `aapt2` works with that platform. Firebase dependencies are pinned in `app/build.gradle` to versions that still build against SDK 33.

## Firebase Setup

Firebase is optional at build time. Without `app/google-services.json`, the APK still builds and opens, but Home Center sync reports that Firebase config is missing and falls back to TickTick for supported commands.

Setup steps are in `docs/FIREBASE_SETUP.md`. Do not commit `app/google-services.json`, service accounts, private keys, or TickTick tokens.

## Install On This Phone

Open `HomeCenter-debug.apk` from Downloads and approve the Android package installer prompt. Direct `pm install` from Termux is blocked on this device by Android package-manager permissions/file context.

## Voice Commands

Supported now:

```text
add eggs to shopping list
create list pantry
create personal list meds
create household list chores
create group list soccer for kids
prefer eggs as 18 count
map eggs to walmart sku 12345
read shopping preferences
build walmart cart for shopping
remove eggs from shopping list
delete eggs from shopping list
take eggs off shopping list
cross eggs off shopping list
mark eggs done on shopping list
read shopping list
what is on shopping list
next
previous
done
turn on hotspot
turn off hotspot
```

Hotspot commands are parsed but not implemented yet. Home Center speech requests transient Android audio focus so music apps should pause or duck while responses are spoken.

Cartesia realtime speech runs through a local Termux proxy. For that path:

```sh
source ~/.bashrc
pip install 'cartesia[websockets]'
sh tools/run_cartesia_proxy.sh
```

Set `CARTESIA_PROXY_BASE_URL=http://localhost:8787` in `local.properties` if you want a nondefault endpoint. The app now requires the Cartesia proxy for speech output.

## Data Model

Home Center stores synced tasks in Firestore under a household bucket. See `docs/DATA_MODEL.md`.

Task fields are:

- `name`
- `description`
- `json`
- `jsonText`
- `dueAt`
- `status` (`active` or `done`)
- audit fields such as `createdAt`, `createdBy`, `completedAt`, and `completedBy`

## Deployment

See `docs/DEPLOYMENT.md` for APK build/copy, Firebase rules deploy, and Git hook setup.

## Smoke Checks

```sh
sh tools/run_regression_tests.sh
gradle assembleDebug --no-daemon
apksigner verify --verbose app/build/outputs/apk/debug/app-debug.apk
aapt dump badging app/build/outputs/apk/debug/app-debug.apk | sed -n '1,20p'
sh tools/check_no_secrets.sh
```

`tools/run_regression_tests.sh` is dependency-free. It runs the secret scanner, source-contract checks for the Firestore membership/write flow, the agent failure matrix from `docs/AGENT_CONTRACT.md`, and a Java command-parser harness for common voice commands.

## List Visibility

Lists can be created as:

- `personal`: visible only to the Google account that owns the list.
- `household`: visible to members of the selected household bucket.
- `group`: visible to members of a Home Center family group inside the household bucket. Group sharing uses a Home Center group name/code, not Google Family Link membership.

Examples:

```text
create personal list meds
create household list chores
create group list soccer for kids
add cleats to soccer list
```

## Local Logs

Home Center writes local-only diagnostic logs by date. Logs are not sent to Firestore or any cloud service. On Android 10+ they are written through the Downloads provider so Termux and Google Files can read them:

```text
/storage/emulated/0/Download/HomeCenter/logs/YYYY-MM-DD.txt
```

The app also shows the active log path in the status area. Useful entries include app startup, spoken command parsing, bucket/list/user context, Firebase successes, automatic bucket membership repair, and Firebase errors such as `PERMISSION_DENIED`.
