#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

TARGET_SHA="${HOME_CENTER_SOURCE_REF:-${1:-}}"
if ! printf '%s' "$TARGET_SHA" | grep -Eq '^[0-9a-f]{40}$'; then
  echo 'BLOCKED: HOME_CENTER_SOURCE_REF must be a full 40-character commit SHA' >&2
  exit 64
fi
PROMPT="${IMPROPER_IMAGE_PROMPT:-educational anatomical study of an adult human hand, dorsal cutaway view, tendons bones and musculature, neutral medical atlas composition, anatomically grounded, no labels}"
SEED="${IMPROPER_IMAGE_SEED:-9092026}"
PROFILE="${IMPROPER_IMAGE_PROFILE:-plain}"
case "$PROFILE" in plain|fleshpunk) ;; *) echo 'BLOCKED: IMPROPER_IMAGE_PROFILE must be plain or fleshpunk' >&2; exit 64;; esac

export GIT_LFS_SKIP_SMUDGE=1
export GIT_CONFIG_COUNT=2
export GIT_CONFIG_KEY_0=filter.lfs.smudge
export GIT_CONFIG_VALUE_0='git-lfs smudge --skip -- %f'
export GIT_CONFIG_KEY_1=filter.lfs.process
export GIT_CONFIG_VALUE_1='git-lfs filter-process --skip'

STATE="$HOME/.local/state/home-center/improper-image-delivery"
SOURCE="$HOME/.local/share/home-center-improper-image/source"
DOC_REL='docs/IMPROPER_IMAGE_DELIVERY_CAMPAIGN.md'
RUN_LOG="$STATE/runtime-run.log"
FINAL="$STATE/runtime-final.json"
mkdir -p "$STATE" "$(dirname "$SOURCE")"
command -v gh >/dev/null 2>&1 || { echo 'BLOCKED: gh is unavailable on phone' >&2; exit 2; }
command -v git >/dev/null 2>&1 || { echo 'BLOCKED: git is unavailable on phone' >&2; exit 2; }

if [ ! -d "$SOURCE/.git" ]; then
  rm -rf "$SOURCE"
  gh repo clone Valar05/home-center "$SOURCE" -- --filter=blob:none --no-checkout
fi
cd "$SOURCE"
git fetch --no-tags origin "$TARGET_SHA"
git cat-file -e "$TARGET_SHA^{commit}"
git sparse-checkout set --cone tools
git checkout --detach --force "$TARGET_SHA"
mkdir -p "$SOURCE/docs"
git show "$TARGET_SHA:$DOC_REL" > "$SOURCE/$DOC_REL"

python3 "$SOURCE/tools/test_phone_relay_shizuku_independence.py" >"$STATE/shizuku-independence.stdout" 2>"$STATE/shizuku-independence.stderr"
python3 "$SOURCE/tools/test_improper_image_delivery_contract.py" >"$STATE/contract.stdout" 2>"$STATE/contract.stderr"

if ! bash "$SOURCE/tools/improper_image_delivery_campaign.sh" "$PROMPT" "$SEED" "$PROFILE" >"$RUN_LOG" 2>&1; then
  rc=$?
  echo "IMPROPER_IMAGE_CAMPAIGN REMOTE_BLOCKED exit=$rc" >&2
  tail -c 12000 "$RUN_LOG" >&2 || true
  exit "$rc"
fi

ACCEPT="$STATE/acceptance-latest.json"
[ -s "$ACCEPT" ] || { echo 'BLOCKED: accepted campaign produced no acceptance receipt' >&2; exit 5; }
python3 - "$ACCEPT" "$FINAL" "$TARGET_SHA" <<'PY'
import datetime,json,sys
accept_path,out_path,source_commit=sys.argv[1:]
r=json.load(open(accept_path,encoding='utf-8'))
cap=r.get('capabilityState') or {}
errors=[]
if not r.get('ok'): errors.append('acceptance ok=false')
if r.get('state')!='accepted_runtime_slice': errors.append(f"unexpected acceptance state {r.get('state')!r}")
if not r.get('promptId'): errors.append('missing ComfyUI promptId')
if not r.get('publicPhonePath','').startswith('/storage/emulated/0/Pictures/Fortress/'): errors.append('public phone path outside Pictures/Fortress')
if not r.get('pngSha256') or r.get('pngSha256')!=r.get('publicPhoneSha256'): errors.append('public PNG hash does not match accepted PNG hash')
if cap.get('shizukuRequired') is not False: errors.append('Shizuku independence not proven')
if cap.get('atomRequired') is not False: errors.append('Atom independence not proven')
if not cap.get('publicPicturesArtifactDelivered'): errors.append('public Pictures delivery not proven')
obj={
  'schema':'improper-image-runtime-final.v1',
  'ok':not errors,
  'sourceCommit':source_commit,
  'owner':'Home Center',
  'executionLane':'primary-phone background Termux relay',
  'renderer':'THECAULDRON localhost ComfyUI',
  'shizukuRequired':False,
  'atomRequired':False,
  'errors':errors,
  'acceptance':r,
  'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
}
open(out_path,'w',encoding='utf-8').write(json.dumps(obj,indent=2,ensure_ascii=False,sort_keys=True)+'\n')
print('IMPROPER_IMAGE_CAMPAIGN REMOTE_ACCEPTED' if obj['ok'] else 'IMPROPER_IMAGE_CAMPAIGN REMOTE_BLOCKED')
print(json.dumps(obj,ensure_ascii=False,sort_keys=True))
raise SystemExit(0 if obj['ok'] else 6)
PY
