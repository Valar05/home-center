#!/data/data/com.termux/files/usr/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
PROJECT="${1:-${FIREBASE_PROJECT:-home-center-dclar}}"
REGION="${GCLOUD_REGION:-us-central1}"
REPOSITORY="${COMMAND_CENTER_RENDER_REPOSITORY:-command-center-workers}"
SERVICE="${COMMAND_CENTER_RENDER_SERVICE:-command-center-blender-render}"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/${REPOSITORY}/blender-render:latest"
CACHE_BUCKET="${COMMAND_CENTER_RENDER_BUCKET:-${HOME_CENTER_GENERATED_BUCKET:-home-center-generated}}"
SERVICE_ACCOUNT="${COMMAND_CENTER_RENDER_SERVICE_ACCOUNT:-}"

eval "$(node "$ROOT/tools/worker_profile_contract.mjs" shell command-center-blender-render)"
MIN_INSTANCES="${COMMAND_CENTER_RENDER_MIN_INSTANCES:-0}"
node "$ROOT/tools/worker_profile_contract.mjs" validate-resolved command-center-blender-render \
  "cpu=$WORKER_CPU" \
  "memory=$WORKER_MEMORY" \
  "concurrency=$WORKER_CONCURRENCY" \
  "minInstances=$MIN_INSTANCES" \
  "maxInstances=$WORKER_MAX_INSTANCES" \
  "timeoutSeconds=$WORKER_TIMEOUT_SECONDS"

gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com storage.googleapis.com --project "$PROJECT" >/dev/null

if ! gcloud artifacts repositories describe "$REPOSITORY" --project "$PROJECT" --location "$REGION" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$REPOSITORY" --project "$PROJECT" --location "$REGION" --repository-format docker --description "Command Center worker and render images" >/dev/null
fi

if ! gcloud storage buckets describe "gs://${CACHE_BUCKET}" --project "$PROJECT" >/dev/null 2>&1; then
  gcloud storage buckets create "gs://${CACHE_BUCKET}" --project "$PROJECT" --location "$REGION" --uniform-bucket-level-access >/dev/null
fi

gcloud builds submit "$ROOT" --project "$PROJECT" --config "$ROOT/cloud-render/cloudbuild.yaml" --substitutions "_IMAGE=${IMAGE}"

SERVICE_ACCOUNT_ARG=""
if [ -n "$SERVICE_ACCOUNT" ]; then
  SERVICE_ACCOUNT_ARG="--service-account=$SERVICE_ACCOUNT"
fi

gcloud run deploy "$SERVICE" \
  --project "$PROJECT" \
  --region "$REGION" \
  --image "$IMAGE" \
  --no-allow-unauthenticated \
  --cpu "$WORKER_CPU" \
  --memory "$WORKER_MEMORY" \
  --concurrency "$WORKER_CONCURRENCY" \
  --timeout "$WORKER_TIMEOUT_SECONDS" \
  --min-instances "$MIN_INSTANCES" \
  --max-instances "$WORKER_MAX_INSTANCES" \
  --cpu-boost \
  --set-env-vars "RENDER_CACHE_BUCKET=${CACHE_BUCKET},HOME_CENTER_GENERATED_BUCKET=${CACHE_BUCKET},COMMAND_CENTER_GENERATED_BUCKET=${CACHE_BUCKET}" \
  $SERVICE_ACCOUNT_ARG

LIVE_CONFIG="$(mktemp)"
trap 'rm -f "$LIVE_CONFIG"' EXIT HUP INT TERM
gcloud run services describe "$SERVICE" --project "$PROJECT" --region "$REGION" --format=json >"$LIVE_CONFIG"
node "$ROOT/tools/worker_profile_contract.mjs" verify-live command-center-blender-render <"$LIVE_CONFIG"

SERVICE_URL="$(gcloud run services describe "$SERVICE" --project "$PROJECT" --region "$REGION" --format='value(status.url)')"
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')"
FUNCTIONS_SA="${COMMAND_CENTER_FUNCTIONS_INVOKER:-${PROJECT_NUMBER}-compute@developer.gserviceaccount.com}"

gcloud run services add-iam-policy-binding "$SERVICE" \
  --project "$PROJECT" \
  --region "$REGION" \
  --member "serviceAccount:${FUNCTIONS_SA}" \
  --role roles/run.invoker >/dev/null

cat <<EOF
Command Center Blender render service deployed:
  service: ${SERVICE}
  url: ${SERVICE_URL}
  image: ${IMAGE}
  profile: ${WORKER_PROFILE}
  cpu: ${WORKER_CPU}
  memory: ${WORKER_MEMORY}
  concurrency: ${WORKER_CONCURRENCY}
  instances: ${MIN_INSTANCES}-${WORKER_MAX_INSTANCES}
  cache: gs://${CACHE_BUCKET}
  invoker: ${FUNCTIONS_SA}

Set Command Center function env:
  COMMAND_CENTER_RENDER_SERVICE_URL=${SERVICE_URL}
EOF
