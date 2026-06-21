#!/data/data/com.termux/files/usr/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"

PROJECT="${1:-${GOOGLE_CLOUD_PROJECT:-}}"
REGION="${REGION:-us-central1}"
SERVICE="dionysus-tax"
SERVICE_DIR="services/dionysus-tax"

if [ -z "$PROJECT" ]; then
  echo "Usage: sh tools/deploy_dionysus_cloud.sh <gcp-project-id>" >&2
  exit 2
fi

if ! command -v gcloud >/dev/null 2>&1; then
  echo "gcloud is not installed or not on PATH." >&2
  exit 127
fi

if [ -n "${DIONYSUS_API_KEY:-}" ]; then
  API_KEY="$DIONYSUS_API_KEY"
elif command -v python3 >/dev/null 2>&1; then
  API_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
elif command -v python >/dev/null 2>&1; then
  API_KEY="$(python -c 'import random; print("".join(random.choice("0123456789abcdef") for _ in range(64)))')"
elif command -v uuidgen >/dev/null 2>&1; then
  API_KEY="$(uuidgen | tr -d '-')$(date +%s)"
else
  API_KEY="dionysus-$(date +%s)"
fi

echo "Deploying Dionysus Tax to project $PROJECT in $REGION"

gcloud config set project "$PROJECT"

gcloud services enable run.googleapis.com cloudbuild.googleapis.com firestore.googleapis.com

if [ ! -f "$SERVICE_DIR/main.py" ]; then
  echo "Missing $SERVICE_DIR/main.py" >&2
  exit 1
fi

if [ ! -f "$SERVICE_DIR/requirements.txt" ]; then
  echo "Missing $SERVICE_DIR/requirements.txt" >&2
  exit 1
fi

cd "$SERVICE_DIR"

gcloud run deploy "$SERVICE" \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --set-env-vars "DIONYSUS_API_KEY=$API_KEY"

URL="$(gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)')"

cat > deploy_result.txt <<EOF
DIONYSUS_URL=$URL
DIONYSUS_API_KEY=$API_KEY
EOF

echo ""
echo "Dionysus Tax deployed."
echo "URL: $URL"
echo "Bearer token: $API_KEY"
echo ""
echo "Verify health:"
echo "curl \"$URL/health\""
echo ""
echo "Verify status:"
echo "curl \"$URL/status\" -H \"Authorization: Bearer $API_KEY\""
