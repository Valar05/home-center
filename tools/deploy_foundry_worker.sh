#!/data/data/com.termux/files/usr/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
PROJECT="${1:-${FIREBASE_PROJECT:-home-center-dclar}}"
REGION="${GCLOUD_FUNCTIONS_REGION:-us-central1}"
ASSIGNMENT="fortress-model-foundry"
QUEUE="foundryAssetWorker"
SERVICE="foundryassetworker"

sh "$ROOT/tools/assert_home_center_mcp_main_release.sh" "$ROOT"
[ "${FOUNDRY_RELEASE_QUEUE_GUARDED:-}" = "true" ] || { echo "Foundry worker deploy requires tools/deploy_foundry_v2_release.sh so its queue remains paused across the worker and MCP swap." >&2; exit 24; }

eval "$(node "$ROOT/tools/worker_profile_contract.mjs" shell fortress-model-foundry)"
node "$ROOT/tools/worker_profile_contract.mjs" validate-resolved fortress-model-foundry \
  cpu="$WORKER_CPU" memory="$WORKER_MEMORY" concurrency="$WORKER_CONCURRENCY" \
  minInstances="$WORKER_MIN_INSTANCES" maxInstances="$WORKER_MAX_INSTANCES" timeoutSeconds="$WORKER_TIMEOUT_SECONDS"

PROJECT_NUMBER="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')"
TASK_SERVICE_ACCOUNT="${FOUNDRY_TASK_SERVICE_ACCOUNT:-${PROJECT_NUMBER}-compute@developer.gserviceaccount.com}"

gcloud functions deploy foundryAssetWorker \
  --gen2 \
  --project="$PROJECT" \
  --region="$REGION" \
  --runtime=nodejs22 \
  --source="$ROOT/functions" \
  --entry-point=foundryAssetWorker \
  --trigger-http \
  --no-allow-unauthenticated \
  --timeout="${WORKER_TIMEOUT_SECONDS}s" \
  --memory="$WORKER_MEMORY" \
  --cpu="$WORKER_CPU" \
  --concurrency="$WORKER_CONCURRENCY" \
  --min-instances="$WORKER_MIN_INSTANCES" \
  --max-instances="$WORKER_MAX_INSTANCES" \
  --service-account="$TASK_SERVICE_ACCOUNT" \
  --set-env-vars=LOG_EXECUTION_ID=true,HOME_CENTER_ARTIFACT_BUCKET="${HOME_CENTER_ARTIFACT_BUCKET:-home-center-generated}"

# Project-level task and service-account IAM is provisioned once. Release automation
# updates runtime resources but intentionally cannot rewrite project IAM.
gcloud functions add-invoker-policy-binding foundryAssetWorker \
  --project="$PROJECT" \
  --region="$REGION" \
  --member="serviceAccount:${TASK_SERVICE_ACCOUNT}" >/dev/null

if gcloud tasks queues describe "$QUEUE" --project="$PROJECT" --location="$REGION" >/dev/null 2>&1; then
  QUEUE_ACTION=update
else
  QUEUE_ACTION=create
fi
gcloud tasks queues "$QUEUE_ACTION" "$QUEUE" \
  --project="$PROJECT" \
  --location="$REGION" \
  --max-concurrent-dispatches="$WORKER_MAX_INSTANCES" \
  --max-dispatches-per-second=4 \
  --max-attempts=1 \
  --max-retry-duration=0s

gcloud run services describe "$SERVICE" --project="$PROJECT" --region="$REGION" --format=json \
  | node "$ROOT/tools/worker_profile_contract.mjs" verify-live fortress-model-foundry
