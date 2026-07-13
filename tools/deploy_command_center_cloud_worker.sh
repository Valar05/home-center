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
GITHUB_SECRET="${COMMAND_CENTER_GITHUB_SECRET:-GITHUB_TOKEN}"
SERVICE_ACCOUNT="${COMMAND_CENTER_WORKER_SERVICE_ACCOUNT:-}"
CPU="${COMMAND_CENTER_WORKER_CPU:-1}"
MEMORY="${COMMAND_CENTER_WORKER_MEMORY:-2Gi}"

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

SERVICE_ACCOUNT_ARG=""
if [ -n "$SERVICE_ACCOUNT" ]; then
  SERVICE_ACCOUNT_ARG="--service-account=$SERVICE_ACCOUNT"
fi

gcloud run jobs deploy "$JOB" \
  --project "$PROJECT" \
  --region "$REGION" \
  --image "$IMAGE" \
  --tasks 1 \
  --max-retries 0 \
  --cpu "$CPU" \
  --memory "$MEMORY" \
  --task-timeout 3600 \
  --set-env-vars "COMMAND_CENTER_BASE=https://us-central1-${PROJECT}.cloudfunctions.net/commandCenterMcp,COMMAND_CENTER_WORKSPACE_SNAPSHOT_BUCKET=${SNAPSHOT_BUCKET}" \
  --set-secrets "COMMAND_CENTER_WORKER_TOKEN=${WORKER_TOKEN_SECRET}:latest,OPENAI_API_KEY=${OPENAI_SECRET}:latest,GH_TOKEN=${GITHUB_SECRET}:latest" \
  $SERVICE_ACCOUNT_ARG

cat <<EOF
Cloud worker image deployed:
  image: ${IMAGE}
  job: ${JOB}
  cpu: ${CPU}
  memory: ${MEMORY}
  snapshot bucket: gs://${SNAPSHOT_BUCKET}
EOF
