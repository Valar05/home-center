#!/data/data/com.termux/files/usr/bin/sh
set -eu
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
PROJECT="${1:-${FIREBASE_PROJECT:-home-center-dclar}}"
REGION="${GCLOUD_FUNCTIONS_REGION:-us-central1}"
SERVICE="home-center-blender"
QUEUE="blenderWorkspace"
ASSIGNMENT="home-center-blender-workspace"
sh "$ROOT/tools/assert_home_center_mcp_main_release.sh" "$ROOT"
[ "${BLENDER_RELEASE_GUARDED:-}" = "true" ] || { echo "Blender workspace deploy requires tools/deploy_blender_workspace_release.sh." >&2; exit 24; }
eval "$(node "$ROOT/tools/worker_profile_contract.mjs" shell home-center-blender-workspace)"
node "$ROOT/tools/worker_profile_contract.mjs" validate-resolved home-center-blender-workspace cpu="$WORKER_CPU" memory="$WORKER_MEMORY" concurrency="$WORKER_CONCURRENCY" minInstances="$WORKER_MIN_INSTANCES" maxInstances="$WORKER_MAX_INSTANCES" timeoutSeconds="$WORKER_TIMEOUT_SECONDS"
# Required APIs are provisioned outside this least-privilege release lane.
# The concrete Artifact Registry, Cloud Build, Cloud Run, and Cloud Tasks calls below fail closed if an API is unavailable.
if ! gcloud artifacts repositories describe home-center --project="$PROJECT" --location="$REGION" >/dev/null 2>&1; then gcloud artifacts repositories create home-center --project="$PROJECT" --location="$REGION" --repository-format=docker --description="Home Center deterministic executors"; fi
HEAD_SHA="$(git -C "$ROOT" rev-parse HEAD)"
IMAGE="$REGION-docker.pkg.dev/$PROJECT/home-center/home-center-blender:$HEAD_SHA"
gcloud builds submit "$ROOT/blender_workspace" --project="$PROJECT" --tag="$IMAGE" --suppress-logs
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')"
TASK_SERVICE_ACCOUNT="${BLENDER_WORKSPACE_TASK_SERVICE_ACCOUNT:-${PROJECT_NUMBER}-compute@developer.gserviceaccount.com}"
gcloud run deploy "$SERVICE" --project="$PROJECT" --region="$REGION" --image="$IMAGE" --no-allow-unauthenticated --service-account="$TASK_SERVICE_ACCOUNT" --cpu="$WORKER_CPU" --memory="$WORKER_MEMORY" --concurrency="$WORKER_CONCURRENCY" --min-instances="$WORKER_MIN_INSTANCES" --max-instances="$WORKER_MAX_INSTANCES" --timeout="${WORKER_TIMEOUT_SECONDS}s" --set-env-vars=HOME_CENTER_ARTIFACT_BUCKET="${HOME_CENTER_ARTIFACT_BUCKET:-home-center-generated}",BLENDER_WORKSPACE_TIMEOUT_SECONDS=1700
SERVICE_URL="$(gcloud run services describe "$SERVICE" --project="$PROJECT" --region="$REGION" --format='value(status.url)')"
gcloud run services add-iam-policy-binding "$SERVICE" --project="$PROJECT" --region="$REGION" --member="serviceAccount:$TASK_SERVICE_ACCOUNT" --role=roles/run.invoker >/dev/null
gcloud iam service-accounts add-iam-policy-binding "$TASK_SERVICE_ACCOUNT" --project="$PROJECT" --member="serviceAccount:$TASK_SERVICE_ACCOUNT" --role=roles/iam.serviceAccountTokenCreator >/dev/null
if gcloud tasks queues describe "$QUEUE" --project="$PROJECT" --location="$REGION" >/dev/null 2>&1; then ACTION=update; else ACTION=create; fi
gcloud tasks queues "$ACTION" "$QUEUE" --project="$PROJECT" --location="$REGION" --max-concurrent-dispatches="$WORKER_MAX_INSTANCES" --max-dispatches-per-second=4 --max-attempts=1 --max-retry-duration=0s
gcloud run services describe "$SERVICE" --project="$PROJECT" --region="$REGION" --format=json | node "$ROOT/tools/worker_profile_contract.mjs" verify-live home-center-blender-workspace
printf '%s
' "BLENDER_WORKSPACE_TASK_URL=$SERVICE_URL" "BLENDER_WORKSPACE_TASK_SERVICE_ACCOUNT=$TASK_SERVICE_ACCOUNT"
