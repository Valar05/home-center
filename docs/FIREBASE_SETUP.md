# Firebase Setup

Home Center uses Firebase Authentication with Google sign-in and Firestore for shared household task lists.

## Create The Firebase Project

1. Create or open a Firebase project.
2. Add an Android app with package name `com.dclar.homecenter`.
3. Download the Android config file and place it at `app/google-services.json`.
4. Do not commit `app/google-services.json`; this repo ignores it.

## Enable Auth

1. In Firebase Console, open Authentication.
2. Enable the Google sign-in provider.
3. Add the debug SHA-1 and SHA-256 fingerprints for this Android debug build.

To print signing fingerprints from this project:

```sh
gradle signingReport --no-daemon
```

Use the `debug` variant values for Firebase.

## Enable Firestore

1. Create a Firestore database.
2. Start in locked mode if offered.
3. Publish the rules from `firebase/firestore.rules`.

The first pilot version treats a household bucket code as the sharing boundary. Anyone signed in who knows the bucket code can join that bucket, and members can read/write its lists and tasks. Use a hard-to-guess bucket code for real testing.

## Rebuild

After placing `app/google-services.json`, rebuild and reinstall:

```sh
gradle assembleDebug --no-daemon
cp app/build/outputs/apk/debug/app-debug.apk /storage/emulated/0/Download/HomeCenter-debug.apk
am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file:///storage/emulated/0/Download/HomeCenter-debug.apk
```

Open the APK from Downloads to install the update.

## Current Project

The active Firebase project for this repo is:

```text
home-center-dclar
```

Completed from CLI on this phone:

- Firebase project created.
- Android app created for `com.dclar.homecenter`.
- Debug SHA-1 and SHA-256 registered.
- `app/google-services.json` downloaded locally. This file is ignored and must not be committed.
- Firestore API enabled.
- Default Firestore database created in `nam5`.
- Firestore rules and indexes deployed.

Still required for Google sign-in:

1. Open Firebase Console for `home-center-dclar`.
2. Go to Authentication.
3. Click Get started if prompted.
4. Enable the Google provider.
5. Re-download the Android config:

```sh
rm app/google-services.json
firebase apps:sdkconfig ANDROID 1:220218838446:android:3dde32bad6ce2fd51d8c3f --project home-center-dclar -o app/google-services.json
sh tools/build_debug_apk.sh
```

The rebuilt app should generate `default_web_client_id` after Google provider/OAuth setup is active.
