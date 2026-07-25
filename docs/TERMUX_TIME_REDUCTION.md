# Termux Time Reduction

Home Center should keep phone-local work on the phone and move repeatable coding chores to GitHub, devcontainers, and cloud image builds.

## Normal Lanes

- Use GitHub Actions `Home Center CI` for source checks and compact reports.
- Use `Deploy Home Center MCP` for manual MCP deploys after GitHub OIDC is configured.
- Use `Deploy Firestore` for rules/indexes without opening Termux.
- Use `Build Cloud Runtime Image` for cached Cloud Build image lanes.
- Use the devcontainer for cloud editing with Node, Java, Gradle, Firebase CLI, gcloud, and gh preinstalled.
- Use Termux for Android-only work: Shizuku, APK install, foreground app operation, and phone-local diagnostics.


## One Command Bootstrap

Run:

```sh
sh tools/home_center_cloud_bootstrap.sh run
```

The wrapper performs every safe local step: status checks, bootstrap token save when `gh` is logged in, GitHub App manifest generation, optional Secret Manager install from `GITHUB_APP_ID`, `GITHUB_APP_INSTALLATION_ID`, and `GITHUB_APP_PRIVATE_KEY`, doctor, and validation. It exits red with `blocked_external_github_app_secrets` when the remaining work is GitHub browser approval or missing secret values.

## Doctor

Run:

```sh
sh tools/home_center_doctor.sh
```

It writes a redacted report to `generated/doctor/home_center_doctor_latest.json` and a compact Markdown summary beside it. It reports GitHub/GCP auth, required Secret Manager entries, dirty state, and MCP endpoint reachability without printing tokens.

## GitHub Admin Setup

Use `tools/github_admin_gh_bootstrap.sh` for the GitHub App manifest and Secret Manager flow. The doctor distinguishes bootstrap-only GitHub access from full GitHub App authority.

## GitHub Actions OIDC Setup

The deploy workflows expect these GitHub secrets:

- `GCP_WORKLOAD_IDENTITY_PROVIDER`
- `GCP_DEPLOY_SERVICE_ACCOUNT`

Do not use a service-account JSON key. If OIDC is not configured, deploy workflows should fail before mutating production.
