#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

# Bootstrap only. Its job is to find/authenticate the real home-center remote,
# install the stable vanguard-overlay command, canary the campaign machinery,
# start the isolated worker, and return Drew's shell. All continuing work belongs
# to the installed campaign; this script must not become a disposable repair chain.

BRANCH="campaign/vanguard-overlay-resurrection"
REPO_SLUG="Valar05/home-center"
STATE="${HC_VANGUARD_OVERLAY_STATE:-$HOME/.local/state/home-center/vanguard-overlay-resurrection}"
BOOT="$STATE/bootstrap"
SOURCE_FALLBACK="$STATE/source"
RECEIPT="$BOOT/bootstrap-receipt.json"
mkdir -p "$BOOT"

log() { printf '[vanguard-overlay bootstrap] %s\n' "$*" >&2; }
fail() {
  local code="$1" detail="$2"
  python3 - "$RECEIPT" "$detail" <<'PY'
import json,sys,time
path,detail=sys.argv[1:]
obj={"schema":"vanguard-overlay-bootstrap-v1","ok":False,"status":"BLOCKED","detail":detail,"atMs":int(time.time()*1000),"truthBoundary":"Bootstrap failure is not product failure and does not authorize a substitute execution lane."}
open(path,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n')
print(json.dumps(obj,indent=2,sort_keys=True))
PY
  exit "$code"
}

is_repo() {
  local dir="$1" remote
  [ -d "$dir" ] || return 1
  git -C "$dir" rev-parse --git-dir >/dev/null 2>&1 || return 1
  remote="$(git -C "$dir" remote get-url origin 2>/dev/null || true)"
  case "$remote" in
    *Valar05/home-center*) return 0 ;;
    *) return 1 ;;
  esac
}

find_repo() {
  local candidate probe parent
  for candidate in \
    "${HC_REPO_ROOT:-}" \
    "$PWD" \
    "$HOME/home-center" \
    "$HOME/src/home-center" \
    "$HOME/projects/home-center" \
    "$HOME/git/home-center" \
    "/storage/emulated/0/Documents/home-center" \
    "/storage/emulated/0/Documents/GitHub/home-center" \
    "$SOURCE_FALLBACK"
  do
    [ -n "$candidate" ] || continue
    probe="$candidate"
    while [ "$probe" != "/" ] && [ -n "$probe" ]; do
      if is_repo "$probe"; then printf '%s\n' "$probe"; return 0; fi
      parent="$(dirname "$probe")"
      [ "$parent" != "$probe" ] || break
      probe="$parent"
    done
  done
  return 1
}

REPO="$(find_repo || true)"
if [ -z "$REPO" ]; then
  log 'No existing authenticated checkout found; attempting non-interactive authenticated clone.'
  rm -rf "$SOURCE_FALLBACK.part" 2>/dev/null || true
  if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    gh repo clone "$REPO_SLUG" "$SOURCE_FALLBACK.part" -- --filter=blob:none >/dev/null 2>&1 || true
  fi
  if ! is_repo "$SOURCE_FALLBACK.part"; then
    rm -rf "$SOURCE_FALLBACK.part" 2>/dev/null || true
    GIT_TERMINAL_PROMPT=0 git clone --filter=blob:none "https://github.com/$REPO_SLUG.git" "$SOURCE_FALLBACK.part" >/dev/null 2>&1 || true
  fi
  if ! is_repo "$SOURCE_FALLBACK.part"; then
    rm -rf "$SOURCE_FALLBACK.part" 2>/dev/null || true
    GIT_TERMINAL_PROMPT=0 git clone --filter=blob:none "git@github.com:$REPO_SLUG.git" "$SOURCE_FALLBACK.part" >/dev/null 2>&1 || true
  fi
  if is_repo "$SOURCE_FALLBACK.part"; then
    rm -rf "$SOURCE_FALLBACK" 2>/dev/null || true
    mv "$SOURCE_FALLBACK.part" "$SOURCE_FALLBACK"
    REPO="$SOURCE_FALLBACK"
  fi
fi

[ -n "$REPO" ] && is_repo "$REPO" || fail 10 'AUTHENTICATED_HOME_CENTER_REPO_UNAVAILABLE: bootstrap could neither discover nor non-interactively clone Valar05/home-center.'

log "Using repository authority: $REPO"
GIT_TERMINAL_PROMPT=0 git -C "$REPO" fetch --prune origin "$BRANCH" || fail 11 'CAMPAIGN_BRANCH_FETCH_FAILED'
HEAD="$(git -C "$REPO" rev-parse "origin/$BRANCH")"
[ -n "$HEAD" ] || fail 12 'CAMPAIGN_BRANCH_HEAD_MISSING'

CAMPAIGN="$BOOT/vanguard_overlay_campaign.py"
CONTRACT="$BOOT/vanguard_overlay_campaign_contract_test.py"
git -C "$REPO" show "origin/$BRANCH:tools/vanguard_overlay_campaign.py" > "$CAMPAIGN.part" || fail 13 'CAMPAIGN_SCRIPT_FETCH_FAILED'
git -C "$REPO" show "origin/$BRANCH:tools/vanguard_overlay_campaign_contract_test.py" > "$CONTRACT.part" || fail 14 'CAMPAIGN_CONTRACT_FETCH_FAILED'
mv "$CAMPAIGN.part" "$CAMPAIGN"
mv "$CONTRACT.part" "$CONTRACT"
chmod 700 "$CAMPAIGN" "$CONTRACT"

SCRIPT_SHA="$(sha256sum "$CAMPAIGN" | awk '{print $1}')"
CONTRACT_SHA="$(sha256sum "$CONTRACT" | awk '{print $1}')"

log 'Running deterministic campaign source contract before installation.'
python3 "$CONTRACT" --campaign "$CAMPAIGN" || fail 15 'CAMPAIGN_SOURCE_CONTRACT_FAILED'

export HC_REPO_ROOT="$REPO"
export HC_VANGUARD_OVERLAY_STATE="$STATE"
log 'Installing stable vanguard-overlay control surface.'
python3 "$CAMPAIGN" install || fail 16 'STABLE_COMMAND_INSTALL_FAILED'

if [ -n "${PREFIX:-}" ] && [ -x "$PREFIX/bin/vanguard-overlay" ]; then
  COMMAND="$PREFIX/bin/vanguard-overlay"
elif [ -x "$HOME/bin/vanguard-overlay" ]; then
  COMMAND="$HOME/bin/vanguard-overlay"
else
  fail 17 'STABLE_COMMAND_NOT_FOUND_AFTER_INSTALL'
fi

log 'Canary-testing inert transport and out-of-band process-tree STOP.'
"$COMMAND" canary || fail 18 'CAMPAIGN_RUNTIME_CANARY_FAILED'

log 'Recording live lane diagnosis (diagnostic gaps do not authorize substitutes).'
"$COMMAND" doctor > "$BOOT/doctor.json" || true

log 'Starting/resuming isolated campaign worker.'
"$COMMAND" resume || fail 19 'CAMPAIGN_WORKER_LAUNCH_FAILED'
"$COMMAND" status > "$BOOT/status.json" || true

python3 - "$RECEIPT" "$REPO" "$HEAD" "$SCRIPT_SHA" "$CONTRACT_SHA" "$COMMAND" <<'PY'
import json,sys,time
path,repo,head,script_sha,contract_sha,command=sys.argv[1:]
obj={
  "schema":"vanguard-overlay-bootstrap-v1",
  "ok":True,
  "status":"CAMPAIGN_RUNNING",
  "atMs":int(time.time()*1000),
  "repository":repo,
  "branch":"campaign/vanguard-overlay-resurrection",
  "branchHead":head,
  "campaignScriptSha256":script_sha,
  "campaignContractSha256":contract_sha,
  "stableCommand":command,
  "processIsolationCanary":"PASS",
  "promptTransportCanary":"PASS",
  "workerLaunch":"PASS",
  "truthBoundary":"This proves bootstrap/campaign installation and worker launch on this body. It does not prove overlay source implementation, Android build, phone deployment, microphone activity, transcription, KEEP, or Drew acceptance."
}
open(path,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n')
print(json.dumps(obj,indent=2,sort_keys=True))
PY

printf '\nVANGUARD OVERLAY CAMPAIGN IS RUNNING\n'
printf '  status:   %s status\n' "$COMMAND"
printf '  follow:   %s follow\n' "$COMMAND"
printf '  stop:     %s stop\n' "$COMMAND"
printf '  resume:   %s resume\n' "$COMMAND"
printf '  receipts: %s receipts\n' "$COMMAND"
printf '  state:    %s\n' "$STATE"
