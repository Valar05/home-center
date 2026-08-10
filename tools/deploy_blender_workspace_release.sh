#!/data/data/com.termux/files/usr/bin/sh
set -eu
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
PROJECT="${1:-${FIREBASE_PROJECT:-home-center-dclar}}"
REGION="${GCLOUD_FUNCTIONS_REGION:-us-central1}"
OLD_QUEUE="foundryAssetWorker"
HEAD_SHA="$(git -C "$ROOT" rev-parse HEAD)"
PUBLIC_MANIFEST_SHA256="$(node -e "const m=require(process.argv[1]);process.stdout.write(m.manifestSha256)" "$ROOT/contracts/home-center-public-tool-manifest.v1.json")"
sh "$ROOT/tools/assert_home_center_mcp_main_release.sh" "$ROOT"
node "$ROOT/tools/deploy_firestore_config_gcloud.mjs" "$PROJECT"
sh "$ROOT/tools/setup_generated_artifact_bucket.sh" "$PROJECT"
if gcloud tasks queues describe "$OLD_QUEUE" --project="$PROJECT" --location="$REGION" >/dev/null 2>&1; then gcloud tasks queues pause "$OLD_QUEUE" --project="$PROJECT" --location="$REGION" >/dev/null || true; fi
WORKER_ENV="$(BLENDER_RELEASE_GUARDED=true sh "$ROOT/tools/deploy_blender_workspace_worker.sh" "$PROJECT")"
BLENDER_WORKSPACE_TASK_URL="$(printf '%s\n' "$WORKER_ENV" | sed -n 's/^BLENDER_WORKSPACE_TASK_URL=//p' | tail -n 1)"
BLENDER_WORKSPACE_TASK_SERVICE_ACCOUNT="$(printf '%s\n' "$WORKER_ENV" | sed -n 's/^BLENDER_WORKSPACE_TASK_SERVICE_ACCOUNT=//p' | tail -n 1)"
[ -n "$BLENDER_WORKSPACE_TASK_URL" ] && [ -n "$BLENDER_WORKSPACE_TASK_SERVICE_ACCOUNT" ]
BLENDER_WORKSPACE_PROJECT="$PROJECT"
export BLENDER_WORKSPACE_PROJECT BLENDER_WORKSPACE_TASK_URL BLENDER_WORKSPACE_TASK_SERVICE_ACCOUNT
sh "$ROOT/tools/deploy_functions_termux.sh" "$PROJECT" commandCenterMcp homeCenterMcp localVoiceFarm computerHands veniceNerve
READY_URL="https://${REGION}-${PROJECT}.cloudfunctions.net/homeCenterMcp/ready"
READY_JSON="$(curl --fail --silent --show-error "$READY_URL")"
READY_JSON="$READY_JSON" EXPECTED_COMMIT="$HEAD_SHA" EXPECTED_MANIFEST="$PUBLIC_MANIFEST_SHA256" node -e 'const p=JSON.parse(process.env.READY_JSON),i=p.releaseIdentity||{};if(!p.ready||i.sourceCommit!==process.env.EXPECTED_COMMIT||i.sourceRef!=="refs/heads/main"||i.publicManifestSha256!==process.env.EXPECTED_MANIFEST)throw new Error("deployed release identity mismatch");console.log(JSON.stringify(i))'
LOCAL_VOICE_HEALTH_URL="https://${REGION}-${PROJECT}.cloudfunctions.net/localVoiceFarm/local-voice-farm/v1/health"
LOCAL_VOICE_HEALTH_JSON="$(curl --fail --silent --show-error "$LOCAL_VOICE_HEALTH_URL")"
LOCAL_VOICE_HEALTH_JSON="$LOCAL_VOICE_HEALTH_JSON" node -e 'const p=JSON.parse(process.env.LOCAL_VOICE_HEALTH_JSON);if(!p.ok||p.service!=="local-voice-farm"||p.apiVersion!=="home-center.local-voice-farm-api.v1"||p.contractVersion!=="home-center.local-voice-farm.v1"||p.provider!=="local_cauldron"||p.engine!=="kokoro-onnx"||p.cloningEnabled!==false)throw new Error("local voice farm deployment health mismatch");console.log(JSON.stringify(p))'
COMPUTER_HANDS_HEALTH_URL="https://${REGION}-${PROJECT}.cloudfunctions.net/computerHands/computer-hands/v1/health"
COMPUTER_HANDS_HEALTH_JSON="$(curl --fail --silent --show-error "$COMPUTER_HANDS_HEALTH_URL")"
COMPUTER_HANDS_HEALTH_JSON="$COMPUTER_HANDS_HEALTH_JSON" node -e 'const p=JSON.parse(process.env.COMPUTER_HANDS_HEALTH_JSON);if(!p.ok||p.service!=="computer-hands"||p.apiVersion!=="home-center.computer-hands-api.v1"||p.contractVersion!=="home-center.computer-hands-contract.v1"||p.fileLayer!=="drive_sync"||!Array.isArray(p.capabilities)||!p.capabilities.includes("screen.capture")||!p.capabilities.includes("shell.exec"))throw new Error("computer hands deployment health mismatch");console.log(JSON.stringify(p))'
VENICE_NERVE_HEALTH_URL="https://${REGION}-${PROJECT}.cloudfunctions.net/veniceNerve/venice-nerve/v1/health"
VENICE_NERVE_HEALTH_JSON="$(curl --fail --silent --show-error "$VENICE_NERVE_HEALTH_URL")"
VENICE_NERVE_HEALTH_JSON="$VENICE_NERVE_HEALTH_JSON" node -e 'const p=JSON.parse(process.env.VENICE_NERVE_HEALTH_JSON);if(!p.ok||p.service!=="venice-nerve"||p.apiVersion!=="home-center.venice-nerve-api.v1"||p.contractVersion!=="venice-nerve-silk.transport.v1"||p.fileLayer!=="drive_sync"||!Array.isArray(p.capabilities)||!p.capabilities.includes("venice.turn"))throw new Error("venice nerve deployment health mismatch");console.log(JSON.stringify(p))'
HOME_CENTER_MCP_URL="https://${REGION}-${PROJECT}.cloudfunctions.net/homeCenterMcp/mcp" HOME_CENTER_EXPECTED_SOURCE_COMMIT="$HEAD_SHA" node "$ROOT/tools/home_center_production_catalog_test.mjs"
if gcloud functions describe foundryAssetWorker --gen2 --project="$PROJECT" --region="$REGION" >/dev/null 2>&1; then gcloud functions delete foundryAssetWorker --gen2 --project="$PROJECT" --region="$REGION" --quiet; fi
if gcloud tasks queues describe "$OLD_QUEUE" --project="$PROJECT" --location="$REGION" >/dev/null 2>&1; then gcloud tasks queues delete "$OLD_QUEUE" --project="$PROJECT" --location="$REGION" --quiet; fi
node "$ROOT/tools/publish_foundry_retirement_record.mjs" "$PROJECT" "$REGION" "$HEAD_SHA" "$BLENDER_WORKSPACE_TASK_URL"
