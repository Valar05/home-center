# GitHub Admin MCP

Home Center can expose a higher-trust GitHub administration lane directly through `homeCenterMcp`. This is separate from Command Center and separate from the existing safe GitHub read/issue/comment tools.

## Authority

Use a private GitHub App as the primary credential. Install it on the allowed owner, initially `Valar05`, and grant only the permissions needed by the enabled operations:

- Metadata: read
- Contents: read/write for branch refs, file commits, and PR merge
- Pull requests: read/write for PR creation and PR metadata
- Issues: read/write for the existing issue/comment lane
- Actions: read/write only when workflow dispatch is enabled
- Workflows: write only when editing `.github/workflows/*` through file upsert
- Administration: write only for repository creation/configuration

Personal-account repository creation cannot rely on a repository-scoped installation token. Configure `GITHUB_BOOTSTRAP_TOKEN` only if Home Center must create repos under a personal account. Keep that token separate from the GitHub App authority.

## Secrets And Flags

Bind these Firebase/Cloud Function secrets for `homeCenterMcp`:

- `GITHUB_APP_ID`
- `GITHUB_APP_INSTALLATION_ID`
- `GITHUB_APP_PRIVATE_KEY`
- `GITHUB_BOOTSTRAP_TOKEN` optional fallback for personal repo creation

Runtime environment:

- `HOME_CENTER_GITHUB_ADMIN_ENABLED=true` enables mutations.
- `HOME_CENTER_GITHUB_ADMIN_OWNERS=Valar05` controls the owner allowlist.

Use `tools/setup_github_admin_secrets.sh home-center-dclar` after exporting the GitHub App values in the shell. The helper writes Secret Manager versions without printing secret values.

Without the feature flag, `github_admin.auth_status` remains inspectable but every mutation fails closed.

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

Every mutation requires `requestId` and writes a `driveBridgeAudit` record. PR merge additionally requires `expectedHeadSha` and rejects draft PRs, head-SHA mismatch, and non-green commit status unless the caller explicitly sets `requireGreenChecks=false`.

## Boundaries

No delete, archive, transfer, secret-management, or token-management operation is exposed in this lane. Existing safe GitHub tools still use `GITHUB_TOKEN` for compatibility and should not be treated as admin authority.
