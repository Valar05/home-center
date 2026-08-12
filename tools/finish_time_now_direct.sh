#!/data/data/com.termux/files/usr/bin/sh
set -eu

PROJECT="${FIREBASE_PROJECT:-home-center-dclar}"
REGION="${GCLOUD_FUNCTIONS_REGION:-us-central1}"
REPO_URL="${HOME_CENTER_REPO_URL:-https://github.com/Valar05/home-center.git}"
WORK_ROOT="${TMPDIR:-$HOME/.cache}/home-center-time-now"
STAMP="$(date +%s)"
WORK="$WORK_ROOT/$STAMP"

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "NEED: $1 is not installed or not on PATH." >&2
    exit 10
  }
}
need git
need node
need gcloud

mkdir -p "$WORK_ROOT"
trap 'status=$?; if [ "$status" -eq 0 ]; then rm -rf "$WORK"; else echo "WORKDIR PRESERVED: $WORK" >&2; fi; exit "$status"' EXIT INT TERM

echo "[1/8] Clone authoritative main without GitHub Actions or LFS smudge"
GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 --branch main "$REPO_URL" "$WORK"
cd "$WORK"

echo "[2/8] Confirm direct GCP identity"
ACCOUNT="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' | head -n 1)"
if [ -z "$ACCOUNT" ]; then
  echo "NEED: gcloud has no active authenticated account. Run: gcloud auth login" >&2
  exit 11
fi
printf 'gcloud account: %s\nproject: %s\nregion: %s\n' "$ACCOUNT" "$PROJECT" "$REGION"

echo "[3/8] Install literal time.now into Home Center drive_operation source"
node tools/install_time_now_runtime_patch.mjs
node --check functions/home_center_mcp.js
git diff --check
if ! grep -Fq "'time.now':" functions/home_center_mcp.js; then
  echo "FAIL: source registry does not contain literal time.now after patch." >&2
  exit 12
fi
if ! grep -Fq "operation === 'time.now'" functions/home_center_mcp.js; then
  echo "FAIL: runtime handler does not contain literal time.now after patch." >&2
  exit 13
fi

echo "[4/8] Commit exact source change with CI skip marker"
if ! git diff --quiet -- functions/home_center_mcp.js; then
  if ! git config user.name >/dev/null 2>&1 || ! git config user.email >/dev/null 2>&1; then
    echo "NEED: git user.name and user.email are not configured. Configure them, then rerun this script." >&2
    exit 14
  fi
  git add functions/home_center_mcp.js
  git commit -m 'Deploy literal Home Center time.now [skip ci]'
fi
COMMIT="$(git rev-parse HEAD)"

echo "[5/8] Push main directly; no workflow dispatch"
git push origin HEAD:main
REMOTE="$(git ls-remote origin refs/heads/main | awk '{print $1}')"
if [ "$REMOTE" != "$COMMIT" ]; then
  echo "FAIL: remote main did not resolve to committed time.now source." >&2
  exit 15
fi

echo "[6/8] Deploy only homeCenterMcp directly with gcloud"
GCLOUD_FUNCTIONS_REGION="$REGION" sh tools/deploy_functions_termux.sh "$PROJECT" homeCenterMcp

echo "[7/8] Verify deployed release identity"
READY_URL="https://${REGION}-${PROJECT}.cloudfunctions.net/homeCenterMcp/ready"
READY_JSON="$(curl --fail --silent --show-error "$READY_URL")"
READY_JSON="$READY_JSON" EXPECTED="$COMMIT" node -e '
const p=JSON.parse(process.env.READY_JSON); const i=p.releaseIdentity||{};
if(!p.ready) throw new Error("Home Center readiness is false");
if(i.sourceCommit!==process.env.EXPECTED) throw new Error(`sourceCommit mismatch: ${i.sourceCommit} != ${process.env.EXPECTED}`);
if(i.sourceRef!=="refs/heads/main") throw new Error(`sourceRef mismatch: ${i.sourceRef}`);
console.log(JSON.stringify({ready:p.ready,releaseIdentity:i},null,2));
'

echo "[8/8] Invoke literal time.now twice through live Home Center"
HOME_CENTER_MCP_URL="https://${REGION}-${PROJECT}.cloudfunctions.net/homeCenterMcp/mcp" node tools/time_now_live_test.mjs

echo "TIME.NOW DIRECT DEPLOY COMPLETE"
echo "commit=$COMMIT"
echo "No GitHub Actions were dispatched by this script."
