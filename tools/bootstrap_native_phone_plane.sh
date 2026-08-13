#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

SOURCE_HEAD="${1:-}"
[[ "$SOURCE_HEAD" =~ ^[0-9a-f]{40}$ ]] || {
  echo "BLOCKED: pass the exact 40-character merged Home Center source commit." >&2
  exit 2
}

STATE_DIR="$HOME/.local/state/home-center"
LOG="$STATE_DIR/phone-relay.log"
NODE="$HOME/.config/home-center/phone-relay.json"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
RECEIPT="$STATE_DIR/native-phone-plane-bootstrap-$STAMP.receipt.json"
mkdir -p "$STATE_DIR"

mapfile -t RELAY_PIDS < <(pgrep -f '[a]ndroid_phone_home_center_relay.py' || true)
(("${#RELAY_PIDS[@]}" <= 1)) || {
  echo "BLOCKED: multiple phone relay processes are running; refusing an ambiguous replacement." >&2
  exit 3
}

LIVE_SCRIPT=""
if (("${#RELAY_PIDS[@]}" == 1)) && [[ -r "/proc/${RELAY_PIDS[0]}/cmdline" ]]; then
  mapfile -d '' LIVE_ARGV < "/proc/${RELAY_PIDS[0]}/cmdline" || true
  for arg in "${LIVE_ARGV[@]:-}"; do
    [[ "$arg" == *android_phone_home_center_relay.py ]] && LIVE_SCRIPT="$arg"
  done
fi
if [[ -z "$LIVE_SCRIPT" ]]; then
  for candidate in     "$HOME/home-center/tools/android_phone_home_center_relay.py"     "$HOME/src/home-center/tools/android_phone_home_center_relay.py"     "/storage/emulated/0/Documents/GodotProjects/home-center/tools/android_phone_home_center_relay.py"
  do
    [[ -f "$candidate" ]] && { LIVE_SCRIPT="$candidate"; break; }
  done
fi
[[ -n "$LIVE_SCRIPT" && -f "$LIVE_SCRIPT" ]] || {
  echo "BLOCKED: the installed Home Center phone relay could not be located." >&2
  exit 4
}

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$LIVE_SCRIPT")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
[[ -n "$REPO_ROOT" && "$SCRIPT_DIR" == "$REPO_ROOT/tools" ]] || {
  echo "BLOCKED: the live relay is not the fixed tools/ worker in a Home Center checkout." >&2
  exit 5
}
ORIGIN="$(git -C "$REPO_ROOT" remote get-url origin 2>/dev/null || true)"
case "$ORIGIN" in
  https://github.com/Valar05/home-center|https://github.com/Valar05/home-center.git|git@github.com:Valar05/home-center.git) ;;
  *) echo "BLOCKED: unexpected Home Center origin: $ORIGIN" >&2; exit 6 ;;
esac

git -C "$REPO_ROOT" fetch --quiet origin main
git -C "$REPO_ROOT" fetch --quiet origin "$SOURCE_HEAD"
MAIN_HEAD="$(git -C "$REPO_ROOT" rev-parse refs/remotes/origin/main)"
git -C "$REPO_ROOT" cat-file -e "$SOURCE_HEAD^{commit}"
git -C "$REPO_ROOT" merge-base --is-ancestor "$SOURCE_HEAD" "$MAIN_HEAD" || {
  echo "BLOCKED: source commit is not merged into current origin/main." >&2
  exit 7
}

FILES=(
  tools/android_phone_home_center_relay.py
  tools/android_phone_diagnostics.py
  tools/android_anvil_shell_maintenance.py
)
STAGE="$(mktemp -d "$STATE_DIR/native-phone-plane.XXXXXX")"
BACKUP="$STATE_DIR/native-phone-plane-backup-$STAMP"
mkdir -p "$BACKUP"
for rel in "${FILES[@]}"; do
  git -C "$REPO_ROOT" show "$SOURCE_HEAD:$rel" > "$STAGE/$(basename "$rel")"
done
python -m py_compile   "$STAGE/android_phone_home_center_relay.py"   "$STAGE/android_phone_diagnostics.py"   "$STAGE/android_anvil_shell_maintenance.py"
grep -q "'phone_maintenance_anvil_shell'" "$STAGE/android_phone_home_center_relay.py"
grep -q "MAINTENANCE_ACTIONS={'anvil_shell_build_install'}" "$STAGE/android_phone_home_center_relay.py"

for rel in "${FILES[@]}"; do
  cp -p "$REPO_ROOT/$rel" "$BACKUP/$(basename "$rel")"
done

restore_old() {
  for rel in "${FILES[@]}"; do
    cp -p "$BACKUP/$(basename "$rel")" "$REPO_ROOT/$rel.rollback"
    mv -f "$REPO_ROOT/$rel.rollback" "$REPO_ROOT/$rel"
  done
}
install_new() {
  for rel in "${FILES[@]}"; do
    cp "$STAGE/$(basename "$rel")" "$REPO_ROOT/$rel.bootstrap-new" || return 1
    chmod --reference="$REPO_ROOT/$rel" "$REPO_ROOT/$rel.bootstrap-new" || return 1
    mv -f "$REPO_ROOT/$rel.bootstrap-new" "$REPO_ROOT/$rel" || return 1
  done
}

if ! install_new; then
  restore_old
  echo "BLOCKED: atomic module installation failed; original files restored." >&2
  exit 8
fi
if (("${#RELAY_PIDS[@]}" == 1)); then
  kill "${RELAY_PIDS[0]}" 2>/dev/null || true
  for _ in 1 2 3 4 5; do
    kill -0 "${RELAY_PIDS[0]}" 2>/dev/null || break
    sleep 1
  done
  if kill -0 "${RELAY_PIDS[0]}" 2>/dev/null; then
    restore_old
    echo "BLOCKED: old relay did not stop; original files restored." >&2
    exit 8
  fi
fi

start_relay() {
  nohup python "$REPO_ROOT/tools/android_phone_home_center_relay.py" >>"$LOG" 2>&1 </dev/null &
  NEW_PID=$!
}
start_relay
sleep 5
if ! kill -0 "$NEW_PID" 2>/dev/null || ! tail -n 120 "$LOG" | grep -q 'Home Center phone relay online: primary-phone'; then
  kill "$NEW_PID" 2>/dev/null || true
  restore_old
  start_relay
  echo "BLOCKED: new relay failed startup verification; original files restored and restarted." >&2
  exit 9
fi

if ! python - "$NODE" <<'PY'
import json, pathlib, sys
node = pathlib.Path(sys.argv[1])
data = json.loads(node.read_text())
caps = ((data.get("registration") or {}).get("capabilities") or [])
required = {"phone_diagnostics_readonly", "phone_maintenance_anvil_shell"}
missing = sorted(required.difference(caps))
if missing:
    raise SystemExit("BLOCKED: registered relay lacks capabilities: " + ",".join(missing))
PY
then
  kill "$NEW_PID" 2>/dev/null || true
  restore_old
  start_relay
  echo "BLOCKED: new capabilities were not registered; original files restored and restarted." >&2
  exit 10
fi

if ! python - "$RECEIPT" "$SOURCE_HEAD" "$MAIN_HEAD" "$REPO_ROOT" "$LIVE_SCRIPT" "$BACKUP" "$NEW_PID" "${FILES[@]}" <<'PY'
import hashlib, json, pathlib, sys, time
receipt, source, main, root, live, backup, pid, *files = sys.argv[1:]
root_path = pathlib.Path(root)
rows = []
for rel in files:
    p = root_path / rel
    rows.append({"path": rel, "bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
body = {
    "schema": "home-center.native-phone-plane-bootstrap.v1",
    "status": "BOOTSTRAP_VERIFIED",
    "automaticReplay": False,
    "deviceId": "primary-phone",
    "laneId": "PHONE_MAINTENANCE",
    "sourceHead": source,
    "observedOriginMain": main,
    "repositoryRoot": root,
    "liveWorker": live,
    "backup": backup,
    "pid": int(pid),
    "capabilities": ["phone_diagnostics_readonly", "phone_maintenance_anvil_shell"],
    "files": rows,
    "recordedAtMs": int(time.time() * 1000),
}
canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
body["receiptHash"] = hashlib.sha256(canonical).hexdigest()
pathlib.Path(receipt).write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")
PY
then
  kill "$NEW_PID" 2>/dev/null || true
  restore_old
  start_relay
  echo "BLOCKED: bootstrap receipt could not be written; original files restored and restarted." >&2
  exit 11
fi
chmod 600 "$RECEIPT"
printf 'NATIVE PHONE PLANE BOOTSTRAP VERIFIED\nRECEIPT=%s\n' "$RECEIPT"
