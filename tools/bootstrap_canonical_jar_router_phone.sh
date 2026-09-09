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

# Live canary: this is not the mocked contract. It fresh-reads the canonical Drive
# registry, resolves the voice transcription, fresh-reads the exact Pasta'Fahr Sheet,
# and captures the existing typed context-use receipt before returning the packet.
python3 - "$CANARY_JSON" "$REGISTRY_ID" "$PASTA_ID" <<'PY'
import hashlib,json,sys
from pathlib import Path
from judgment_jar_task_router import task_source_packet

out,registry_id,pasta_id=sys.argv[1:]
packet=task_source_packet("Pasta apostrophe far. What does he actually judge?")
required=[
    f"REGISTRY_FILE_ID: {registry_id}",
    f"SOURCE_FILE_ID: {pasta_id}",
    "Which strands are living lineage",
    "Trace the noodle",
]
missing=[value for value in required if value not in packet]
if missing:
    raise SystemExit("LIVE_CANARY_FAILED missing="+json.dumps(missing))
if "Pastafarian" in packet or "apostasy doctrine" in packet.lower():
    raise SystemExit("LIVE_CANARY_FAILED hallucinated doctrine leaked into canonical packet")
obj={
    "schema":"canonical-jar-router-live-canary.v1",
    "ok":True,
    "input":"Pasta apostrophe far. What does he actually judge?",
    "canonicalRegistryFileId":registry_id,
    "canonicalJarFileId":pasta_id,
    "packetSha256":hashlib.sha256(packet.encode()).hexdigest(),
    "actualJudgmentRecovered":True,
    "actualCompactLawRecovered":True,
    "pastafarianRejected":True,
}
Path(out).write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(obj,sort_keys=True))
PY

# Push the canary's already-captured typed Jar receipt through the existing Home
# Center heartbeat path, then verify the exact fingerprint by reading the remote ledger.
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

python3 tools/judgment_jars.py flush-receipts >/dev/null

python3 - "$FINGERPRINT" "$INSTALL_RECEIPT" "$CANARY_JSON" "$RECEIPT" "$EXPECTED" "$REGISTRY_ID" "$PASTA_ID" <<'PY'
import json,sys,time
from pathlib import Path
from home_center_mcp_client import HomeCenterMcp

fingerprint,install_path,canary_path,out_path,commit,registry_id,pasta_id=sys.argv[1:]
state=Path.home()/'.local/state/home-center/vlad-swarm/judgment-jar-receipts/home-center-ledger.json'
if not state.is_file():
    raise SystemExit('BLOCKED: Home Center receipt ledger identity is unavailable after flush')
ledger=json.loads(state.read_text(encoding='utf-8'))
file_id=str(ledger.get('fileId') or '')
title=str(ledger.get('title') or 'Judgment Jar Usage Receipts — Vlad and Home Center')
if not file_id:
    raise SystemExit('BLOCKED: Home Center receipt ledger has no file ID')
remote=HomeCenterMcp().read_document(file_id,title)
marker='judgmentJarReceiptFingerprint: '+fingerprint
if marker not in remote:
    raise SystemExit('BLOCKED: Home Center remote receipt readback failed')
install=json.loads(Path(install_path).read_text(encoding='utf-8'))
canary=json.loads(Path(canary_path).read_text(encoding='utf-8'))
if install.get('ok') is not True or install.get('canonicalTaskJarRouting') is not True:
    raise SystemExit('BLOCKED: installed Adam receipt does not prove canonical task Jar routing')
obj={
    'schema':'canonical-jar-router-phone-deployment.v1',
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
