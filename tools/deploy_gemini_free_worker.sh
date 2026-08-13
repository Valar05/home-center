#!/usr/bin/env bash
set -euo pipefail
ROOT="${HC_REPO_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"
PROJECT="${HC_GCP_PROJECT:-home-center-dclar}"
REGION="${HC_GEMINI_REGION:-us-central1}"
SERVICE="${HC_GEMINI_SERVICE:-home-center-gemini-free-worker}"
STATE="${HC_GEMINI_STATE:-$HOME/.local/state/home-center/gemini-worker}"
mkdir -p "$STATE"
command -v gcloud >/dev/null 2>&1 || { echo 'BLOCKED: gcloud CLI unavailable on this execution body.' >&2; exit 20; }

gcloud config set project "$PROJECT" >/dev/null
gcloud services enable run.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com >/dev/null
if ! gcloud secrets describe GEMINI_API_KEY >/dev/null 2>&1; then
  echo 'BLOCKED: Secret Manager secret GEMINI_API_KEY does not exist. Home Center already declares this secret; provision its value through the authorized secret lane.' >&2
  exit 21
fi

gcloud run deploy "$SERVICE" \
  --source "$ROOT/services/gemini-free-worker" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 2 \
  --cpu 1 \
  --memory 256Mi \
  --concurrency 20 \
  --timeout 120 \
  --set-secrets GEMINI_API_KEY=GEMINI_API_KEY:latest \
  --set-env-vars HC_GEMINI_MODEL="${HC_GEMINI_MODEL:-gemini-2.5-flash}" \
  --quiet
URL="$(gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)')"
[ -n "$URL" ] || { echo 'BLOCKED: Cloud Run deploy returned no service URL.' >&2; exit 22; }
HEALTH="$(curl -fsS "$URL/health")"
RUN="$(curl -fsS -H 'content-type: application/json' -d '{"prompt":"Return exactly: GEMINI_WORKER_OK","temperature":0}' "$URL/v1/run")"
python3 - "$STATE/deploy.json" "$URL" "$HEALTH" "$RUN" <<'PY'
import json,sys,time
path,url,health,run=sys.argv[1:]
h=json.loads(health); r=json.loads(run)
ok=bool(h.get('ok') and h.get('configured') and r.get('ok') and 'GEMINI_WORKER_OK' in str(r.get('text','')))
obj={'schema':'home-center.gemini-worker.deploy.v1','ok':ok,'url':url,'health':h,'canary':r,'sshRequired':False,'ipv6Required':False,'recordedAtEpoch':int(time.time())}
open(path,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n')
print(json.dumps(obj,indent=2,sort_keys=True))
raise SystemExit(0 if ok else 23)
PY
printf '%s\n' "$URL" > "$STATE/url"
