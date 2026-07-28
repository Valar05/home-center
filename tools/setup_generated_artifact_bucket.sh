#!/data/data/com.termux/files/usr/bin/sh
set -eu

PROJECT="${1:-${FIREBASE_PROJECT:-home-center-dclar}}"
REGION="${GCLOUD_REGION:-us-central1}"
BUCKET="${HOME_CENTER_GENERATED_BUCKET:-home-center-generated}"
OWNER_MEMBER="${HOME_CENTER_BUCKET_OWNER:-user:dclarke1005@gmail.com}"
COMMAND_CENTER_SA="${COMMAND_CENTER_SERVICE_ACCOUNT:-}"
WORKER_SA="${COMMAND_CENTER_WORKER_SERVICE_ACCOUNT:-}"
TMP_JSON="${TMPDIR:-/tmp}/home-center-generated-lifecycle-$$.json"

# Required APIs are provisioned once; the release identity intentionally cannot enable services.
if ! gcloud storage buckets describe "gs://${BUCKET}" --project "$PROJECT" >/dev/null 2>&1; then
  gcloud storage buckets create "gs://${BUCKET}" \
    --project "$PROJECT" \
    --location "$REGION" \
    --uniform-bucket-level-access \
    --public-access-prevention >/dev/null
fi

gcloud storage buckets update "gs://${BUCKET}" \
  --project "$PROJECT" \
  --uniform-bucket-level-access \
  --public-access-prevention \
  --versioning >/dev/null

cat > "$TMP_JSON" <<'JSON'
{
  "rule": [
    {"action": {"type": "Delete"}, "condition": {"age": 7, "matchesPrefix": ["temp/"]}},
    {"action": {"type": "Delete"}, "condition": {"age": 30, "matchesPrefix": ["audio/drew/voice-tests/", "audio/june/voice-tests/", "audio/shared/voice-tests/"]}},
    {"action": {"type": "Delete"}, "condition": {"age": 30, "matchesPrefix": ["indexes/filesystem/v1/trash/"]}},
    {"action": {"type": "Delete"}, "condition": {"age": 14, "matchesPrefix": ["logs/"]}}
  ]
}
JSON

gcloud storage buckets update "gs://${BUCKET}" --project "$PROJECT" --lifecycle-file="$TMP_JSON" >/dev/null
rm -f "$TMP_JSON"

if [ -n "$OWNER_MEMBER" ]; then
  gcloud storage buckets add-iam-policy-binding "gs://${BUCKET}" --project "$PROJECT" --member "$OWNER_MEMBER" --role roles/storage.admin >/dev/null 2>&1 || true
fi
if [ -n "$COMMAND_CENTER_SA" ]; then
  gcloud storage buckets add-iam-policy-binding "gs://${BUCKET}" --project "$PROJECT" --member "serviceAccount:${COMMAND_CENTER_SA}" --role roles/storage.objectAdmin >/dev/null
fi
if [ -n "$WORKER_SA" ]; then
  gcloud storage buckets add-iam-policy-binding "gs://${BUCKET}" --project "$PROJECT" --member "serviceAccount:${WORKER_SA}" --role roles/storage.objectAdmin >/dev/null
fi

gcloud storage buckets describe "gs://${BUCKET}" --project "$PROJECT" --format=json | node -e '
let s=""; process.stdin.on("data", c => s += c); process.stdin.on("end", () => { const b=JSON.parse(s); console.log(JSON.stringify({ok:true, bucket:"gs://" + (b.name || process.env.BUCKET), uniformBucketLevelAccess:b.iamConfiguration && b.iamConfiguration.uniformBucketLevelAccess, publicAccessPrevention:b.iamConfiguration && b.iamConfiguration.publicAccessPrevention, versioning:b.versioning, lifecycle:b.lifecycle}, null, 2)); });'
