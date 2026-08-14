#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO="${HC_REPO:-Valar05/home-center}"
R="${HC_REPO_ROOT:-}"
SAFE_ROOT="${HC_SAFE_REPO_ROOT:-$HOME/.local/share/home-center/runtime-source}"
STATE="$HOME/.local/state/home-center/bootstrap"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
LOG="$STATE/bootstrap-$RUN_ID.log"
RECEIPT="$STATE/latest.json"
USER_REPO=""
USER_DIRTY="unknown"
SOURCE_MODE=""
mkdir -p "$STATE"
: >"$LOG"

say(){ printf '%s\n' "$*" | tee -a "$LOG" >&2; }
git_safe(){ GIT_LFS_SKIP_SMUDGE=1 git "$@"; }

write_receipt(){
  local ok="$1" stage="$2" detail="$3" source_commit=""
  if [ -n "${R:-}" ] && [ -d "$R/.git" ]; then
    source_commit="$(git_safe -C "$R" rev-parse HEAD 2>/dev/null || true)"
  fi
  python3 - "$RECEIPT" "$ok" "$stage" "$detail" "${R:-}" "$USER_REPO" "$USER_DIRTY" "$SOURCE_MODE" "$source_commit" "$SAFE_ROOT" "$LOG" <<'PY'
import json,sys,time,os
(p,ok,stage,detail,repo,user_repo,user_dirty,source_mode,source_commit,safe_root,log)=sys.argv[1:]
if user_dirty == 'true':
    dirty_value = True
elif user_dirty == 'false':
    dirty_value = False
else:
    dirty_value = None
obj={
  'schema':'adam-phone-bootstrap-v3',
  'ok':ok=='true',
  'stage':stage,
  'detail':detail,
  'repo':repo,
  'sourceCommit':source_commit,
  'sourceMode':source_mode,
  'userCheckout':user_repo,
  'userCheckoutDirtyAtDiscovery':dirty_value,
  'preservedUserCheckout':bool(user_repo),
  'isolatedManagedSource':bool(repo and os.path.abspath(repo)==os.path.abspath(safe_root)),
  'destructiveUserResetUsed':False,
  'destructiveUserDeleteUsed':False,
  'log':log,
  'updatedAtEpoch':int(time.time()),
  'selfHeal':True,
  'lfsCheckoutRecovery':True,
}
t=p+'.tmp'
with open(t,'w',encoding='utf-8') as f:
    f.write(json.dumps(obj,indent=2,sort_keys=True)+'\n')
os.replace(t,p)
print(json.dumps(obj,sort_keys=True))
PY
}

fail(){ write_receipt false "$1" "$2" >/dev/null || true; say "BLOCKED[$1]: $2"; exit "${3:-1}"; }

ensure_package(){
  local command_name="$1" package_name="$2"
  command -v "$command_name" >/dev/null 2>&1 && return 0
  command -v pkg >/dev/null 2>&1 || fail prerequisites "missing $command_name and Termux pkg is unavailable" 10
  pkg install -y "$package_name" >>"$LOG" 2>&1 || fail prerequisites "could not install $package_name" 11
  command -v "$command_name" >/dev/null 2>&1 || fail prerequisites "$command_name is still unavailable after installing $package_name" 12
}

ensure_base_tools(){
  ensure_package git git
  ensure_package python3 python
  ensure_package gh gh
}

find_repo(){
  local requested="${HC_REPO_ROOT:-}" d
  if [ -n "$requested" ]; then
    USER_REPO="$requested"
    if [ -d "$requested/.git" ]; then R="$requested"; return 0; fi
    say "Explicit Home Center path is not a usable Git checkout; preserving it and using an isolated managed source."
    R=""
    return 1
  fi
  R=""
  for d in "$HOME/home-center" "$HOME/src/home-center" "$HOME/repos/home-center"; do
    if [ -d "$d/.git" ]; then
      R="$d"
      USER_REPO="$d"
      return 0
    fi
  done
  return 1
}

repo_dirty(){
  [ -n "$(git_safe -C "$1" status --porcelain=v1 --untracked-files=all 2>/dev/null || printf 'status-unavailable')" ]
}

repo_branch(){
  git_safe -C "$1" symbolic-ref --quiet --short HEAD 2>/dev/null || true
}

use_existing_checkout_if_safe(){
  local branch
  if repo_dirty "$R"; then
    USER_DIRTY="true"
    say "Preserving dirty Home Center checkout unchanged: $R"
    return 2
  fi
  USER_DIRTY="false"
  branch="$(repo_branch "$R")"
  if [ "$branch" != "main" ]; then
    say "Preserving clean non-main checkout unchanged (branch=${branch:-detached}): $R"
    return 2
  fi
  say "Fast-forwarding clean main checkout with LFS smudge disabled: $R"
  git_safe -C "$R" fetch --prune origin main >>"$LOG" 2>&1 || return 2
  git_safe -C "$R" merge --ff-only origin/main >>"$LOG" 2>&1 || return 2
  SOURCE_MODE="existing-clean-main-fast-forward"
  return 0
}

# Ownership evidence lives beside the managed checkout, never inside it, so the
# marker cannot dirty Git status or be mistaken for user-authored repository data.
managed_marker(){ printf '%s.managed' "$SAFE_ROOT"; }

quarantine_managed_source(){
  local reason="$1" marker destination destination_marker
  [ -e "$SAFE_ROOT" ] || return 0
  marker="$(managed_marker)"
  [ -f "$marker" ] || fail safe_source_collision "refusing to alter unmarked path $SAFE_ROOT" 30
  destination="$SAFE_ROOT.quarantine.$RUN_ID"
  destination_marker="$destination.managed"
  [ ! -e "$destination" ] && [ ! -e "$destination_marker" ] \
    || fail safe_source_collision "quarantine destination already exists: $destination" 31
  say "Preserving prior managed runtime source at $destination ($reason)."
  mv "$SAFE_ROOT" "$destination" || fail safe_source_quarantine "could not preserve $SAFE_ROOT at $destination" 32
  mv "$marker" "$destination_marker" \
    || fail safe_source_quarantine "managed source moved to $destination but its ownership marker could not be moved" 32
}

clone_managed_source(){
  local parent temp temp_marker marker
  parent="$(dirname "$SAFE_ROOT")"
  temp="$SAFE_ROOT.tmp.$RUN_ID"
  temp_marker="$temp.managed"
  marker="$(managed_marker)"
  mkdir -p "$parent"
  [ ! -e "$temp" ] && [ ! -e "$temp_marker" ] \
    || fail safe_source_collision "temporary managed source already exists: $temp" 33
  [ ! -e "$SAFE_ROOT" ] && [ ! -e "$marker" ] \
    || fail safe_source_collision "refusing to replace existing managed source path or marker: $SAFE_ROOT" 34
  say "Cloning isolated Home Center runtime source with LFS smudge disabled: $temp"
  GIT_LFS_SKIP_SMUDGE=1 gh repo clone "$REPO" "$temp" >>"$LOG" 2>&1 \
    || fail clone "could not obtain $REPO at isolated path $temp; partial path preserved" 20
  [ -d "$temp/.git" ] || fail clone "clone completed without a Git checkout at $temp" 21
  printf 'managed-by=tools/bootstrap_adam_phone.sh\ncreated=%s\n' "$RUN_ID" >"$temp_marker"
  mv "$temp" "$SAFE_ROOT" || fail clone "could not activate managed runtime source at $SAFE_ROOT" 22
  mv "$temp_marker" "$marker" \
    || fail clone "runtime source activated at $SAFE_ROOT but ownership marker activation failed" 23
  R="$SAFE_ROOT"
  SOURCE_MODE="isolated-managed-clone"
}

prepare_managed_source(){
  local branch marker
  marker="$(managed_marker)"
  if [ -e "$SAFE_ROOT" ] || [ -e "$marker" ]; then
    [ -d "$SAFE_ROOT/.git" ] && [ -f "$marker" ] \
      || fail safe_source_collision "managed source path/marker pair is incomplete; refusing to alter either: $SAFE_ROOT" 30
    branch="$(repo_branch "$SAFE_ROOT")"
    if repo_dirty "$SAFE_ROOT" || [ "$branch" != "main" ]; then
      quarantine_managed_source "dirty, detached, or non-main managed source"
      clone_managed_source
      return 0
    fi
    say "Fast-forwarding isolated managed runtime source: $SAFE_ROOT"
    if git_safe -C "$SAFE_ROOT" fetch --prune origin main >>"$LOG" 2>&1 \
      && git_safe -C "$SAFE_ROOT" merge --ff-only origin/main >>"$LOG" 2>&1; then
      R="$SAFE_ROOT"
      SOURCE_MODE="isolated-managed-fast-forward"
      return 0
    fi
    quarantine_managed_source "fast-forward failed"
  fi
  clone_managed_source
}

select_source(){
  if find_repo; then
    if use_existing_checkout_if_safe; then return 0; fi
  fi
  prepare_managed_source
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
  select_source
  install_and_verify || fail install "source selected without altering the user checkout, but Adam installation/verification failed; see $LOG" 40
  write_receipt true ready "Adam installed from a verified source while preserving any existing checkout" >/dev/null
  say "READY: adam is installed. Bootstrap receipt: $RECEIPT"

  if [ "$#" -gt 0 ]; then
    adam "$@"
  fi
}

main "$@"
