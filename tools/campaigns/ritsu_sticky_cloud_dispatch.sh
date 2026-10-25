#!/usr/bin/env bash
# One-shot dispatch for the tested Ritsu Sticky Snippets cloud campaign.
# Can run in any working directory. GitHub Actions runs repo-owned scripts.
set -Eeuo pipefail
repo="Valar05/home-center"
branch="campaign/ritsu-local-tailnet-20261024"
pin="6d52c9be921db0d194af7bdf9a83934f11cbea37"
if ! command -v gh >/dev/null 2>&1; then
  echo "FAIL=github_cli_missing; install and authenticate GitHub CLI" >&2
  exit 2
fi
gh auth status --hostname github.com >/dev/null || {
  echo "FAIL=github_cli_not_authenticated" >&2; exit 2;
}
head="$(gh api "repos/$repo/git/ref/heads/$branch" --jq '.object.sha')"
[ "$head" = "$pin" ] || {
  echo "FAIL=campaign_ref_moved EXPECTED=$pin ACTUAL=$head" >&2
  exit 2
}
echo "RESOLVED_REPO=https://github.com/$repo"
echo "EXECUTION_DIR=GitHub_Actions"
echo "BRANCH=$branch"
echo "HEAD=$pin"
echo "CAMPAIGN=ritsu_sticky_v018"
echo "MODE=cloud_unit_tests_and_unsigned_release_compile"
# Repeated invocation should not dispatch another run for an already
# successful exact commit. No operator-owned destructive operations.
existing="$(gh run list --repo "$repo" --workflow build.yml \
  --branch "$branch" --commit "$pin" --event workflow_dispatch \
  --limit 20 --json databaseId,status,conclusion \
  --jq '[.[]|select(.status=="completed" and .conclusion=="success")][0].databaseId // empty')"
if [ -n "$existing" ]; then
  echo "ALREADY_VALIDATED_RUN=https://github.com/$repo/actions/runs/$existing"
  echo "INSTALLABLE_UPGRADE=BLOCKED_PENDING_SIGNING_COMPATIBILITY"
  exit 0
fi
gh workflow run build.yml --repo "$repo" --ref "$branch"
echo "DISPATCHED_REF=$pin"
echo "NOTE=GitHub tests and unsigned compilation only; NOT an installable update"
echo "INSTALLABLE_UPGRADE=BLOCKED_PENDING_SIGNING_COMPATIBILITY"
