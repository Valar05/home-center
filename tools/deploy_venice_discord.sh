#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"

PROJECT="${1:-home-center-dclar}"
REGION="${GCLOUD_FUNCTIONS_REGION:-us-central1}"
WARM_COST_APPROVAL="${2:-}"
EXPECTED_PROJECT="home-center-dclar"

if [ "$PROJECT" != "$EXPECTED_PROJECT" ]; then
  echo "Venice deployment is pinned to $EXPECTED_PROJECT; refusing project $PROJECT." >&2
  exit 2
fi

if [ "$WARM_COST_APPROVAL" != "--approve-warm-cost" ]; then
  echo "Venice keeps exactly one 512 MiB instance warm and is capped at one total instance." >&2
  echo "Run only after owner approval: sh tools/deploy_venice_discord.sh $PROJECT --approve-warm-cost" >&2
  exit 2
fi

git fetch origin main --quiet
HEAD_SHA="$(git rev-parse HEAD)"
MAIN_SHA="$(git rev-parse origin/main)"
if [ "$HEAD_SHA" != "$MAIN_SHA" ] || [ -n "$(git status --porcelain)" ]; then
  echo "Venice release requires a clean commit exactly matching origin/main." >&2
  exit 2
fi

sh tools/check_no_secrets.sh
node --test functions/venice_discord.test.js
node tools/generate_venice_worker_profile.mjs --check
node tools/worker_profile_contract_test.mjs

eval "$(node tools/worker_profile_contract.mjs shell venice-discord-interactions)"
node tools/worker_profile_contract.mjs validate-resolved venice-discord-interactions \
  "cpu=$WORKER_CPU" \
  "memory=$WORKER_MEMORY" \
  "concurrency=$WORKER_CONCURRENCY" \
  "minInstances=$WORKER_MIN_INSTANCES" \
  "maxInstances=$WORKER_MAX_INSTANCES" \
  "timeoutSeconds=$WORKER_TIMEOUT_SECONDS" \
  "serviceAccount=$WORKER_SERVICE_ACCOUNT"

SERVICE_ACCOUNT_ID="${WORKER_SERVICE_ACCOUNT%%@*}"

if ! gcloud secrets describe DISCORD_PUBLIC_KEY \
  --project "$PROJECT" \
  --no-log-http \
  --verbosity=error \
  --quiet >/dev/null; then
  echo "Required Venice public-key metadata is unavailable: DISCORD_PUBLIC_KEY" >&2
  exit 1
fi
if ! gcloud secrets describe OPENAI_API_KEY \
  --project "$PROJECT" \
  --no-log-http \
  --verbosity=error \
  --quiet >/dev/null; then
  echo "Required Venice generation secret metadata is unavailable: OPENAI_API_KEY" >&2
  exit 1
fi
if ! gcloud secrets describe VENICE_WEB_BRIDGE_TOKEN \
  --project "$PROJECT" \
  --no-log-http \
  --verbosity=error \
  --quiet >/dev/null; then
  echo "Required Venice web bridge secret metadata is unavailable: VENICE_WEB_BRIDGE_TOKEN" >&2
  exit 1
fi
if ! gcloud secrets describe GEMINI_API_KEY \
  --project "$PROJECT" \
  --no-log-http \
  --verbosity=error \
  --quiet >/dev/null; then
  echo "Required Venice fallback secret metadata is unavailable: GEMINI_API_KEY" >&2
  exit 1
fi
gcloud secrets versions access latest \
  --secret=DISCORD_PUBLIC_KEY \
  --project "$PROJECT" \
  --no-log-http \
  --verbosity=error \
  --quiet \
  | node -e '
const fs = require("fs");
const value = fs.readFileSync(0, "utf8").trim();
if (!/^[0-9a-f]{64}$/i.test(value)) {
  process.stderr.write("DISCORD_PUBLIC_KEY latest version is not a 32-byte hex verification key.\n");
  process.exit(1);
}
'
gcloud secrets versions access latest \
  --secret=VENICE_WEB_BRIDGE_TOKEN \
  --project "$PROJECT" \
  --no-log-http \
  --verbosity=error \
  --quiet \
  | node -e '
const fs = require("fs");
const value = fs.readFileSync(0, "utf8").trim();
if (value.length < 32) {
  process.stderr.write("VENICE_WEB_BRIDGE_TOKEN latest version is too short.\n");
  process.exit(1);
}
'

if ! gcloud iam service-accounts describe "$WORKER_SERVICE_ACCOUNT" \
  --project "$PROJECT" \
  --quiet >/dev/null 2>&1; then
  gcloud iam service-accounts create "$SERVICE_ACCOUNT_ID" \
    --display-name="Venice Discord interaction runtime" \
    --project "$PROJECT" \
    --quiet
fi

gcloud projects add-iam-policy-binding "$PROJECT" \
  --member="serviceAccount:$WORKER_SERVICE_ACCOUNT" \
  --role="roles/datastore.user" \
  --condition=None \
  --no-log-http \
  --verbosity=error \
  --quiet >/dev/null

gcloud projects add-iam-policy-binding "$PROJECT" \
  --member="serviceAccount:$WORKER_SERVICE_ACCOUNT" \
  --role="roles/cloudtasks.enqueuer" \
  --condition=None \
  --no-log-http \
  --verbosity=error \
  --quiet >/dev/null

gcloud iam service-accounts add-iam-policy-binding "$WORKER_SERVICE_ACCOUNT" \
  --member="serviceAccount:$WORKER_SERVICE_ACCOUNT" \
  --role="roles/iam.serviceAccountUser" \
  --project "$PROJECT" \
  --condition=None \
  --no-log-http \
  --verbosity=error \
  --quiet >/dev/null

gcloud secrets add-iam-policy-binding OPENAI_API_KEY \
  --member="serviceAccount:$WORKER_SERVICE_ACCOUNT" \
  --role="roles/secretmanager.secretAccessor" \
  --project "$PROJECT" \
  --condition=None \
  --no-log-http \
  --verbosity=error \
  --quiet >/dev/null

if gcloud tasks queues describe venice-discord-generation \
  --location "$REGION" \
  --project "$PROJECT" \
  --quiet >/dev/null 2>&1; then
  gcloud tasks queues update venice-discord-generation \
    --location "$REGION" \
    --project "$PROJECT" \
    --max-attempts=1 \
    --max-concurrent-dispatches=4 \
    --max-dispatches-per-second=4 \
    --quiet >/dev/null
else
  gcloud tasks queues create venice-discord-generation \
    --location "$REGION" \
    --project "$PROJECT" \
    --max-attempts=1 \
    --max-concurrent-dispatches=4 \
    --max-dispatches-per-second=4 \
    --quiet >/dev/null
fi

gcloud projects get-iam-policy "$PROJECT" \
  --format=json \
  --no-log-http \
  --verbosity=error \
  --quiet \
  | node -e '
const fs = require("fs");
const policy = JSON.parse(fs.readFileSync(0, "utf8"));
const expected = "serviceAccount:venice-discord-runtime@home-center-dclar.iam.gserviceaccount.com";
const granted = (policy.bindings || []).some((binding) =>
  binding.role === "roles/datastore.user"
  && !binding.condition
  && (binding.members || []).includes(expected));
if (!granted) {
  process.stderr.write("Dedicated Venice runtime is missing unconditional roles/datastore.user.\n");
  process.exit(1);
}
'

gcloud firestore fields ttls update expireAt \
  --collection-group=veniceDiscordAudit \
  --enable-ttl \
  --project "$PROJECT" \
  --quiet

TTL_POLICY_JSON="$(gcloud firestore fields ttls list \
  --collection-group=veniceDiscordAudit \
  --project "$PROJECT" \
  --format=json \
  --quiet)"
printf '%s' "$TTL_POLICY_JSON" | node -e '
const fs = require("fs");
const policies = JSON.parse(fs.readFileSync(0, "utf8"));
const suffix = "/collectionGroups/veniceDiscordAudit/fields/expireAt";
const active = policies.some((policy) => String(policy.name || "").endsWith(suffix) && policy.ttlConfig?.state === "ACTIVE");
if (!active) {
  process.stderr.write("Firestore TTL policy is not ACTIVE for veniceDiscordAudit.expireAt.\n");
  process.exit(1);
}
'

npm --prefix functions ci --ignore-scripts --no-audit --no-fund

# The shared Functions entrypoint can exceed Firebase's default 10-second
# discovery window on a cold Windows checkout. The owner-approved warm instance
# also requires Firebase's explicit billing acknowledgement.
export FUNCTIONS_DISCOVERY_TIMEOUT="${FUNCTIONS_DISCOVERY_TIMEOUT:-60}"
firebase deploy --only functions:veniceDiscordInteractions --project "$PROJECT" --force

SERVICE_NAME="$(gcloud functions describe veniceDiscordInteractions \
  --gen2 \
  --project "$PROJECT" \
  --region "$REGION" \
  --format='value(serviceConfig.service)' | sed 's#.*/##')"
if [ -z "$SERVICE_NAME" ]; then
  echo "Could not resolve the deployed Venice Cloud Run service." >&2
  exit 1
fi

gcloud run services describe "$SERVICE_NAME" \
  --project "$PROJECT" \
  --region "$REGION" \
  --format=json \
  | node tools/worker_profile_contract.mjs verify-live venice-discord-interactions
