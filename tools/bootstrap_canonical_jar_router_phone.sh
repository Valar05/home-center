#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO="Valar05/home-center"
STATE="${HC_STATE_DIR:-$HOME/.local/state/home-center}/canonical-jar-router"
SOURCE="$STATE/source"
PART="$STATE/source.part"
RECEIPT="$STATE/deployment-receipt.json"
CANARY_JSON="$STATE/live-pastafahr-canary.json"
INSTALL_RECEIPT="${HC_STATE_DIR:-$HOME/.local/state/home-center}/adam-cli-install-receipt.json"
JAR_RECEIPT_STATE="${HC_JUDGMENT_JARS_RECEIPT_STATE_DIR:-$HOME/.local/state/home-center/vlad-swarm/judgment-jar-receipts}"
REGISTRY_ID="1UixBuLJRw-x5BoMGx81YXRpuN66iZhGGJoz40Iqx48Q"
PASTA_ID="1VlPlNiiRBW5KSI9Bb3zryWTDRkNRahfQkvlFV7er_KE"

mkdir -p "$STATE"
for cmd in gh git python3; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "BLOCKED: required command missing: $cmd" >&2; exit 2; }
done

gh auth status >/dev/null 2>&1 || { echo "BLOCKED: GitHub CLI is not authenticated." >&2; exit 3; }
EXPECTED="$(gh api "repos/$REPO/commits/main" --jq .sha)"
[ -n "$EXPECTED" ] || { echo "BLOCKED: could not resolve remote main commit." >&2; exit 4; }

if [ -d "$SOURCE/.git" ]; then
  REMOTE="$(git -C "$SOURCE" remote get-url origin 2>/dev/null || true)"
  case "$REMOTE" in
    *Valar05/home-center*) ;;
    *)
      STAMP="$(date +%Y%m%d-%H%M%S)"
      mv "$SOURCE" "$STATE/source.foreign.$STAMP"
      ;;
  esac
fi

if [ ! -d "$SOURCE/.git" ]; then
  rm -rf "$PART"
  GIT_LFS_SKIP_SMUDGE=1 gh repo clone "$REPO" "$PART" -- --depth 1 --branch main
  mv "$PART" "$SOURCE"
fi

GIT_LFS_SKIP_SMUDGE=1 git -C "$SOURCE" fetch --depth 1 origin "$EXPECTED"
git -C "$SOURCE" checkout --detach --force "$EXPECTED" >/dev/null
ACTUAL="$(git -C "$SOURCE" rev-parse HEAD)"
[ "$ACTUAL" = "$EXPECTED" ] || { echo "BLOCKED: source commit mismatch expected=$EXPECTED actual=$ACTUAL" >&2; exit 5; }

cd "$SOURCE"
python3 tools/test_judgment_jar_task_router.py
HC_REPO_ROOT="$SOURCE" bash tools/install_adam_cli.sh

# Live production canary. This imports the installed production launcher wiring.
# Planning must embed the freshly fetched canonical source. Execution is probed
# before model transport by replacing only its downstream executor with a witness
# that reads active_jars() while the real execution wrapper carries task context.
python3 - "$CANARY_JSON" "$REGISTRY_ID" "$PASTA_ID" <<'PY'
import hashlib,json,sys
from pathlib import Path
import adam_receipted_worker as production

out,registry_id,pasta_id=sys.argv[1:]
task="Pasta apostrophe far. What does he actually judge?"
required=[
    f"REGISTRY_FILE_ID: {registry_id}",
    f"SOURCE_FILE_ID: {pasta_id}",
    "Which strands are living lineage",
    "Trace the noodle",
]

def verify(label,text):
    missing=[value for value in required if value not in text]
    if missing:
        raise SystemExit(label+"_FAILED missing="+json.dumps(missing))
    if "Pastafarian" in text or "apostasy doctrine" in text.lower():
        raise SystemExit(label+"_FAILED hallucinated doctrine leaked into canonical packet")

planning=production.planning_system(task,Path.cwd())
verify("PLANNING_CANARY",planning)

observed={}
original=production._original_execution_run_task
def witness(received_task,*args,**kwargs):
    if received_task != task:
        raise SystemExit("EXECUTION_CANARY_FAILED task changed before execution")
    observed["packet"]=production.active_jars()
    return 0
production._original_execution_run_task=witness
try:
    rc=production.execution_run_task(task,Path.cwd())
finally:
    production._original_execution_run_task=original
if rc != 0:
    raise SystemExit("EXECUTION_CANARY_FAILED wrapper returned nonzero")
execution=observed.get("packet","")
verify("EXECUTION_CANARY",execution)

obj={
    "schema":"canonical-jar-router-live-canary.v2",
    "ok":True,
    "input":task,
    "canonicalRegistryFileId":registry_id,
    "canonicalJarFileId":pasta_id,
    "planningPacketSha256":hashlib.sha256(planning.encode()).hexdigest(),
    "executionPacketSha256":hashlib.sha256(execution.encode()).hexdigest(),
    "productionPlanningWiring":True,
    "productionExecutionWiring":True,
    "actualJudgmentRecovered":True,
    "actualCompactLawRecovered":True,
    "pastafarianRejected":True,
}
Path(out).write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(obj,sort_keys=True))
PY

LAST_CAPTURED="$JAR_RECEIPT_STATE/last-captured.json"
[ -f "$LAST_CAPTURED" ] || { echo "BLOCKED: live canary did not capture a Jar receipt." >&2; exit 6; }
FINGERPRINT="$(python3 - "$LAST_CAPTURED" "$PASTA_ID" <<'PY'
import json,sys
obj=json.load(open(sys.argv[1],encoding='utf-8'))
if obj.get('jar',{}).get('sourceFileId') != sys.argv[2]:
    raise SystemExit('last captured receipt is not the canonical Pasta\u2019Fahr Jar')
print(obj['dedupFingerprint'])
PY
)"

# Preserve the existing oldest-first outbox contract. Drain it through its existing
# primitive until this exact canary receipt is delivered. Historical quarantine or
# backoff remains a real blocker; this campaign does not route around it.
python3 - "$FINGERPRINT" "$INSTALL_RECEIPT" "$CANARY_JSON" "$RECEIPT" "$EXPECTED" "$REGISTRY_ID" "$PASTA_ID" <<'PY'
import json,sys,time
from pathlib import Path
from home_center_mcp_client import HomeCenterMcp
from judgment_jar_common import CONFIG_PATH, read_config
from judgment_jar_receipts import flush, paths

fingerprint,install_path,canary_path,out_path,commit,registry_id,pasta_id=sys.argv[1:]
config=read_config(CONFIG_PATH)
state=paths(config)

def delivered_receipt():
    directory=state['delivered']
    if not directory.is_dir():
        return None
    for path in directory.glob('*.json'):
        try:
            obj=json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            continue
        if obj.get('dedupFingerprint') == fingerprint:
            return obj
    return None

delivered=delivered_receipt()
last_flush=None
for _ in range(25):
    if delivered is not None:
        break
    last_flush=flush(config,limit=100)
    delivered=delivered_receipt()
    if delivered is not None:
        break
    blocked=(last_flush or {}).get('blocked')
    if blocked:
        raise SystemExit('BLOCKED: ordered Judgment Jar receipt outbox blocked before canary delivery: '+json.dumps(blocked,sort_keys=True))
if delivered is None:
    raise SystemExit('BLOCKED: canary receipt not delivered after bounded oldest-first outbox drain')

home=delivered.get('homeCenter') or {}
file_id=str(home.get('fileId') or '')
title=str(home.get('title') or 'Judgment Jar Usage Receipts — Vlad and Home Center')
if not file_id:
    raise SystemExit('BLOCKED: delivered canary receipt has no Home Center ledger file ID')
remote=HomeCenterMcp().read_document(file_id,title)
marker='judgmentJarReceiptFingerprint: '+fingerprint
if marker not in remote:
    raise SystemExit('BLOCKED: Home Center remote receipt readback failed')

install=json.loads(Path(install_path).read_text(encoding='utf-8'))
canary=json.loads(Path(canary_path).read_text(encoding='utf-8'))
if install.get('ok') is not True or install.get('canonicalTaskJarRouting') is not True:
    raise SystemExit('BLOCKED: installed Adam receipt does not prove canonical task Jar routing')
if canary.get('productionPlanningWiring') is not True or canary.get('productionExecutionWiring') is not True:
    raise SystemExit('BLOCKED: production planning/execution Jar canary did not pass')
obj={
    'schema':'canonical-jar-router-phone-deployment.v2',
    'ok':True,
    'sourceCommit':commit,
    'canonicalRegistryFileId':registry_id,
    'canonicalPastaFahrFileId':pasta_id,
    'productionLauncherInstalled':True,
    'planningCanonicalJarRouting':True,
    'executionCanonicalJarRouting':True,
    'jarUnresolvedFailsClosed':True,
    'liveDriveCanary':canary,
    'contextReceiptFingerprint':fingerprint,
    'homeCenterReceiptLedgerFileId':file_id,
    'homeCenterRemoteReceiptReadback':True,
    'installedAdamReceipt':str(Path(install_path)),
    'completedAtEpoch':int(time.time()),
}
Path(out_path).write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps(obj,indent=2,sort_keys=True))
PY

echo "HOME CENTER CANONICAL JUDGMENT JAR ROUTER FIXED"
echo "Receipt: $RECEIPT"
