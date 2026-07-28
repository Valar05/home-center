#!/data/data/com.termux/files/usr/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
PROJECT="${1:-${FIREBASE_PROJECT:-home-center-dclar}}"
REGION="${GCLOUD_FUNCTIONS_REGION:-us-central1}"
QUEUE="foundryAssetWorker"
HEAD_SHA="$(git -C "$ROOT" rev-parse HEAD)"
PUBLIC_MANIFEST_SHA256="$(node -e "const m=require(process.argv[1]);process.stdout.write(m.manifestSha256)" "$ROOT/contracts/home-center-public-tool-manifest.v1.json")"
QUEUE_WAS_RUNNING=false

sh "$ROOT/tools/assert_home_center_mcp_main_release.sh" "$ROOT"

node "$ROOT/tools/deploy_firestore_config_gcloud.mjs" "$PROJECT"
sh "$ROOT/tools/setup_generated_artifact_bucket.sh" "$PROJECT"

if gcloud tasks queues describe "$QUEUE" --project="$PROJECT" --location="$REGION" >/dev/null 2>&1; then
  STATE="$(gcloud tasks queues describe "$QUEUE" --project="$PROJECT" --location="$REGION" --format='value(state)')"
  if [ "$STATE" = "RUNNING" ]; then
    gcloud tasks queues pause "$QUEUE" --project="$PROJECT" --location="$REGION"
    QUEUE_WAS_RUNNING=true
  fi
fi
resume_queue() {
  if [ "$QUEUE_WAS_RUNNING" = "true" ]; then
    gcloud tasks queues resume "$QUEUE" --project="$PROJECT" --location="$REGION" >/dev/null
  fi
}
trap resume_queue EXIT HUP INT TERM

FOUNDRY_RELEASE_QUEUE_GUARDED=true sh "$ROOT/tools/deploy_foundry_worker.sh" "$PROJECT"
sh "$ROOT/tools/deploy_functions_termux.sh" "$PROJECT" commandCenterMcp homeCenterMcp

READY_URL="https://${REGION}-${PROJECT}.cloudfunctions.net/homeCenterMcp/ready"
READY_JSON="$(curl --fail --silent --show-error "$READY_URL")"
READY_JSON="$READY_JSON" EXPECTED_COMMIT="$HEAD_SHA" EXPECTED_MANIFEST="$PUBLIC_MANIFEST_SHA256" node - <<'VERIFY'
const payload=JSON.parse(process.env.READY_JSON);
const identity=payload.releaseIdentity||{};
if(!payload.ready) throw new Error('homeCenterMcp readiness is not green');
if(identity.sourceCommit!==process.env.EXPECTED_COMMIT) throw new Error('deployed source commit mismatch: '+identity.sourceCommit);
if(identity.sourceRef!=='refs/heads/main') throw new Error('deployed source ref is not main: '+identity.sourceRef);
if(identity.publicManifestSha256!==process.env.EXPECTED_MANIFEST) throw new Error('deployed public manifest mismatch: '+identity.publicManifestSha256);
process.stdout.write(JSON.stringify({ok:true,releaseIdentity:identity})+'\n');
VERIFY

HOME_CENTER_MCP_URL="https://${REGION}-${PROJECT}.cloudfunctions.net/homeCenterMcp/mcp" HOME_CENTER_EXPECTED_SOURCE_COMMIT="$HEAD_SHA" node "$ROOT/tools/home_center_production_catalog_test.mjs"

resume_queue
QUEUE_WAS_RUNNING=false
trap - EXIT HUP INT TERM
