# GitHub Admin MCP

Home Center exposes a higher-trust GitHub administration lane directly through `homeCenterMcp`. It is separate from Command Center and the safe GitHub read/issue/comment tools.

## Per-user authority

GitHub Admin is personal to the authenticated Home Center user. The approved Home Center identities are:

- Drew: `dclarke1005@gmail.com`
- June: `junewren28@gmail.com`
- Tim: `timothypomeroy07@gmail.com`

Each user profile binds that Home Center email to that user's own GitHub App installation ID and allowed GitHub owner/login. Owner checks, installation-token minting, repository access, audit identity, and idempotency replay all use this binding. A missing profile fails closed with `github_admin_user_profile_missing`; Home Center never lends Drew's installation or bootstrap token to June or Tim.

Drew retains the deployed legacy binding through `GITHUB_APP_INSTALLATION_ID`, `HOME_CENTER_GITHUB_ADMIN_OWNERS`, and the optional personal-repository bootstrap token. This compatibility path applies only to `dclarke1005@gmail.com`, so adding June and Tim does not disrupt Drew's access.

Use one private GitHub App as the credential issuer. Each person installs that app on their own GitHub account or organization and selects the repositories Home Center may administer. Grant only the permissions needed by the enabled operations:

- Metadata: read
- Contents: read/write for branch refs, file commits, and PR merge
- Pull requests: read/write for PR creation and PR metadata
- Issues: read/write for the existing issue/comment lane
- Actions: read/write only when workflow dispatch is enabled
- Workflows: write only when editing `.github/workflows/*` through file upsert
- Administration: write only for organization repository creation/configuration

GitHub App installation tokens cannot create a repository under a personal account. Drew's existing optional `GITHUB_BOOTSTRAP_TOKEN` remains Drew-only. A June or Tim request with `ownerType: user` fails closed with `github_admin_user_token_missing`; do not solve that boundary by sharing Drew's token. Repositories can instead be created manually once, created under an organization installation, or supported later with a separately authorized per-user credential design.

## Secrets and configuration

Bind these Firebase/Cloud Function secrets for `homeCenterMcp`:

- `GITHUB_APP_ID`
- `GITHUB_APP_INSTALLATION_ID` (Drew compatibility binding)
- `GITHUB_APP_PRIVATE_KEY`
- `GITHUB_BOOTSTRAP_TOKEN` (optional, Drew-only personal repository creation)

Runtime environment:

- `HOME_CENTER_GITHUB_ADMIN_ENABLED=true` enables mutations.
- `HOME_CENTER_GITHUB_ADMIN_OWNERS=Valar05` preserves Drew's owner allowlist.
- `HOME_CENTER_GITHUB_ADMIN_USER_PROFILES_B64` contains Base64-encoded JSON profiles for additional users.

Do not put tokens or private keys in the profile JSON. It contains only email-to-installation routing metadata. For example:

```json
{
  "junewren28@gmail.com": {
    "owners": ["JUNES_GITHUB_LOGIN"],
    "installationId": "JUNES_NUMERIC_INSTALLATION_ID"
  },
  "timothypomeroy07@gmail.com": {
    "owners": ["TIMS_GITHUB_LOGIN"],
    "installationId": "TIMS_NUMERIC_INSTALLATION_ID"
  }
}
```

Encode the reviewed JSON without printing any credential:

```sh
HOME_CENTER_GITHUB_ADMIN_USER_PROFILES_B64="$(printf '%s' "$PROFILE_JSON" | base64 | tr -d '\n')"
export HOME_CENTER_GITHUB_ADMIN_USER_PROFILES_B64
```

Use `tools/setup_github_admin_secrets.sh home-center-dclar` after exporting the GitHub App secret values. The helper writes Secret Manager versions without printing them. The profile environment value is supplied by `tools/deploy_functions_termux.sh` and must be reviewed before the main-only deployment.

Without the feature flag, `github_admin.auth_status` remains inspectable but every mutation fails closed. Its v2 response reports the authenticated actor, credential scope, bound-installation state, allowed owners, provider probe, and disabled reasons without exposing credentials.

## Operations

Preferred durable invocation is `drive_operation` with these registry names:

- `github_admin.auth_status`
- `github_admin.repos.create`
- `github_admin.repos.configure`
- `github_admin.branches.create`
- `github_admin.files.upsert`
- `github_admin.pull_requests.create`
- `github_admin.pull_requests.merge`
- `github_admin.workflows.dispatch`

Top-level aliases are also exposed when the connector schema is fresh: `github_admin_auth_status`, `github_admin_create_repo`, `github_admin_configure_repo`, `github_admin_create_branch`, `github_admin_upsert_file`, `github_admin_create_pull_request`, `github_admin_merge_pull_request`, and `github_admin_dispatch_workflow`.

Every mutation requires `requestId` and writes a `driveBridgeAudit` record owned by the authenticated Home Center actor. Reusing another user's request ID fails with `github_admin_request_id_owner_conflict`; it cannot replay their result. PR merge additionally requires `expectedHeadSha` and rejects draft PRs, head-SHA mismatch, and non-green commit status unless the caller explicitly sets `requireGreenChecks=false`.

## Boundaries

No delete, archive, transfer, secret-management, or token-management operation is exposed. Existing safe GitHub tools still use `GITHUB_TOKEN` for compatibility and must not be treated as personal GitHub Admin authority.
