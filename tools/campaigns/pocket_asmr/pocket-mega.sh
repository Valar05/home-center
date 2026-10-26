#!/usr/bin/env bash
# Consolidated Pocket ASMR repair campaign. Termux -> existing cauldron -> CMD.
set -Eeuo pipefail
ACTION="${1:-repair}"
CAULDRON="${POCKET_CAULDRON_COMMAND:-cauldron}"
ROOT='C:\Users\dclar\PocketASMRGit'
BRANCH='campaign/pocket-asmr-queue-20261026'
SERVICE='C:\Users\dclar\PocketASMRGit\tools\campaigns\pocket_asmr\pocket-service.cmd'
TASK='Ritsu Pocket ASMR Gateway'
STEP=preflight
trap 'rc=$?; printf "POCKET_RESULT=FAILED STEP=%s EXIT=%s\n" "$STEP" "$rc" >&2' ERR
say(){ printf 'POCKET_%s=%s\n' "$1" "$2"; }
stop(){ say BLOCKED "$*"; exit 2; }
remote(){ "$CAULDRON" "cmd /d /c \"$1\""; }
preflight(){
 STEP=preflight
 command -v "$CAULDRON" >/dev/null || stop 'cauldron_missing'
 say TRANSPORT "$CAULDRON"
 "$CAULDRON" --doctor || stop 'cauldron_unreachable'
}
probe(){
 STEP=diagnostics
 remote "if exist $ROOT\.git (echo POCKET_GIT_PRESENT) else (echo POCKET_GIT_MISSING)"
 remote "if exist $SERVICE (echo POCKET_SERVICE_PRESENT) else (echo POCKET_SERVICE_MISSING)"
 remote "schtasks /query /tn \"$TASK\" /fo LIST /v" || true
 remote 'netstat -ano -p TCP' | grep -E ':10215[[:space:]]|:10205[[:space:]]' || true
}
sync_source(){
 STEP=fetch
 remote "if exist $ROOT\.git (exit /b 0) else (exit /b 30)" || stop 'missing_remote_git_checkout'
 remote "git -c safe.directory=C:/Users/dclar/PocketASMRGit -C $ROOT fetch origin $BRANCH" || stop 'fetch_failed'
 STEP=checkout
 # Only owned campaign files, never git reset, full checkout or unrelated LFS assets.
 remote "git -c safe.directory=C:/Users/dclar/PocketASMRGit -C $ROOT checkout FETCH_HEAD -- tools/campaigns/pocket_asmr/pocket-service.cmd tools/campaigns/pocket_asmr/asmr_api.py tools/campaigns/pocket_asmr/asmr.txt" || stop 'campaign_checkout_failed'
 remote "if exist $SERVICE (echo POCKET_SERVICE_FOUND) else (exit /b 31)" || stop 'service_missing'
}
install(){
 STEP=install
 remote "call $SERVICE install" || stop 'task_install_failed_or_permission_denied'
}
on(){
 STEP=start
 remote "call $SERVICE on" || stop 'task_start_failed'
}
off(){
 STEP=stop
 remote "call $SERVICE off" || stop 'task_stop_failed'
}
gateway_probe(){
 STEP=gateway
 remote 'curl.exe --noproxy "*" --connect-timeout 4 --max-time 8 -s -o NUL -w "GATEWAY_HTTP=%{http_code}" http://127.0.0.1:10215/asmr/health' || stop 'gateway_unreachable'
 say AUTHENTICATED_AUDIO NOT_YET_VERIFIED
 say PHONE_TUNNEL NOT_YET_CONFIGURED
}
case "$ACTION" in
 repair)
   preflight; sync_source; probe; install; on; probe; gateway_probe
   ;;
 sync)
   preflight; sync_source
   ;;
 status)
   preflight; probe
   ;;
 on)
   preflight; on; probe
   ;;
 off)
   preflight; off; probe
   ;;
 *)
   echo 'Usage: bash pocket-mega.sh repair|sync|status|on|off' >&2
   exit 2
   ;;
esac
