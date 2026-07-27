#!/data/data/com.termux/files/usr/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
PROJECT="${1:-${FIREBASE_PROJECT:-home-center-dclar}}"
REGION="${GCLOUD_FUNCTIONS_REGION:-us-central1}"
shift || true

if [ "$#" -gt 0 ]; then
  FUNCTIONS="$*"
else
  FUNCTIONS="commandCenterMcp homeCenterMcp"
fi

case " $FUNCTIONS " in
  *" homeCenterMcp "*) sh "$ROOT/tools/assert_home_center_mcp_main_release.sh" "$ROOT" ;;
esac

deploy_command_center_mcp() {
  gcloud functions deploy commandCenterMcp \
    --gen2 \
    --project="$PROJECT" \
    --region="$REGION" \
    --runtime=nodejs22 \
    --source="$ROOT/functions" \
    --entry-point=commandCenterMcp \
    --trigger-http \
    --allow-unauthenticated \
    --timeout=300s \
    --set-env-vars=LOG_EXECUTION_ID=true,COMMAND_CENTER_RENDER_SERVICE_URL="${COMMAND_CENTER_RENDER_SERVICE_URL:-https://command-center-blender-render-vxybsaualq-uc.a.run.app}",COMMAND_CENTER_RENDER_BUCKET="${COMMAND_CENTER_RENDER_BUCKET:-home-center-dclar-command-center-renders}"
}

home_center_mcp_secrets_arg() {
  printf '%s' 'GOOGLE_OAUTH_CLIENT_ID=GOOGLE_OAUTH_CLIENT_ID:latest,GOOGLE_OAUTH_CLIENT_SECRET=GOOGLE_OAUTH_CLIENT_SECRET:latest,GITHUB_TOKEN=GITHUB_TOKEN:latest,GITHUB_BOOTSTRAP_TOKEN=GITHUB_BOOTSTRAP_TOKEN:latest,CARTESIA_API_KEY=CARTESIA_API_KEY:latest,GITHUB_APP_ID=GITHUB_APP_ID:latest,GITHUB_APP_INSTALLATION_ID=GITHUB_APP_INSTALLATION_ID:latest,GITHUB_APP_PRIVATE_KEY=GITHUB_APP_PRIVATE_KEY:latest'
}

deploy_home_center_mcp() {
  gcloud functions deploy homeCenterMcp \
    --gen2 \
    --project="$PROJECT" \
    --region="$REGION" \
    --runtime=nodejs22 \
    --source="$ROOT/functions" \
    --entry-point=homeCenterMcp \
    --trigger-http \
    --allow-unauthenticated \
    --timeout=300s \
    --memory=1Gi \
    --cpu=1 \
    --set-env-vars=HOME_CENTER_MCP_EXTENDED_TOOLS=true,HOME_CENTER_GITHUB_ADMIN_ENABLED=true,HOME_CENTER_GITHUB_ADMIN_OWNERS="${HOME_CENTER_GITHUB_ADMIN_OWNERS:-Valar05}",COMMAND_CENTER_RENDER_SERVICE_URL="${COMMAND_CENTER_RENDER_SERVICE_URL:-https://command-center-blender-render-vxybsaualq-uc.a.run.app}",COMMAND_CENTER_RENDER_BUCKET="${COMMAND_CENTER_RENDER_BUCKET:-home-center-dclar-command-center-renders}",COMMAND_CENTER_MCP_URL="${COMMAND_CENTER_MCP_URL:-https://us-central1-home-center-dclar.cloudfunctions.net/commandCenterMcp/mcp}" \
    --set-secrets="$(home_center_mcp_secrets_arg)"
}

deploy_audio_library_api() {
  gcloud functions deploy audioLibraryApi \
    --gen2 \
    --project="$PROJECT" \
    --region="$REGION" \
    --runtime=nodejs20 \
    --source="$ROOT/functions" \
    --entry-point=audioLibraryApi \
    --trigger-http \
    --allow-unauthenticated \
    --timeout=300s \
    --memory=512Mi \
    --set-env-vars=HOME_CENTER_GENERATED_BUCKET="${HOME_CENTER_GENERATED_BUCKET:-home-center-generated}",HOME_CENTER_AUDIO_LIBRARY_PUBLIC_BASE="${HOME_CENTER_AUDIO_LIBRARY_PUBLIC_BASE:-https://${REGION}-${PROJECT}.cloudfunctions.net/audioLibraryApi}"
}

deploy_credit_backed_http_function() {
  FN="$1"
  TIMEOUT="$2"
  SECRETS="$3"
  gcloud functions deploy "$FN" \
    --gen2 \
    --project="$PROJECT" \
    --region="$REGION" \
    --runtime=nodejs20 \
    --source="$ROOT/functions" \
    --entry-point="$FN" \
    --trigger-http \
    --allow-unauthenticated \
    --timeout="$TIMEOUT" \
    --memory=256Mi \
    --set-env-vars=LOG_EXECUTION_ID=true \
    --set-secrets="$SECRETS"
}

deploy_credit_backed_http() {
  deploy_credit_backed_http_function agentToolTurn 120s 'OPENAI_API_KEY=OPENAI_API_KEY:latest'
  deploy_credit_backed_http_function agentTurn 120s 'OPENAI_API_KEY=OPENAI_API_KEY:latest,GOOGLE_OAUTH_CLIENT_ID=GOOGLE_OAUTH_CLIENT_ID:latest,GOOGLE_OAUTH_CLIENT_SECRET=GOOGLE_OAUTH_CLIENT_SECRET:latest'
  deploy_credit_backed_http_function creativePromptSmoke 120s 'OPENAI_API_KEY=OPENAI_API_KEY:latest'
  deploy_credit_backed_http_function turnContractSmoke 120s 'OPENAI_API_KEY=OPENAI_API_KEY:latest'
  deploy_credit_backed_http_function metalPromptSmoke 300s 'OPENAI_API_KEY=OPENAI_API_KEY:latest,GOOGLE_OAUTH_CLIENT_ID=GOOGLE_OAUTH_CLIENT_ID:latest,GOOGLE_OAUTH_CLIENT_SECRET=GOOGLE_OAUTH_CLIENT_SECRET:latest'
  deploy_credit_backed_http_function tts 60s 'ELEVENLABS_API_KEY=ELEVENLABS_API_KEY:latest,CARTESIA_API_KEY=CARTESIA_API_KEY:latest'
  deploy_credit_backed_http_function speak 60s 'ELEVENLABS_API_KEY=ELEVENLABS_API_KEY:latest,CARTESIA_API_KEY=CARTESIA_API_KEY:latest'
  deploy_credit_backed_http_function ttsVoices 60s 'ELEVENLABS_API_KEY=ELEVENLABS_API_KEY:latest,CARTESIA_API_KEY=CARTESIA_API_KEY:latest'
}

deploy_command_center_render_worker() {
  QUEUE="commandCenterRenderWorker"
  PROJECT_NUMBER="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')"
  TASK_SERVICE_ACCOUNT="${COMMAND_CENTER_RENDER_TASK_SERVICE_ACCOUNT:-${PROJECT_NUMBER}-compute@developer.gserviceaccount.com}"

  gcloud functions deploy commandCenterRenderWorker \
    --gen2 \
    --project="$PROJECT" \
    --region="$REGION" \
    --runtime=nodejs22 \
    --source="$ROOT/functions" \
    --entry-point=commandCenterRenderWorker \
    --trigger-http \
    --no-allow-unauthenticated \
    --timeout=1800s \
    --memory=512Mi \
    --cpu=1 \
    --concurrency=1 \
    --max-instances=4 \
    --service-account="$TASK_SERVICE_ACCOUNT" \
    --set-env-vars=LOG_EXECUTION_ID=true,COMMAND_CENTER_RENDER_SERVICE_URL="${COMMAND_CENTER_RENDER_SERVICE_URL:-https://command-center-blender-render-vxybsaualq-uc.a.run.app}",COMMAND_CENTER_RENDER_BUCKET="${COMMAND_CENTER_RENDER_BUCKET:-home-center-dclar-command-center-renders}"

  gcloud projects add-iam-policy-binding "$PROJECT" \
    --member="serviceAccount:${TASK_SERVICE_ACCOUNT}" \
    --role=roles/cloudtasks.enqueuer >/dev/null
  gcloud iam service-accounts add-iam-policy-binding "$TASK_SERVICE_ACCOUNT" \
    --project="$PROJECT" \
    --member="serviceAccount:${TASK_SERVICE_ACCOUNT}" \
    --role=roles/iam.serviceAccountUser >/dev/null
  gcloud functions add-invoker-policy-binding commandCenterRenderWorker \
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
    --max-concurrent-dispatches=4 \
    --max-dispatches-per-second=4 \
    --max-attempts=1 \
    --max-retry-duration=0s
  gcloud tasks queues describe "$QUEUE" --project="$PROJECT" --location="$REGION" \
    --format='yaml(name,state,rateLimits,retryConfig)'
}

deploy_she_raw_mcp() {
  gcloud functions deploy sheRawMcp \
    --gen2 \
    --project="$PROJECT" \
    --region="$REGION" \
    --runtime=nodejs22 \
    --source="$ROOT/functions" \
    --entry-point=sheRawMcp \
    --trigger-http \
    --allow-unauthenticated \
    --timeout=300s
}

for fn in $FUNCTIONS; do
  case "$fn" in
    commandCenterMcp) deploy_command_center_mcp ;;
    commandCenterRenderWorker) deploy_command_center_render_worker ;;
    homeCenterMcp) deploy_home_center_mcp ;;
    audioLibraryApi) deploy_audio_library_api ;;
    creditBackedHttp) deploy_credit_backed_http ;;
    sheRawMcp) deploy_she_raw_mcp ;;
    *)
      echo "Unsupported gcloud deploy target: $fn" >&2
      echo "Supported: commandCenterMcp commandCenterRenderWorker homeCenterMcp audioLibraryApi creditBackedHttp sheRawMcp" >&2
      exit 2
      ;;
  esac
done
