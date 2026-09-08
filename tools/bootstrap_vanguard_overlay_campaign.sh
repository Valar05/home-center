#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

# Primary-phone bootstrap for VANGUARD // OVERLAY RESURRECTION.
#
# This script does not implement the overlay. It installs/canaries the durable phone
# runner, which coordinates with THECAULDRON through the GitHub PR mailbox and owns
# phone build/Shizuku/live evidence. It returns Drew's shell immediately after the
# isolated campaign worker is launched.

BRANCH="campaign/vanguard-overlay-resurrection"
REPO_SLUG="Valar05/home-center"
STATE="${HC_VANGUARD_OVERLAY_STATE:-$HOME/.local/state/home-center/vanguard-overlay-resurrection}"
BOOT="$STATE/bootstrap"
SHADOW="$BOOT/shadow"
SOURCE_FALLBACK="$STATE/source"
RECEIPT="$BOOT/bootstrap-receipt.json"
mkdir -p "$BOOT" "$SHADOW/tools" "$SHADOW/campaigns/vanguard-overlay-resurrection"

log() { printf '[vanguard-overlay bootstrap] %s\n' "$*" >&2; }
fail() {
  local code="$1" detail="$2"
  python3 - "$RECEIPT" "$detail" <<'PY'
import json,sys,time
path,detail=sys.argv[1:]
obj={
  "schema":"vanguard-overlay-phone-bootstrap-v2",
  "ok":False,
  "status":"BLOCKED",
  "detail":detail,
  "atMs":int(time.time()*1000),
  "truthBoundary":"Bootstrap failure is not Android product failure and does not authorize an adjacent execution lane."
}
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

[ -n "$REPO" ] && is_repo "$REPO" || fail 10 'AUTHENTICATED_HOME_CENTER_REPO_UNAVAILABLE: could neither discover nor non-interactively clone Valar05/home-center.'

log "Using repository authority: $REPO"
GIT_TERMINAL_PROMPT=0 git -C "$REPO" fetch --prune origin "$BRANCH" || fail 11 'CAMPAIGN_BRANCH_FETCH_FAILED'
HEAD="$(git -C "$REPO" rev-parse "origin/$BRANCH")"
[ -n "$HEAD" ] || fail 12 'CAMPAIGN_BRANCH_HEAD_MISSING'

copy_remote() {
  local rel="$1" dest="$2" code="$3"
  mkdir -p "$(dirname "$dest")"
  git -C "$REPO" show "origin/$BRANCH:$rel" > "$dest.part" || fail "$code" "REMOTE_FILE_FETCH_FAILED:$rel"
  mv "$dest.part" "$dest"
}

CORE="$SHADOW/tools/vanguard_overlay_campaign.py"
PHONE="$SHADOW/tools/vanguard_overlay_phone_campaign.py"
CORE_CONTRACT="$SHADOW/tools/vanguard_overlay_campaign_contract_test.py"
PHONE_CONTRACT="$SHADOW/tools/vanguard_overlay_phone_campaign_contract_test.py"
DESKTOP="$SHADOW/tools/vanguard_overlay_throne_campaign.ps1"
PROTOCOL="$SHADOW/campaigns/vanguard-overlay-resurrection/PHONE_CANARY_PROTOCOL.md"

copy_remote 'tools/vanguard_overlay_campaign.py' "$CORE" 13
copy_remote 'tools/vanguard_overlay_phone_campaign.py' "$PHONE" 14
copy_remote 'tools/vanguard_overlay_campaign_contract_test.py' "$CORE_CONTRACT" 15
copy_remote 'tools/vanguard_overlay_phone_campaign_contract_test.py' "$PHONE_CONTRACT" 16
copy_remote 'tools/vanguard_overlay_throne_campaign.ps1' "$DESKTOP" 17
copy_remote 'campaigns/vanguard-overlay-resurrection/PHONE_CANARY_PROTOCOL.md' "$PROTOCOL" 18
chmod 700 "$CORE" "$PHONE" "$CORE_CONTRACT" "$PHONE_CONTRACT"

CORE_SHA="$(sha256sum "$CORE" | awk '{print $1}')"
PHONE_SHA="$(sha256sum "$PHONE" | awk '{print $1}')"
CORE_CONTRACT_SHA="$(sha256sum "$CORE_CONTRACT" | awk '{print $1}')"
PHONE_CONTRACT_SHA="$(sha256sum "$PHONE_CONTRACT" | awk '{print $1}')"

log 'Running deterministic campaign-core source contract.'
python3 "$CORE_CONTRACT" --campaign "$CORE" || fail 20 'CAMPAIGN_CORE_SOURCE_CONTRACT_FAILED'

log 'Running deterministic cross-body phone/desktop topology contract.'
python3 "$PHONE_CONTRACT" --root "$SHADOW" || fail 21 'CROSS_BODY_CAMPAIGN_SOURCE_CONTRACT_FAILED'

export HC_REPO_ROOT="$REPO"
export HC_VANGUARD_OVERLAY_STATE="$STATE"
log 'Installing stable vanguard-overlay phone control surface.'
python3 "$PHONE" install || fail 22 'STABLE_COMMAND_INSTALL_FAILED'

if [ -n "${PREFIX:-}" ] && [ -x "$PREFIX/bin/vanguard-overlay" ]; then
  COMMAND="$PREFIX/bin/vanguard-overlay"
elif [ -x "$HOME/bin/vanguard-overlay" ]; then
  COMMAND="$HOME/bin/vanguard-overlay"
else
  fail 23 'STABLE_COMMAND_NOT_FOUND_AFTER_INSTALL'
fi

log 'Canary-testing inert transport and whole-process-tree STOP.'
"$COMMAND" canary || fail 24 'CAMPAIGN_RUNTIME_CANARY_FAILED'

log 'Recording live phone-body diagnosis. Missing bodies remain precise boundaries.'
"$COMMAND" doctor > "$BOOT/doctor.json" || true

log 'Starting/resuming isolated phone campaign worker.'
"$COMMAND" resume || fail 25 'CAMPAIGN_WORKER_LAUNCH_FAILED'
"$COMMAND" status > "$BOOT/status.json" || true

python3 - "$RECEIPT" "$REPO" "$HEAD" "$CORE_SHA" "$PHONE_SHA" "$CORE_CONTRACT_SHA" "$PHONE_CONTRACT_SHA" "$COMMAND" <<'PY'
import json,sys,time
path,repo,head,core_sha,phone_sha,core_contract_sha,phone_contract_sha,command=sys.argv[1:]
obj={
  "schema":"vanguard-overlay-phone-bootstrap-v2",
  "ok":True,
  "status":"PHONE_CAMPAIGN_RUNNING",
  "atMs":int(time.time()*1000),
  "repository":repo,
  "branch":"campaign/vanguard-overlay-resurrection",
  "branchHead":head,
  "campaignCoreSha256":core_sha,
  "phoneRunnerSha256":phone_sha,
  "campaignContractSha256":core_contract_sha,
  "crossBodyContractSha256":phone_contract_sha,
  "stableCommand":command,
  "processIsolationCanary":"PASS",
  "promptTransportCanary":"PASS",
  "workerLaunch":"PASS",
  "truthBoundary":"This proves phone bootstrap/campaign installation and worker launch on this body. It does not prove free-tab completion, Android implementation/build, overlay deployment, microphone activity, transcription, KEEP, or Drew acceptance."
}
open(path,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n')
print(json.dumps(obj,indent=2,sort_keys=True))
PY

printf '\nVANGUARD PHONE CAMPAIGN IS RUNNING\n'
printf '  status:   %s status\n' "$COMMAND"
printf '  follow:   %s follow\n' "$COMMAND"
printf '  stop:     %s stop\n' "$COMMAND"
printf '  resume:   %s resume\n' "$COMMAND"
printf '  receipts: %s receipts\n' "$COMMAND"
printf '  state:    %s\n' "$STATE"
printf '\nCross-body note: repair requests are durable PR #351 mailbox entries; THECAULDRON\n'
printf 'runner, not phone localhost, is responsible for actuating Chromium Throne.\n'
