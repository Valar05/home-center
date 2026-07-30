#!/data/data/com.termux/files/usr/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
PROJECT="${1:-${FIREBASE_PROJECT:-home-center-dclar}}"
REGION="${GCLOUD_FUNCTIONS_REGION:-us-central1}"
shift || true

SOURCE_REPOSITORY="Valar05/home-center"
SOURCE_COMMIT="$(git -C "$ROOT" rev-parse HEAD)"
SOURCE_REF="refs/heads/main"
PUBLIC_MANIFEST_SHA256="$(node -e "const m=require(process.argv[1]); process.stdout.write(m.manifestSha256)" "$ROOT/contracts/home-center-public-tool-manifest.v1.json")"

if [ "$#" -gt 0 ]; then
  FUNCTIONS="$*"
else
  FUNCTIONS="commandCenterMcp homeCenterMcp"
fi

case " $FUNCTIONS " in
  *" homeCenterMcp "*|*" commandCenterMcp "*) sh "$ROOT/tools/assert_home_center_mcp_main_release.sh" "$ROOT" ;;
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
    --set-env-vars=LOG_EXECUTION_ID=true
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
    --set-env-vars=HOME_CENTER_MCP_EXTENDED_TOOLS=true,HOME_CENTER_SOURCE_REPOSITORY="$SOURCE_REPOSITORY",HOME_CENTER_SOURCE_COMMIT="$SOURCE_COMMIT",HOME_CENTER_SOURCE_REF="$SOURCE_REF",HOME_CENTER_PUBLIC_MANIFEST_SHA256="$PUBLIC_MANIFEST_SHA256",HOME_CENTER_GITHUB_ADMIN_ENABLED=true,HOME_CENTER_GITHUB_ADMIN_OWNERS="${HOME_CENTER_GITHUB_ADMIN_OWNERS:-Valar05}",COMMAND_CENTER_MCP_URL="${COMMAND_CENTER_MCP_URL:-https://us-central1-home-center-dclar.cloudfunctions.net/commandCenterMcp/mcp}",TVTROPER_RETRIEVAL_URL="${TVTROPER_RETRIEVAL_URL:-https://tvtroper-retrieval-vxybsaualq-uc.a.run.app}",BLENDER_WORKSPACE_TASK_URL="${BLENDER_WORKSPACE_TASK_URL:-}",BLENDER_WORKSPACE_TASK_SERVICE_ACCOUNT="${BLENDER_WORKSPACE_TASK_SERVICE_ACCOUNT:-}",BLENDER_WORKSPACE_QUEUE="${BLENDER_WORKSPACE_QUEUE:-blenderWorkspace}",BLENDER_WORKSPACE_REGION="${BLENDER_WORKSPACE_REGION:-us-central1}" \
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
    homeCenterMcp) deploy_home_center_mcp ;;
    audioLibraryApi) deploy_audio_library_api ;;
    creditBackedHttp) deploy_credit_backed_http ;;
    sheRawMcp) deploy_she_raw_mcp ;;
    *)
      echo "Unsupported gcloud deploy target: $fn" >&2
      echo "Supported: commandCenterMcp homeCenterMcp audioLibraryApi creditBackedHttp sheRawMcp" >&2
      exit 2
      ;;
  esac
done
