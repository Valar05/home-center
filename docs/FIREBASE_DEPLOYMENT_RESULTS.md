# Firebase Deployment Results

Date: 2026-06-20

## What Ran

- `sh tools/deploy_firebase.sh home-center-dclar`

## Result

- Firestore rules compiled successfully.
- Firestore indexes deployed successfully.
- Firebase deploy completed cleanly for project `home-center-dclar`.

## Notes

- The repo-supported deploy path is Firebase CLI, not `gcloud`.
- The helper script `bootstrap_dionysis_cloud.sh` was not used for the successful deploy.
