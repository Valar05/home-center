#!/data/data/com.termux/files/usr/bin/sh
set -eu

PROJECT="${1:-${FIREBASE_PROJECT:-home-center-dclar}}"
REGION="${GCLOUD_REGION:-us-central1}"
SECRET="${COMMAND_CENTER_CODEX_ACCESS_TOKEN_SECRET:-CODEX_ACCESS_TOKEN}"
JOBS="${COMMAND_CENTER_CODEX_ACCESS_TOKEN_JOBS:-command-center-debian-worker,cloud-debian-codex-autoprov-20260725-0206}"
SERVICE_ACCOUNT="${COMMAND_CENTER_WORKER_SERVICE_ACCOUNT:-}"
UPDATE_JOBS="${COMMAND_CENTER_UPDATE_CODEX_ACCESS_TOKEN_JOBS:-1}"

usage() {
  cat <<EOF
Usage:
  CODEX_ACCESS_TOKEN=<token> sh tools/ingest_codex_access_token.sh [gcp-project]
  printf %s "<token>" | sh tools/ingest_codex_access_token.sh [gcp-project]

Environment:
  COMMAND_CENTER_CODEX_ACCESS_TOKEN_SECRET  Secret name. Default: CODEX_ACCESS_TOKEN
  COMMAND_CENTER_CODEX_ACCESS_TOKEN_JOBS    Comma-separated Cloud Run jobs to update.
  COMMAND_CENTER_WORKER_SERVICE_ACCOUNT     Runtime service account. Default: Compute default SA.
  COMMAND_CENTER_UPDATE_CODEX_ACCESS_TOKEN_JOBS=0  Store secret only, do not update jobs.
EOF
}

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  usage
  exit 0
fi

if [ -n "${CODEX_ACCESS_TOKEN:-}" ]; then
  TOKEN="$CODEX_ACCESS_TOKEN"
else
  if [ -t 0 ]; then
    echo "Paste or pipe CODEX_ACCESS_TOKEN on stdin, or set CODEX_ACCESS_TOKEN in the environment." >&2
    exit 2
  fi
  TOKEN="$(cat)"
fi

TOKEN="$(printf %s "$TOKEN" | tr -d '\r' | sed 's/[[:space:]]*$//')"
if [ -z "$TOKEN" ]; then
  echo "CODEX_ACCESS_TOKEN is empty." >&2
  exit 2
fi

case "$TOKEN" in
  *"
"*|*"
	"*)
    echo "CODEX_ACCESS_TOKEN must be a single token, not a multi-line blob." >&2
    exit 2
    ;;
esac

if [ -z "$SERVICE_ACCOUNT" ]; then
  PROJECT_NUMBER="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')"
  SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
fi

TOKEN_SHA="$(printf %s "$TOKEN" | sha256sum | awk '{print $1}')"

gcloud services enable secretmanager.googleapis.com run.googleapis.com --project "$PROJECT" >/dev/null

if ! gcloud secrets describe "$SECRET" --project "$PROJECT" >/dev/null 2>&1; then
  gcloud secrets create "$SECRET" --project "$PROJECT" --replication-policy=automatic >/dev/null
fi

printf %s "$TOKEN" | gcloud secrets versions add "$SECRET" --project "$PROJECT" --data-file=- >/dev/null

gcloud secrets add-iam-policy-binding "$SECRET" \
  --project "$PROJECT" \
  --member "serviceAccount:${SERVICE_ACCOUNT}" \
  --role roles/secretmanager.secretAccessor >/dev/null

UPDATED_JOBS=""
if [ "$UPDATE_JOBS" != "0" ]; then
  OLD_IFS="$IFS"
  IFS=,
  for JOB in $JOBS; do
    IFS="$OLD_IFS"
    JOB="$(printf %s "$JOB" | sed 's/^ *//; s/ *$//')"
    if [ -z "$JOB" ]; then
      IFS=,
      continue
    fi
    if gcloud run jobs describe "$JOB" --project "$PROJECT" --region "$REGION" >/dev/null 2>&1; then
      gcloud run jobs update "$JOB" \
        --project "$PROJECT" \
        --region "$REGION" \
        --update-secrets "CODEX_ACCESS_TOKEN=${SECRET}:latest" >/dev/null
      UPDATED_JOBS="${UPDATED_JOBS}${UPDATED_JOBS:+,}${JOB}"
    fi
    IFS=,
  done
  IFS="$OLD_IFS"
fi

cat <<EOF
Codex access token ingested.
project: ${PROJECT}
secret: ${SECRET}
secret_ref: secretmanager://${PROJECT}/${SECRET}/latest
sha256: ${TOKEN_SHA}
service_account: ${SERVICE_ACCOUNT}
updated_jobs: ${UPDATED_JOBS:-none}
EOF
