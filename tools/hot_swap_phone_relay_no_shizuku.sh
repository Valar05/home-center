#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

TARGET_SHA="${HOME_CENTER_SOURCE_REF:-${1:-}}"
case "$TARGET_SHA" in
  [0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]*) ;;
  *) echo 'BLOCKED: HOME_CENTER_SOURCE_REF must be a commit SHA' >&2; exit 64 ;;
esac

export GIT_LFS_SKIP_SMUDGE=1
export GIT_CONFIG_COUNT=2
export GIT_CONFIG_KEY_0=filter.lfs.smudge
export GIT_CONFIG_VALUE_0='git-lfs smudge --skip -- %f'
export GIT_CONFIG_KEY_1=filter.lfs.process
export GIT_CONFIG_VALUE_1='git-lfs filter-process --skip'

STATE="$HOME/.local/state/home-center"
DEPLOY_STATE="$STATE/relay-hotswap"
SOURCE="$HOME/.local/share/home-center-phone-relay/source"
BIN="$HOME/bin"
PID_FILE="$STATE/phone-relay.pid"
LOG="$STATE/phone-relay.log"
mkdir -p "$DEPLOY_STATE" "$BIN" "$(dirname "$SOURCE")"

[ -f "$HOME/.config/home-center/codex-hub.json" ] || {
  echo 'BLOCKED: Home Center pairing config is missing.' >&2
  exit 2
}
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

python3 "$SOURCE/tools/test_phone_relay_shizuku_independence.py"
NEW_RELAY="$SOURCE/tools/android_phone_home_center_relay.py"
NEW_SHA="$(python3 - "$NEW_RELAY" <<'PY'
import hashlib,sys
print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())
PY
)"

cat > "$BIN/home-center-phone-relay" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec python '$NEW_RELAY' "\$@"
EOF
chmod 700 "$BIN/home-center-phone-relay"

OLD_PID=''
if [ -s "$PID_FILE" ]; then OLD_PID="$(cat "$PID_FILE" 2>/dev/null || true)"; fi
case "$OLD_PID" in (*[!0-9]*|'') OLD_PID='';; esac

RESTART="$DEPLOY_STATE/restart-${TARGET_SHA:0:12}.sh"
RECEIPT="$DEPLOY_STATE/latest.json"
cat > "$RESTART" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
set -u
sleep 8
OLD_PID='$OLD_PID'
PID_FILE='$PID_FILE'
LOG='$LOG'
RECEIPT='$RECEIPT'
TARGET_SHA='$TARGET_SHA'
NEW_SHA='$NEW_SHA'
HEARTBEAT='$STATE/phone-relay-heartbeat.json'
if [ -n "\$OLD_PID" ] && [ -r "/proc/\$OLD_PID/cmdline" ]; then
  if tr '\0' ' ' < "/proc/\$OLD_PID/cmdline" | grep -q 'android_phone_home_center_relay.py'; then
    kill "\$OLD_PID" 2>/dev/null || true
    for _ in 1 2 3 4 5 6 7 8 9 10; do
      kill -0 "\$OLD_PID" 2>/dev/null || break
      sleep 0.5
    done
  fi
fi
nohup '$BIN/home-center-phone-relay' >>"\$LOG" 2>&1 < /dev/null &
NEW_PID=\$!
printf '%s\n' "\$NEW_PID" > "\$PID_FILE"
OK=0
for _ in \$(seq 1 30); do
  if ! kill -0 "\$NEW_PID" 2>/dev/null; then break; fi
  if [ -s "\$HEARTBEAT" ] && python3 - "\$HEARTBEAT" "\$NEW_SHA" <<'PY' >/dev/null 2>&1
import json,sys
try:
    r=json.load(open(sys.argv[1],encoding='utf-8'))
except Exception:
    raise SystemExit(1)
raise SystemExit(0 if r.get('sourceSha256')==sys.argv[2] and r.get('baselineTransport')=='termux-no-shizuku' else 1)
PY
  then OK=1; break; fi
  sleep 1
done
python3 - "\$RECEIPT" "\$TARGET_SHA" "\$NEW_SHA" "\$OLD_PID" "\$NEW_PID" "\$OK" <<'PY'
import datetime,json,sys
path,target,source_hash,old_pid,new_pid,ok=sys.argv[1:]
obj={
  'schema':'home-center-phone-relay-hotswap.v1',
  'ok':ok=='1',
  'sourceCommit':target,
  'relaySourceSha256':source_hash,
  'oldPid':int(old_pid) if old_pid.isdigit() else None,
  'newPid':int(new_pid),
  'baselineTransport':'termux-no-shizuku',
  'shizukuRequired':False,
  'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
}
open(path,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n')
print(json.dumps(obj,sort_keys=True))
raise SystemExit(0 if obj['ok'] else 4)
PY
EOF
chmod 700 "$RESTART"
nohup bash "$RESTART" >>"$DEPLOY_STATE/restart.log" 2>&1 < /dev/null &

python3 - "$TARGET_SHA" "$NEW_SHA" "$OLD_PID" "$RESTART" <<'PY'
import json,sys
commit,source_hash,old_pid,restart=sys.argv[1:]
print(json.dumps({
  'schema':'home-center-phone-relay-hotswap-scheduled.v1',
  'ok':True,
  'sourceCommit':commit,
  'relaySourceSha256':source_hash,
  'oldPid':int(old_pid) if old_pid.isdigit() else None,
  'baselineTransport':'termux-no-shizuku',
  'shizukuRequired':False,
  'restartHelper':restart,
},sort_keys=True))
PY
