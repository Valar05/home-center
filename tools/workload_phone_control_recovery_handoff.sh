#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

# Priority-0 Home Center phone-control handoff for an authorized workload carrier.
# Boundaries: Home Center only; no Shizuku/rish/ADB dependency; no Drew-as-transport;
# no GitHub Actions; no force-push; no completion claim without Home Center receipts.

PROJECT="${HC_GCP_PROJECT:-home-center-dclar}"
REGION="${HC_GCP_REGION:-us-central1}"
REPO_SLUG="Valar05/home-center"
PRIMARY="primary-phone"
RESCUE="primary-phone-rescue-v1"
RESCUE_SOURCE_SHA256="a18096e9affd54d0ac580de3bd5f329060164ec818f125096779d196e8cbff5d"
MAX_RETRIES="${HC_HANDOFF_RETRIES:-6}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
NONCE="phone-control-${STAMP}-$$"
ROOT="${HC_HOME_CENTER_REPO:-$(git rev-parse --show-toplevel 2>/dev/null || true)}"
WT=""
DEPLOY_SHA=""
URI=""

log(){ printf '[phone-control-workload] %s\n' "$*"; }
fail(){ printf 'HANDOFF_STATUS=BLOCKED\nBLOCKER=%s\nDETAIL=%s\n' "$1" "${2:-}" >&2; exit 1; }
cleanup(){ [ -n "$WT" ] && [ -n "$ROOT" ] && git -C "$ROOT" worktree remove --force "$WT" >/dev/null 2>&1 || true; }
trap cleanup EXIT INT TERM
for c in git python3 node npm gcloud curl; do command -v "$c" >/dev/null 2>&1 || fail missing_tool "$c"; done
[ -n "$ROOT" ] || fail repo_missing "Run from an authorized $REPO_SLUG checkout or set HC_HOME_CENTER_REPO."
case "$(git -C "$ROOT" remote get-url origin 2>/dev/null || true)" in *github.com[:/]Valar05/home-center.git|*github.com/Valar05/home-center) ;; *) fail wrong_repo "$ROOT";; esac
ACCOUNT="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' 2>/dev/null | head -n1 || true)"
[ -n "$ACCOUNT" ] || fail gcp_auth_missing "Workload must provide authorized gcloud credentials. Do not ask Drew for a key."
gcloud projects describe "$PROJECT" --format='value(projectId)' >/dev/null 2>&1 || fail gcp_project_unreachable "$PROJECT"

patch_and_test(){
python3 - <<'PY'
from pathlib import Path
p=Path('functions/phone_hands_relay.js'); s=p.read_text()
old="""  const now = Date.now();
  await devRef.set({lastSeenAtMs: now, status: 'online'}, {merge: true});
  const query = await admin.firestore().collection(COLLECTIONS.commands)
    .where('ownerKey','==',device.ownerKey).where('deviceId','==',id).where('status','==','queued').limit(10).get();
  const candidates = query.docs.map((d) => d.data()).filter((x) => Number(x.expiresAtMs || 0) > now).sort((a,b) => a.createdAtMs-b.createdAtMs);
  if (!candidates.length) return {ok: true, command: null};
  const chosen = candidates[0];
  const leaseOwner = `device:${id}`;
  await admin.firestore().collection(COLLECTIONS.commands).doc(chosen.commandId).set({status:'leased', leaseOwner, leaseExpiresAtMs: now + Math.max(5000, Math.min(Number(leaseMs), 120000)), updatedAtMs: now}, {merge:true});
  return {ok: true, command: {...chosen, status:'leased', leaseOwner}};
"""
new="""  const now = Date.now();
  await devRef.set({lastSeenAtMs: now, status: 'online'}, {merge: true});
  const PHONE_QUEUE_SCAN_LIMIT = 100;
  const PHONE_QUEUE_DRAIN_ROUNDS = 20;
  const commands = admin.firestore().collection(COLLECTIONS.commands);
  const leasedQuery = await commands
    .where('ownerKey','==',device.ownerKey).where('deviceId','==',id).where('status','==','leased')
    .limit(PHONE_QUEUE_SCAN_LIMIT).get();
  const staleLeases = leasedQuery.docs
    .map((doc)=>({...doc.data(),commandId:safeText((doc.data()||{}).commandId,180)||doc.id}))
    .filter((x)=>Number(x.leaseExpiresAtMs||0)>0 && Number(x.leaseExpiresAtMs||0)<=Date.now());
  if (staleLeases.length) {
    const batch=admin.firestore().batch(); const t=Date.now();
    for (const x of staleLeases) batch.set(commands.doc(x.commandId),{status:'failed',error:'lease_expired_before_completion',completedAtMs:t,updatedAtMs:t,leaseExpiresAtMs:0},{merge:true});
    await batch.commit();
  }
  let candidates=[];
  for (let round = 0; round < PHONE_QUEUE_DRAIN_ROUNDS; round += 1) {
    const scanNow=Date.now();
    const query=await commands.where('ownerKey','==',device.ownerKey).where('deviceId','==',id).where('status','==','queued').limit(PHONE_QUEUE_SCAN_LIMIT).get();
    const queued=query.docs.map((doc)=>({...doc.data(),commandId:safeText((doc.data()||{}).commandId,180)||doc.id})).sort((a,b)=>Number(a.createdAtMs||0)-Number(b.createdAtMs||0));
    if (!queued.length) break;
    const expired=queued.filter((x)=>Number(x.expiresAtMs||0)<=scanNow);
    if (expired.length) {
      const batch=admin.firestore().batch();
      for (const x of expired) batch.set(commands.doc(x.commandId),{status:'failed',error:'expired_before_lease',completedAtMs:scanNow,updatedAtMs:scanNow,leaseExpiresAtMs:0},{merge:true});
      await batch.commit();
    }
    candidates=queued.filter((x)=>Number(x.expiresAtMs||0)>scanNow);
    if (candidates.length || !expired.length) break;
  }
  if (!candidates.length) return {ok: true, command: null};
  const chosen=candidates.find((x)=>Number(x.expiresAtMs||0)>Date.now());
  if (!chosen) return {ok: true, command: null};
  const leaseOwner=`device:${id}`; const leaseNow=Date.now();
  await commands.doc(chosen.commandId).set({status:'leased',leaseOwner,leaseExpiresAtMs:leaseNow+Math.max(5000,Math.min(Number(leaseMs),120000)),updatedAtMs:leaseNow},{merge:true});
  return {ok:true,command:{...chosen,status:'leased',leaseOwner}};
"""
already=all(x in s for x in ['PHONE_QUEUE_SCAN_LIMIT = 100','PHONE_QUEUE_DRAIN_ROUNDS = 20',"error:'expired_before_lease'","error:'lease_expired_before_completion'"]) and '.limit(10).get()' not in s
if already: print('PATCH_ALREADY_PRESENT=1')
elif s.count(old)==1: p.write_text(s.replace(old,new)); print('PATCH_APPLIED=1')
else: raise SystemExit('BLOCKED: queue source changed; reviewed patch no longer applies exactly')
PY
if [ ! -f tools/phone_hands_queue_starvation_contract_test.mjs ]; then
cat > tools/phone_hands_queue_starvation_contract_test.mjs <<'JS'
import fs from 'node:fs'; import assert from 'node:assert/strict';
const s=fs.readFileSync('functions/phone_hands_relay.js','utf8');
assert.doesNotMatch(s,/where\('status','==','queued'\)\.limit\(10\)\.get\(\)/);
for (const x of ['PHONE_QUEUE_SCAN_LIMIT = 100','PHONE_QUEUE_DRAIN_ROUNDS = 20','expired_before_lease','lease_expired_before_completion']) assert.ok(s.includes(x),x);
assert.ok(s.includes('for (let round = 0; round < PHONE_QUEUE_DRAIN_ROUNDS; round += 1)'));
console.log('phone hands queue starvation contract: ok');
JS
fi
node --check functions/phone_hands_relay.js
node tools/phone_hands_queue_starvation_contract_test.mjs
node tools/phone_hands_relay_contract_test.mjs
npm --prefix functions ci
npm --prefix functions run test --if-present
}

prepare_source(){
  local n=1 base latest
  while [ "$n" -le "$MAX_RETRIES" ]; do
    log "SOURCE_ATTEMPT=$n/$MAX_RETRIES"
    git -C "$ROOT" fetch --quiet origin main; base="$(git -C "$ROOT" rev-parse origin/main)"
    [ -n "$WT" ] && git -C "$ROOT" worktree remove --force "$WT" >/dev/null 2>&1 || true
    WT="$(mktemp -d "${TMPDIR:-/tmp}/hc-phone-control.XXXXXX")"; rmdir "$WT"
    git -C "$ROOT" worktree add --detach "$WT" "$base" >/dev/null; cd "$WT"; patch_and_test
    if git diff --quiet -- functions/phone_hands_relay.js tools/phone_hands_queue_starvation_contract_test.mjs; then DEPLOY_SHA="$base"; return 0; fi
    git config user.name home-center-workload-repair; git config user.email home-center-workload-repair@users.noreply.github.com
    git add functions/phone_hands_relay.js tools/phone_hands_queue_starvation_contract_test.mjs
    git commit -m 'Fix Phone Hands queue starvation and stale leases [skip ci]' >/dev/null
    git -C "$ROOT" fetch --quiet origin main; latest="$(git -C "$ROOT" rev-parse origin/main)"
    if [ "$latest" = "$base" ] && git push origin HEAD:main >/dev/null 2>&1; then DEPLOY_SHA="$(git rev-parse HEAD)"; return 0; fi
    n=$((n+1))
  done
  fail main_too_hot "No force push attempted after $MAX_RETRIES races."
}

deploy(){
  cd "$WT"; local short state label body code
  short="$(printf '%s' "$DEPLOY_SHA"|cut -c1-12)"
  gcloud functions deploy phoneHandsRelay --gen2 --project="$PROJECT" --region="$REGION" --runtime=nodejs22 --source="$WT/functions" --entry-point=phoneHandsRelay --trigger-http --allow-unauthenticated --timeout=120s --update-labels="hc-source=$short,hc-repair=phone-queue-v2" --quiet >/dev/null
  state="$(gcloud functions describe phoneHandsRelay --gen2 --project="$PROJECT" --region="$REGION" --format='value(state)')"
  URI="$(gcloud functions describe phoneHandsRelay --gen2 --project="$PROJECT" --region="$REGION" --format='value(serviceConfig.uri)')"
  label="$(gcloud functions describe phoneHandsRelay --gen2 --project="$PROJECT" --region="$REGION" --format='value(labels.hc-source)')"
  [ "$state" = ACTIVE ] || fail deploy_state "$state"; [ "$label" = "$short" ] || fail deploy_sha_label "$label"
  body="$(mktemp)"; code="$(curl -sS -o "$body" -w '%{http_code}' -X POST -H 'Content-Type: application/json' -d '{}' "$URI/register" || true)"
  [ "$code" = 401 ] && grep -q 'missing bearer token' "$body" || { cat "$body" >&2; fail relay_auth_canary "HTTP $code"; }; rm -f "$body"
}

emit_handoff(){
  local out="${TMPDIR:-/tmp}/${NONCE}.json" rescue_id="${NONCE}-rescue" primary_id="${NONCE}-primary" retire_id="${NONCE}-retire"
  python3 - "$out" "$STAMP" "$DEPLOY_SHA" "$URI" "$RESCUE" "$RESCUE_SOURCE_SHA256" "$PRIMARY" "$rescue_id" "$primary_id" "$retire_id" <<'PY'
import json,sys
out,stamp,sha,uri,rescue,rescue_sha,primary,rid,pid,xid=sys.argv[1:]
can=lambda text:{'action':'phone_shell','command':f"printf '{text}\\n'; date +%s",'cwd':'/data/data/com.termux/files/home','timeoutSeconds':15}
cleanup='set -euo pipefail; r="$HOME/.local/state/home-center/rescue-relay/primary-phone-rescue-v1"; p="$(cat "$r/relay.pid" 2>/dev/null || true)"; [ -z "$p" ] && { printf "RESCUE_RETIRED=already_absent\\n"; exit 0; }; [ "$p" != "$$" ]; tr "\\0" "\\n" < "/proc/$p/environ" | grep -Fxq "HC_PHONE_DEVICE_ID=primary-phone-rescue-v1"; tr "\\0" "\\n" < "/proc/$p/environ" | grep -Fxq "HOME=$r/home"; kill "$p"; for i in 1 2 3 4 5 6 7 8 9 10; do kill -0 "$p" 2>/dev/null || break; sleep 1; done; ! kill -0 "$p" 2>/dev/null; rm -f "$r/home/.config/home-center/codex-hub.json" "$r/home/.config/home-center/phone-relay.json"; printf "RESCUE_RETIRED=1\\n"'
obj={'schema':'home-center.workload.phone-control-handoff.v1','createdAtUtc':stamp,'owner':'Drew','commission':'Restore reliable Home Center phone control without Shizuku as a dependency or Drew as command transport.','deployed':{'sourceSha':sha,'uri':uri,'shizukuRequired':False},'rescueProvenance':{'deviceId':rescue,'historicalSourceSha256':rescue_sha,'historicalPidTrusted':False},'nextCalls':[{'operation':'command_center.phone_hands.devices','args':{}},{'operation':'command_center.phone_hands.enqueue','args':{'idempotencyKey':rid,'deviceId':rescue,'commandId':rid,'ttlMs':120000,'action':can('HOME_CENTER_RESCUE_CANARY_V2')}},{'operation':'command_center.phone_hands.get','args':{'commandId':rid},'require':'completed exitCode=0 + rescue marker'},{'operation':'command_center.phone_hands.enqueue','args':{'idempotencyKey':pid,'deviceId':primary,'commandId':pid,'ttlMs':120000,'action':can('HOME_CENTER_PRIMARY_CANARY_V2')}},{'operation':'command_center.phone_hands.get','args':{'commandId':pid},'require':'completed exitCode=0 + primary marker'},{'operation':'command_center.phone_hands.enqueue','args':{'idempotencyKey':xid,'deviceId':primary,'commandId':xid,'ttlMs':120000,'action':{'action':'phone_shell','command':cleanup,'cwd':'/data/data/com.termux/files/home','timeoutSeconds':30}}},{'operation':'command_center.phone_hands.get','args':{'commandId':xid},'require':'completed exitCode=0 + RESCUE_RETIRED='},{'operation':'command_center.phone_hands.devices','args':{}}],'completion':'Only after both canaries complete and rescue retirement completes through Home Center.','stopRule':'If Home Center is absent or Resource not found, stop as WORKLOAD_INGRESS_BLOCKED. Do not bootstrap the phone again. Do not substitute another control plane.'}
open(out,'w').write(json.dumps(obj,indent=2,sort_keys=True)+'\n'); print(json.dumps(obj,indent=2,sort_keys=True))
PY
  RECEIPT="receipts/workload/${STAMP}-${NONCE}.json"
  if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    command -v base64 >/dev/null 2>&1 || fail missing_tool base64
    gh api --method PUT "repos/$REPO_SLUG/contents/$RECEIPT" -f message="Bind phone-control workload handoff $STAMP [skip ci]" -f branch=main -f content="$(base64 < "$out" | tr -d '\n')" >/dev/null || fail receipt_persist_failed "$RECEIPT"
    log "RECEIPT=$RECEIPT"
  else
    log "RECEIPT_LOCAL_ONLY=$out"
    log 'WORKLOAD_MUST_PERSIST_RECEIPT=1'
  fi
  printf 'HANDOFF_STATUS=AWAITING_HOME_CENTER_CANARIES\nDEPLOYED_SOURCE_SHA=%s\nNEXT=Execute nextCalls from the JSON above through Home Center; no new phone script.\n' "$DEPLOY_SHA"
}

prepare_source
deploy
emit_handoff
