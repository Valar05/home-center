# Deployment

Home Center has two deployment targets:

1. Build and copy the debug APK to Android Downloads.
2. Deploy Firestore rules and indexes to Firebase.

The Firebase deploy path uses the Firebase CLI, not `gcloud`.

## Install Firebase CLI

Firebase's documented npm install path is:

```sh
npm install -g firebase-tools
```

Then authenticate from Termux with the no-localhost flow:

```sh
firebase login --no-localhost
firebase projects:list
```

If global npm install fails on this phone, the fallback is to run Firebase setup from a desktop/laptop, commit only the non-secret project files, and copy `app/google-services.json` onto the phone manually. Do not commit `app/google-services.json`.

## Firebase Project Files

Committed:

- `firebase.json`
- `firebase/firestore.rules`
- `firebase/firestore.indexes.json`
- `.firebaserc.example`

Ignored/local:

- `.firebaserc`
- `app/google-services.json`
- service accounts
- keystores
- API tokens

To create a local `.firebaserc` after you know the project id:

```sh
cp .firebaserc.example .firebaserc
# edit your-firebase-project-id
```

The deploy scripts can also use an explicit project id and do not require `.firebaserc`.

## Commands

Build, verify, copy, and refresh the APK in Downloads:

```sh
sh tools/build_debug_apk.sh
```

Deploy Firestore rules and indexes:

```sh
sh tools/deploy_firebase.sh <firebase-project-id>
```

Build APK and deploy Firestore in one pass:

```sh
sh tools/deploy_all.sh <firebase-project-id>
```

Or use an environment variable:

```sh
FIREBASE_PROJECT=<firebase-project-id> sh tools/deploy_all.sh
```

## Git Hooks

Install repo-local hooks with:

```sh
sh tools/install_git_hooks.sh
```

Configured hooks:

- `pre-commit`: runs `sh tools/check_no_secrets.sh`
- `pre-push`: runs `sh tools/build_debug_apk.sh`
- Optional Firestore deploy on push: set `HOME_CENTER_FIREBASE_DEPLOY_ON_PUSH=1` and `FIREBASE_PROJECT=<firebase-project-id>`

Android shared storage often strips executable permission, so hooks may fail with permission errors. The explicit `sh tools/...` commands are the reliable path on this phone.
