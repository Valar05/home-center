#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

# POCKET TTS KEEP // VANGUARD OVERLAY RESURRECTION
#
# This is the one operator-run bootstrap authorized for this campaign.
# Its first job is to return the Home Center phone relay to ChatGPT control.
# It then installs/resumes the durable Vanguard overlay campaign from the exact
# remote branch. It does not claim Pocket playback or overlay deployment merely
# because the bootstrap itself succeeds.
#
# IMPORTANT: this bootstrap never hydrates Git LFS payloads. The control plane
# does not depend on historical art/evidence blobs, and a missing LFS object must
# never be allowed to block relay recovery again.

REPO_SLUG="Valar05/home-center"
CAMPAIGN_BRANCH="campaign/vanguard-overlay-resurrection"
STATE="${HC_POCKET_OVERLAY_STATE:-$HOME/.local/state/home-center/pocket-overlay-keep}"
RELAY_RUNTIME="$STATE/relay-runtime"
VANGUARD_BOOT="$STATE/vanguard-bootstrap.sh"
LOG="$STATE/bootstrap.log"
RECEIPT="$STATE/bootstrap-receipt.json"
mkdir -p "$STATE"

exec > >(tee -a "$LOG") 2>&1

say(){ printf '[pocket-overlay] %s\n' "$*"; }
fail(){
  local code="$1" detail="$2"
  python3 - "$RECEIPT" "$detail" <<'PY'
import json,sys,time
path,detail=sys.argv[1:]
obj={
  "schema":"home-center.pocket-overlay-bootstrap.v1",
  "ok":False,
  "status":"BLOCKED",
  "detail":detail,
  "atMs":int(time.time()*1000),
  "truthBoundary":"Bootstrap failure is not Pocket TTS failure and is not Android overlay product evidence. No adjacent execution lane is authorized."
}
open(path,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n')
print(json.dumps(obj,sort_keys=True))
PY
  exit "$code"
}

command -v git >/dev/null 2>&1 || fail 10 "git missing in Termux"
command -v python3 >/dev/null 2>&1 || fail 11 "python3 missing in Termux"
command -v tar >/dev/null 2>&1 || fail 12 "tar missing in Termux"
command -v sha256sum >/dev/null 2>&1 || fail 13 "sha256sum missing in Termux"

is_repo(){
  local dir="$1" remote
  [ -d "$dir" ] || return 1
  git -C "$dir" rev-parse --git-dir >/dev/null 2>&1 || return 1
  remote="$(git -C "$dir" remote get-url origin 2>/dev/null || true)"
  case "$remote" in
    *Valar05/home-center*) return 0 ;;
    *) return 1 ;;
  esac
}

find_repo(){
  local candidate probe parent
  for candidate in \
    "${HC_REPO_ROOT:-}" \
    "$PWD" \
    "$HOME/home-center" \
    "$HOME/src/home-center" \
    "$HOME/projects/home-center" \
    "$HOME/git/home-center" \
    "/storage/emulated/0/Documents/GodotProjects/home-center" \
    "/storage/emulated/0/Documents/home-center" \
    "/storage/emulated/0/Documents/GitHub/home-center"
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
  command -v gh >/dev/null 2>&1 || fail 14 "AUTHENTICATED_HOME_CENTER_REPO_UNAVAILABLE: no checkout found and gh is unavailable"
  gh auth status >/dev/null 2>&1 || fail 15 "AUTHENTICATED_HOME_CENTER_REPO_UNAVAILABLE: no checkout found and gh is not authenticated"
  CLONE="$STATE/source"
  if ! is_repo "$CLONE"; then
    rm -rf "$CLONE.part" 2>/dev/null || true
    say "No checkout found; cloning the private Home Center source into campaign state without Git LFS hydration."
    GIT_LFS_SKIP_SMUDGE=1 gh repo clone "$REPO_SLUG" "$CLONE.part" -- --filter=blob:none || fail 16 "Home Center clone failed"
    if command -v git-lfs >/dev/null 2>&1 || git lfs version >/dev/null 2>&1; then
      git -C "$CLONE.part" lfs install --local --skip-smudge >/dev/null 2>&1 || true
    fi
    rm -rf "$CLONE" 2>/dev/null || true
    mv "$CLONE.part" "$CLONE"
  fi
  REPO="$CLONE"
fi
is_repo "$REPO" || fail 17 "Resolved Home Center path is not the authorized repository"

say "Repository authority: $REPO"
GIT_TERMINAL_PROMPT=0 git -C "$REPO" fetch --prune origin \
  '+refs/heads/main:refs/remotes/origin/main' \
  '+refs/heads/campaign/vanguard-overlay-resurrection:refs/remotes/origin/campaign/vanguard-overlay-resurrection' \
  || fail 18 "Git fetch failed"
MAIN_SHA="$(git -C "$REPO" rev-parse origin/main)"
CAMPAIGN_SHA="$(git -C "$REPO" rev-parse "origin/$CAMPAIGN_BRANCH")"
say "Remote main: $MAIN_SHA"
say "Vanguard branch: $CAMPAIGN_SHA"

# Build a clean relay runtime from reviewed remote main without checking out,
# resetting, or overwriting Drew's working tree. This prevents the relay itself
# from depending on a dirty/stale checkout.
rm -rf "$RELAY_RUNTIME.part"
mkdir -p "$RELAY_RUNTIME.part"
git -C "$REPO" archive --format=tar "$MAIN_SHA" | tar -xf - -C "$RELAY_RUNTIME.part" || fail 20 "Could not materialize reviewed Home Center relay runtime"
[ -f "$RELAY_RUNTIME.part/tools/android_phone_home_center_relay.py" ] || fail 21 "Reviewed relay source missing from main"
rm -rf "$RELAY_RUNTIME"
mv "$RELAY_RUNTIME.part" "$RELAY_RUNTIME"
RELAY_SHA="$(sha256sum "$RELAY_RUNTIME/tools/android_phone_home_center_relay.py" | awk '{print $1}')"
say "Relay source SHA-256: $RELAY_SHA"

PAIR="$HOME/.config/home-center/codex-hub.json"
[ -s "$PAIR" ] || fail 22 "Home Center Termux pairing config is missing: $PAIR"

RELAY_STATE="$HOME/.local/state/home-center"
RELAY_LOG="$STATE/phone-relay.log"
RELAY_PID="$RELAY_STATE/phone-relay.pid"
mkdir -p "$HOME/bin" "$RELAY_STATE"
cat > "$HOME/bin/home-center-phone-relay" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec python3 '$RELAY_RUNTIME/tools/android_phone_home_center_relay.py' "\$@"
EOF
chmod 700 "$HOME/bin/home-center-phone-relay"

# Stop only known relay processes. Do not touch SSH, Shizuku, overlays, tmux,
# Android UI, or unrelated Termux processes.
if [ -f "$RELAY_PID" ]; then
  OLD_PID="$(cat "$RELAY_PID" 2>/dev/null || true)"
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    kill "$OLD_PID" 2>/dev/null || true
    for _ in 1 2 3 4 5; do kill -0 "$OLD_PID" 2>/dev/null || break; sleep 1; done
  fi
fi
for PID in $(pgrep -f '[a]ndroid_phone_home_center_relay.py' 2>/dev/null || true); do
  kill "$PID" 2>/dev/null || true
done
sleep 1

# This log is campaign-owned and starts empty, so startup proof cannot be
# accidentally satisfied by an old "online" line from a previous relay.
: > "$RELAY_LOG"
say "Starting reviewed Home Center phone relay."
nohup "$HOME/bin/home-center-phone-relay" >>"$RELAY_LOG" 2>&1 </dev/null &
NEW_PID=$!
printf '%s\n' "$NEW_PID" > "$RELAY_PID"

RELAY_READY=false
for _ in $(seq 1 25); do
  if ! kill -0 "$NEW_PID" 2>/dev/null; then
    tail -n 80 "$RELAY_LOG" || true
    fail 23 "Home Center relay exited during startup"
  fi
  if grep -q 'Home Center phone relay online: primary-phone' "$RELAY_LOG" 2>/dev/null; then
    RELAY_READY=true
    break
  fi
  sleep 1
done
[ "$RELAY_READY" = true ] || { tail -n 80 "$RELAY_LOG" || true; fail 24 "Relay process stayed alive but never reported primary-phone online"; }
say "HOME CENTER RELAY: ONLINE pid=$NEW_PID"

# Doctor is useful evidence but is deliberately non-fatal here. Once the relay
# is back, ChatGPT owns repair of a failing Pocket boundary through Home Center.
DOCTOR_FILE="$STATE/pocket-doctor.json"
DOCTOR_RC=127
if command -v fortress-read >/dev/null 2>&1; then
  set +e
  fortress-read --doctor >"$DOCTOR_FILE" 2>&1
  DOCTOR_RC=$?
  set -e
elif [ -f "$RELAY_RUNTIME/tools/fortress_read_aloud.py" ]; then
  set +e
  python3 "$RELAY_RUNTIME/tools/fortress_read_aloud.py" --doctor >"$DOCTOR_FILE" 2>&1
  DOCTOR_RC=$?
  set -e
else
  printf '%s\n' '{"ok":false,"blockedReason":"fortress-read source unavailable"}' > "$DOCTOR_FILE"
fi
say "Pocket doctor exit: $DOCTOR_RC (non-fatal; receipt at $DOCTOR_FILE)"

# Install/resume the already-commissioned Vanguard overlay campaign from the
# exact remote branch. Its own evidence vocabulary stays strict; a running
# campaign is not an Android-deployed claim.
git -C "$REPO" show "$CAMPAIGN_SHA:tools/bootstrap_vanguard_overlay_campaign.sh" > "$VANGUARD_BOOT" || fail 30 "Vanguard bootstrap missing from campaign branch"
chmod 700 "$VANGUARD_BOOT"
set +e
(
  cd "$REPO"
  HC_REPO_ROOT="$REPO" bash "$VANGUARD_BOOT"
)
VANGUARD_RC=$?
set -e
say "Vanguard bootstrap exit: $VANGUARD_RC"

python3 - "$RECEIPT" "$REPO" "$MAIN_SHA" "$CAMPAIGN_SHA" "$RELAY_SHA" "$NEW_PID" "$DOCTOR_RC" "$VANGUARD_RC" <<'PY'
import json,sys,time
path,repo,main_sha,campaign_sha,relay_sha,pid,doctor_rc,vanguard_rc=sys.argv[1:]
obj={
  "schema":"home-center.pocket-overlay-bootstrap.v1",
  "ok":True,
  "status":"HOME_CENTER_CONTROL_RETURNED",
  "atMs":int(time.time()*1000),
  "repository":repo,
  "mainSha":main_sha,
  "campaignSha":campaign_sha,
  "relaySourceSha256":relay_sha,
  "relayPid":int(pid),
  "relayOnlineObserved":True,
  "pocketDoctorExitCode":int(doctor_rc),
  "vanguardBootstrapExitCode":int(vanguard_rc),
  "manualScriptBudgetConsumed":True,
  "nextAuthority":"ChatGPT -> Home Center -> Phone Hands -> primary-phone",
  "truthBoundary":"This proves the reviewed phone relay started and the Vanguard bootstrap was attempted from the exact remote branch. It does not prove Pocket playback, Android overlay deployment, microphone capture, transcription, KEEP, or Drew acceptance. Those now continue through Home Center without another manual script."
}
open(path,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n')
print(json.dumps(obj,indent=2,sort_keys=True))
PY

printf '\nHOME CENTER CONTROL RETURNED\n'
printf 'Receipt: %s\n' "$RECEIPT"
printf 'Do not run another repair script for this campaign. Continue in ChatGPT/Home Center.\n'
