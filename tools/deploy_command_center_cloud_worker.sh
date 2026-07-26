#!/data/data/com.termux/files/usr/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
PROJECT="${1:-${FIREBASE_PROJECT:-home-center-dclar}}"
REGION="${GCLOUD_REGION:-us-central1}"
REPOSITORY="${COMMAND_CENTER_WORKER_REPOSITORY:-command-center-workers}"
JOB="${COMMAND_CENTER_CLOUD_WORKER_JOB:-command-center-debian-worker}"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/${REPOSITORY}/debian-codex:latest"
SNAPSHOT_BUCKET="${COMMAND_CENTER_WORKSPACE_SNAPSHOT_BUCKET:-${PROJECT}-command-center-worker-sessions}"
WORKER_TOKEN_SECRET="${COMMAND_CENTER_WORKER_TOKEN_SECRET:-COMMAND_CENTER_CLOUD_WORKER_TOKEN}"
OPENAI_SECRET="${COMMAND_CENTER_OPENAI_SECRET:-OPENAI_API_KEY}"
CODEX_ACCESS_TOKEN_SECRET="${COMMAND_CENTER_CODEX_ACCESS_TOKEN_SECRET:-CODEX_ACCESS_TOKEN}"
GITHUB_SECRET="${COMMAND_CENTER_GITHUB_SECRET:-GITHUB_TOKEN}"
SERVICE_ACCOUNT="${COMMAND_CENTER_WORKER_SERVICE_ACCOUNT:-}"

eval "$(node "$ROOT/tools/worker_profile_contract.mjs" shell command-center-codex)"
node "$ROOT/tools/worker_profile_contract.mjs" validate-resolved command-center-codex \
  "cpu=$WORKER_CPU" \
  "memory=$WORKER_MEMORY" \
  "tasks=$WORKER_TASKS" \
  "maxRetries=$WORKER_MAX_RETRIES" \
  "timeoutSeconds=$WORKER_TIMEOUT_SECONDS"

gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com storage.googleapis.com --project "$PROJECT" >/dev/null

if ! gcloud secrets describe "$WORKER_TOKEN_SECRET" --project "$PROJECT" >/dev/null 2>&1; then
  cat >&2 <<EOF
Missing Secret Manager secret ${WORKER_TOKEN_SECRET}.

First register the worker and store the returned workerToken in that secret:
  node tools/command_center_oneshot_worker.mjs register --manifest tools/command_center_base_manifests/cloud-run-debian-codex.json --config /tmp/cloud-run-debian-codex-worker.json
  # then add the workerToken value to Secret Manager secret ${WORKER_TOKEN_SECRET}

Rerun this deploy script after the secret exists.
EOF
  exit 2
fi

if ! gcloud artifacts repositories describe "$REPOSITORY" --project "$PROJECT" --location "$REGION" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$REPOSITORY" --project "$PROJECT" --location "$REGION" --repository-format docker --description "Command Center worker images" >/dev/null
fi

if ! gcloud storage buckets describe "gs://${SNAPSHOT_BUCKET}" --project "$PROJECT" >/dev/null 2>&1; then
  gcloud storage buckets create "gs://${SNAPSHOT_BUCKET}" --project "$PROJECT" --location "$REGION" --uniform-bucket-level-access >/dev/null
fi

gcloud builds submit "$ROOT" --project "$PROJECT" --config "$ROOT/cloud-worker/cloudbuild.yaml" --substitutions "_IMAGE=${IMAGE}"

SECRET_ARGS="COMMAND_CENTER_WORKER_TOKEN=${WORKER_TOKEN_SECRET}:latest,OPENAI_API_KEY=${OPENAI_SECRET}:latest,GH_TOKEN=${GITHUB_SECRET}:latest"
if gcloud secrets describe "$CODEX_ACCESS_TOKEN_SECRET" --project "$PROJECT" >/dev/null 2>&1; then
  SECRET_ARGS="${SECRET_ARGS},CODEX_ACCESS_TOKEN=${CODEX_ACCESS_TOKEN_SECRET}:latest"
fi

SERVICE_ACCOUNT_ARG=""
if [ -n "$SERVICE_ACCOUNT" ]; then
  SERVICE_ACCOUNT_ARG="--service-account=$SERVICE_ACCOUNT"
fi

gcloud run jobs deploy "$JOB" \
  --project "$PROJECT" \
  --region "$REGION" \
  --image "$IMAGE" \
  --tasks "$WORKER_TASKS" \
  --max-retries "$WORKER_MAX_RETRIES" \
  --cpu "$WORKER_CPU" \
  --memory "$WORKER_MEMORY" \
  --task-timeout "$WORKER_TIMEOUT_SECONDS" \
  --set-env-vars "COMMAND_CENTER_BASE=https://us-central1-${PROJECT}.cloudfunctions.net/commandCenterMcp,COMMAND_CENTER_WORKSPACE_SNAPSHOT_BUCKET=${SNAPSHOT_BUCKET}" \
  --set-secrets "$SECRET_ARGS" \
  $SERVICE_ACCOUNT_ARG

LIVE_CONFIG="$(mktemp)"
trap 'rm -f "$LIVE_CONFIG"' EXIT HUP INT TERM
gcloud run jobs describe "$JOB" --project "$PROJECT" --region "$REGION" --format=json >"$LIVE_CONFIG"
node "$ROOT/tools/worker_profile_contract.mjs" verify-live command-center-codex <"$LIVE_CONFIG"

cat <<EOF
Cloud worker image deployed:
  image: ${IMAGE}
  job: ${JOB}
  profile: ${WORKER_PROFILE}
  cpu: ${WORKER_CPU}
  memory: ${WORKER_MEMORY}
  snapshot bucket: gs://${SNAPSHOT_BUCKET}
EOF
