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
    --timeout=300s
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
    --set-env-vars=HOME_CENTER_MCP_EXTENDED_TOOLS=true \
    --set-secrets=GOOGLE_OAUTH_CLIENT_ID=GOOGLE_OAUTH_CLIENT_ID:latest,GOOGLE_OAUTH_CLIENT_SECRET=GOOGLE_OAUTH_CLIENT_SECRET:latest,GITHUB_TOKEN=GITHUB_TOKEN:latest
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
