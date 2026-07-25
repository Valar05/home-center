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

deploy_command_center_mcp() {
  gcloud functions deploy commandCenterMcp \
    --gen2 \
    --project="$PROJECT" \
    --region="$REGION" \
    --runtime=nodejs20 \
    --source="$ROOT/functions" \
    --entry-point=commandCenterMcp \
    --trigger-http \
    --allow-unauthenticated \
    --timeout=300s \
    --set-env-vars=LOG_EXECUTION_ID=true,COMMAND_CENTER_RENDER_SERVICE_URL="${COMMAND_CENTER_RENDER_SERVICE_URL:-https://command-center-blender-render-vxybsaualq-uc.a.run.app}",COMMAND_CENTER_RENDER_BUCKET="${COMMAND_CENTER_RENDER_BUCKET:-home-center-dclar-command-center-renders}"
}

deploy_home_center_mcp() {
  gcloud functions deploy homeCenterMcp \
    --gen2 \
    --project="$PROJECT" \
    --region="$REGION" \
    --runtime=nodejs20 \
    --source="$ROOT/functions" \
    --entry-point=homeCenterMcp \
    --trigger-http \
    --allow-unauthenticated \
    --timeout=300s \
    --set-env-vars=HOME_CENTER_MCP_EXTENDED_TOOLS=true,COMMAND_CENTER_RENDER_SERVICE_URL="${COMMAND_CENTER_RENDER_SERVICE_URL:-https://command-center-blender-render-vxybsaualq-uc.a.run.app}",COMMAND_CENTER_RENDER_BUCKET="${COMMAND_CENTER_RENDER_BUCKET:-home-center-dclar-command-center-renders}",COMMAND_CENTER_MCP_URL="${COMMAND_CENTER_MCP_URL:-https://us-central1-home-center-dclar.cloudfunctions.net/commandCenterMcp/mcp}" \
    --set-secrets=GOOGLE_OAUTH_CLIENT_ID=GOOGLE_OAUTH_CLIENT_ID:latest,GOOGLE_OAUTH_CLIENT_SECRET=GOOGLE_OAUTH_CLIENT_SECRET:latest,GITHUB_TOKEN=GITHUB_TOKEN:latest,CARTESIA_API_KEY=CARTESIA_API_KEY:latest
}

deploy_she_raw_mcp() {
  gcloud functions deploy sheRawMcp \
    --gen2 \
    --project="$PROJECT" \
    --region="$REGION" \
    --runtime=nodejs20 \
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
    sheRawMcp) deploy_she_raw_mcp ;;
    *)
      echo "Unsupported gcloud deploy target: $fn" >&2
      echo "Supported: commandCenterMcp homeCenterMcp sheRawMcp" >&2
      exit 2
      ;;
  esac
done
