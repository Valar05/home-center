#!/data/data/com.termux/files/usr/bin/sh
set -eu

PROJECT="${1:-${FIREBASE_PROJECT:-home-center-dclar}}"
PRIVATE_KEY_FILE="${2:-${GITHUB_APP_PRIVATE_KEY_FILE:-}}"

need_env() {
  name="$1"
  value="$(printenv "$name" || true)"
  if [ -z "$value" ]; then
    echo "Missing required environment variable: $name" >&2
    exit 2
  fi
  printf '%s' "$value"
}

set_secret_from_value() {
  name="$1"
  value="$2"
  if gcloud secrets describe "$name" --project "$PROJECT" >/dev/null 2>&1; then
    printf '%s' "$value" | gcloud secrets versions add "$name" --project "$PROJECT" --data-file=- >/dev/null
  else
    printf '%s' "$value" | gcloud secrets create "$name" --project "$PROJECT" --replication-policy=automatic --data-file=- >/dev/null
  fi
  echo "$name stored in Secret Manager for $PROJECT"
}

set_secret_from_file() {
  name="$1"
  source_file="$2"
  if [ ! -f "$source_file" ]; then
    echo "Private key file not found: $source_file" >&2
    exit 2
  fi
  node - "$source_file" <<'NODE'
const {createPrivateKey} = require('node:crypto');
const fs = require('node:fs');
createPrivateKey(fs.readFileSync(process.argv[2], 'utf8'));
NODE
  if gcloud secrets describe "$name" --project "$PROJECT" >/dev/null 2>&1; then
    gcloud secrets versions add "$name" --project "$PROJECT" --data-file="$source_file" >/dev/null
  else
    gcloud secrets create "$name" --project "$PROJECT" --replication-policy=automatic --data-file="$source_file" >/dev/null
  fi
  echo "$name stored in Secret Manager for $PROJECT"
}

set_secret_from_value GITHUB_APP_ID "$(need_env GITHUB_APP_ID)"
set_secret_from_value GITHUB_APP_INSTALLATION_ID "$(need_env GITHUB_APP_INSTALLATION_ID)"
if [ -z "$PRIVATE_KEY_FILE" ]; then
  echo "Usage: sh tools/setup_github_admin_secrets.sh [project] PRIVATE_KEY_PEM" >&2
  echo "GITHUB_APP_PRIVATE_KEY is intentionally not accepted through the environment." >&2
  exit 2
fi
set_secret_from_file GITHUB_APP_PRIVATE_KEY "$PRIVATE_KEY_FILE"

if [ -n "${GITHUB_BOOTSTRAP_TOKEN:-}" ]; then
  set_secret_from_value GITHUB_BOOTSTRAP_TOKEN "$GITHUB_BOOTSTRAP_TOKEN"
else
  if ! gcloud secrets describe GITHUB_BOOTSTRAP_TOKEN --project "$PROJECT" >/dev/null 2>&1; then
    printf '' | gcloud secrets create GITHUB_BOOTSTRAP_TOKEN --project "$PROJECT" --replication-policy=automatic --data-file=- >/dev/null
    echo "GITHUB_BOOTSTRAP_TOKEN stored as empty optional secret for $PROJECT"
  else
    echo "GITHUB_BOOTSTRAP_TOKEN already exists; left unchanged"
  fi
fi
