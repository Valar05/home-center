#!/data/data/com.termux/files/usr/bin/sh
set -eu

PROJECT="${FIREBASE_PROJECT:-home-center-dclar}"
BILLING_ACCOUNT="${BILLING_ACCOUNT:-0177BC-8C61C8-CD30A1}"
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
DEPLOY_DIR="${TMPDIR:-/data/data/com.termux/files/usr/tmp}/home-center-functions-deploy"

need_env() {
  name="$1"
  value="$(printenv "$name" || true)"
  if [ -z "$value" ]; then
    printf '%s: ' "$name" >&2
    stty -echo 2>/dev/null || true
    IFS= read -r value
    stty echo 2>/dev/null || true
    printf '\n' >&2
  fi
  if [ -z "$value" ]; then
    echo "$name is required" >&2
    exit 1
  fi
  printf '%s' "$value"
}

set_secret() {
  name="$1"
  value="$2"
  if gcloud secrets describe "$name" --project "$PROJECT" >/dev/null 2>&1; then
    printf '%s' "$value" | gcloud secrets versions add "$name" --project "$PROJECT" --data-file=- >/dev/null
  else
    printf '%s' "$value" | gcloud secrets create "$name" --project "$PROJECT" --replication-policy=automatic --data-file=- >/dev/null
  fi
  echo "$name set"
}

echo "Configuring Firebase project $PROJECT"
gcloud billing projects link "$PROJECT" --billing-account="$BILLING_ACCOUNT" >/dev/null
gcloud services enable secretmanager.googleapis.com cloudfunctions.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com run.googleapis.com firebaseextensions.googleapis.com --project "$PROJECT" >/dev/null

OPENAI_VALUE="$(need_env OPENAI_API_KEY)"
GOOGLE_ID="$(need_env GOOGLE_OAUTH_CLIENT_ID)"
GOOGLE_SECRET="$(need_env GOOGLE_OAUTH_CLIENT_SECRET)"

set_secret OPENAI_API_KEY "$OPENAI_VALUE"
set_secret GOOGLE_OAUTH_CLIENT_ID "$GOOGLE_ID"
set_secret GOOGLE_OAUTH_CLIENT_SECRET "$GOOGLE_SECRET"

python3 - <<PY
from pathlib import Path
import shutil
src=Path('$ROOT')
dst=Path('$DEPLOY_DIR')
if (dst/'functions').exists():
    shutil.rmtree(dst/'functions')
dst.mkdir(parents=True, exist_ok=True)
shutil.copytree(src/'functions', dst/'functions', ignore=shutil.ignore_patterns('node_modules'))
shutil.copy2(src/'firebase.json', dst/'firebase.json')
PY

npm install --prefix "$DEPLOY_DIR/functions" >/dev/null
FUNCTIONS_MANIFEST_OUTPUT_PATH="$DEPLOY_DIR/functions/functions.yaml" node "$DEPLOY_DIR/functions/node_modules/firebase-functions/lib/bin/firebase-functions.js" "$DEPLOY_DIR/functions" ignored
firebase deploy --only functions --project "$PROJECT" --config "$DEPLOY_DIR/firebase.json"
curl -fsS "https://us-central1-$PROJECT.cloudfunctions.net/health"
echo
