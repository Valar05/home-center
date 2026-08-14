#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO="${HC_REPO:-Valar05/home-center}"
R="${HC_REPO_ROOT:-}"
STATE="$HOME/.local/state/home-center/bootstrap"
LOG="$STATE/bootstrap.log"
RECEIPT="$STATE/latest.json"
mkdir -p "$STATE"
: >"$LOG"

say(){ printf '%s\n' "$*" | tee -a "$LOG" >&2; }
write_receipt(){
  local ok="$1" stage="$2" detail="$3"
  python3 - "$RECEIPT" "$ok" "$stage" "$detail" "${R:-}" <<'PY'
import json,sys,time,os
p,ok,stage,detail,repo=sys.argv[1:]
obj={
  'schema':'adam-phone-bootstrap-v2',
  'ok':ok=='true',
  'stage':stage,
  'detail':detail,
  'repo':repo,
  'updatedAtEpoch':int(time.time()),
  'selfHeal':True,
  'lfsCheckoutRecovery':True,
}
t=p+'.tmp';open(t,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n');os.replace(t,p)
print(json.dumps(obj,sort_keys=True))
PY
}
fail(){ write_receipt false "$1" "$2" >/dev/null || true; say "BLOCKED[$1]: $2"; exit "${3:-1}"; }

ensure_base_tools(){
  command -v git >/dev/null 2>&1 || pkg install -y git >>"$LOG" 2>&1
  command -v python3 >/dev/null 2>&1 || pkg install -y python >>"$LOG" 2>&1
  command -v gh >/dev/null 2>&1 || pkg install -y gh >>"$LOG" 2>&1
}

find_repo(){
  if [ -n "$R" ] && [ -d "$R/.git" ]; then return 0; fi
  R=""
  local d
  for d in "$HOME/home-center" "$HOME/src/home-center" "$HOME/repos/home-center"; do
    if [ -d "$d/.git" ]; then R="$d"; return 0; fi
  done
  return 1
}

# The control-plane repository contains historical LFS evidence. Adam's phone
# bootstrap does not require those binary artifacts, so LFS must never be able
# to strand checkout before the self-healer is installed.
git_safe(){ GIT_LFS_SKIP_SMUDGE=1 git "$@"; }

recover_existing_checkout(){
  say "Recovering existing Home Center checkout without LFS smudge..."
  git_safe -C "$R" fetch --prune origin main >>"$LOG" 2>&1 || return 1
  # A failed initial clone commonly leaves HEAD populated but the worktree
  # half-checked-out. Re-materialize tracked control files while leaving LFS
  # pointers untouched instead of asking the operator to delete/reclone.
  git_safe -C "$R" reset --hard origin/main >>"$LOG" 2>&1 || return 1
  git_safe -C "$R" config --local filter.lfs.smudge "git-lfs smudge --skip -- %f" >>"$LOG" 2>&1 || true
  git_safe -C "$R" config --local filter.lfs.process "git-lfs filter-process --skip" >>"$LOG" 2>&1 || true
  return 0
}

clone_repo(){
  R="$HOME/home-center"
  say "Cloning Home Center with LFS smudge disabled..."
  rm -rf "$R.bootstrap-tmp"
  if GIT_LFS_SKIP_SMUDGE=1 gh repo clone "$REPO" "$R.bootstrap-tmp" >>"$LOG" 2>&1; then
    if [ -e "$R" ]; then rm -rf "$R"; fi
    mv "$R.bootstrap-tmp" "$R"
    return 0
  fi
  rm -rf "$R.bootstrap-tmp"
  return 1
}

install_and_verify(){
  [ -f "$R/tools/install_adam_prompt_phone.sh" ] || return 1
  bash "$R/tools/install_adam_prompt_phone.sh" >>"$LOG" 2>&1 || return 1
  hash -r
  command -v adam >/dev/null 2>&1 || return 1
  adam --help >>"$LOG" 2>&1 || return 1
  return 0
}

main(){
  ensure_base_tools
  if find_repo; then
    if ! recover_existing_checkout; then
      say "Existing checkout could not be repaired in place; replacing it safely."
      clone_repo || fail clone "could not obtain $REPO with LFS smudge disabled" 20
    fi
  else
    clone_repo || fail clone "could not obtain $REPO with LFS smudge disabled" 20
  fi

  install_and_verify || fail install "repository recovered, but Adam prompt installation/verification failed; see $LOG" 21
  write_receipt true ready "Home Center checkout repaired/updated; Adam installed and callable" >/dev/null
  say "READY: adam is installed. Bootstrap receipt: $RECEIPT"

  if [ "$#" -gt 0 ]; then
    adam "$@"
  fi
}

main "$@"
