#!/data/data/com.termux/files/usr/bin/sh
set -eu

PROJECT="${1:-${FIREBASE_PROJECT:-home-center-dclar}}"

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

set_secret_from_value GITHUB_APP_ID "$(need_env GITHUB_APP_ID)"
set_secret_from_value GITHUB_APP_INSTALLATION_ID "$(need_env GITHUB_APP_INSTALLATION_ID)"
set_secret_from_value GITHUB_APP_PRIVATE_KEY "$(need_env GITHUB_APP_PRIVATE_KEY)"

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
