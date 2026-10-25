#!/usr/bin/env bash
# One-shot dispatch for the tested Ritsu Sticky Snippets cloud campaign.
# Can run in any working directory. GitHub Actions runs repo-owned scripts.
set -Eeuo pipefail
repo="Valar05/home-center"
branch="campaign/ritsu-local-tailnet-20261024"
expected_script_blob="ca0573017cae4c968f6e704429f4c04f830e6a29"
expected_android_blob="3a72ab9c02a9adda4ec665d406a37fb6beb290fd"
expected_workflow_blob="f55a331092e677c2b5ae3341e0b974f205542ae7"
if ! command -v gh >/dev/null 2>&1; then
  echo "FAIL=github_cli_missing; install and authenticate GitHub CLI" >&2
  exit 2
fi
gh auth status --hostname github.com >/dev/null || {
  echo "FAIL=github_cli_not_authenticated" >&2; exit 2;
}
head="$(gh api "repos/$repo/git/ref/heads/$branch" --jq '.object.sha')"
campaign_blob="$(gh api "repos/$repo/contents/tools/campaigns/ritsu_sticky_campaign.sh?ref=$branch" --jq '.sha')"
android_blob="$(gh api "repos/$repo/contents/android/ritsu-control/app/build.gradle?ref=$branch" --jq '.sha')"
workflow_blob="$(gh api "repos/$repo/contents/.github/workflows/build.yml?ref=$branch" --jq '.sha')"
[ "$campaign_blob" = "$expected_script_blob" ] &&
[ "$android_blob" = "$expected_android_blob" ] &&
[ "$workflow_blob" = "$expected_workflow_blob" ] || {
  echo "FAIL=campaign_source_drift; do not dispatch unreviewed code" >&2
  exit 2
}
echo "RESOLVED_REPO=https://github.com/$repo"
echo "EXECUTION_DIR=GitHub_Actions"
echo "BRANCH=$branch"
echo "HEAD=$head"
echo "CAMPAIGN=ritsu_sticky_v018"
echo "MODE=cloud_unit_tests_and_unsigned_release_compile"
# Repeated invocation should not dispatch another run for an already
# successful exact commit. No operator-owned destructive operations.
existing="$(gh run list --repo "$repo" --workflow build.yml \
  --branch "$branch" --commit "$head" --event workflow_dispatch \
  --limit 20 --json databaseId,status,conclusion \
  --jq '[.[]|select(.status=="completed" and .conclusion=="success")][0].databaseId // empty')"
if [ -n "$existing" ]; then
  echo "ALREADY_VALIDATED_RUN=https://github.com/$repo/actions/runs/$existing"
  echo "INSTALLABLE_UPGRADE=BLOCKED_PENDING_SIGNING_COMPATIBILITY"
  exit 0
fi
gh workflow run build.yml --repo "$repo" --ref "$branch"
echo "DISPATCHED_REF=$head"
echo "NOTE=GitHub tests and unsigned compilation only; NOT an installable update"
echo "INSTALLABLE_UPGRADE=BLOCKED_PENDING_SIGNING_COMPATIBILITY"
