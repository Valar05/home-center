#!/data/data/com.termux/files/usr/bin/bash
# Fortress Online — primary-phone continuous creation megabootstrap
# One idempotent entrypoint. Installs/repairs the phone body, keeps it awake,
# preserves commands while the desktop is unavailable, and dispatches them only
# through the bounded Chromium Throne command client.
set -Eeuo pipefail
umask 077

VERSION="2026.08.13.1"
OWNER="Drew Clarke"
DEFAULT_REPO_A="/storage/emulated/0/Documents/GodotProjects/home-center-phone-hands"
DEFAULT_REPO_B="/storage/emulated/0/Documents/GodotProjects/home-center"
STATE_ROOT="${HC_STATE_DIR:-$HOME/.local/state/home-center}/fortress-continuous"
INSTALL_ROOT="$HOME/.local/share/home-center/fortress-continuous"
BIN_ROOT="$HOME/bin"
BOOT_ROOT="$HOME/.termux/boot"
LOCK_DIR="$STATE_ROOT/bootstrap.lock"
LOG="$STATE_ROOT/fortress-phone.log"
LATEST="$STATE_ROOT/latest.json"
HISTORY="$STATE_ROOT/history.jsonl"
CONTRACT="$STATE_ROOT/continuous-creation-contract.json"
SEED_HASH="$STATE_ROOT/seeded-contract.sha256"
DISPATCH_CURSOR="$STATE_ROOT/dispatch-cursor.json"
DISPATCH_LOG="$STATE_ROOT/dispatch.jsonl"
SUPERVISOR_LOG="$STATE_ROOT/supervisor.log"
SELF_PATH="${BASH_SOURCE[0]}"
REPO_ROOT=""
RUNTIME_ROOT="${HC_FORTRESS_RUNTIME:-${PREFIX:-$HOME/.local}/var/lib/fortress-campaign/runtime}"
MODE="${1:-ensure}"

mkdir -p "$STATE_ROOT" "$INSTALL_ROOT" "$BIN_ROOT" "$BOOT_ROOT"
touch "$LOG" "$HISTORY" "$DISPATCH_LOG"
chmod 700 "$STATE_ROOT" "$INSTALL_ROOT" "$BIN_ROOT" "$BOOT_ROOT" 2>/dev/null || true
chmod 600 "$LOG" "$HISTORY" "$DISPATCH_LOG" 2>/dev/null || true

log() {
  printf '%s %s\n' "$(date -Iseconds)" "$*" | tee -a "$LOG" >&2
}

json_receipt() {
  local phase="$1" status="$2" detail="$3"
  shift 3 || true
  python3 - "$LATEST" "$HISTORY" "$phase" "$status" "$detail" "$VERSION" "$@" <<'PY'
import json, os, sys, time
latest, history, phase, status, detail, version, *pairs = sys.argv[1:]
extra = {}
for pair in pairs:
    if "=" not in pair:
        continue
    key, value = pair.split("=", 1)
    if value in ("true", "false"):
        extra[key] = value == "true"
    else:
        try:
            extra[key] = int(value)
        except ValueError:
            extra[key] = value
obj = {
    "schema": "fortress.phone.megabootstrap.receipt.v1",
    "version": version,
    "phase": phase,
    "status": status,
    "detail": detail,
    "atEpoch": int(time.time()),
    **extra,
}
os.makedirs(os.path.dirname(latest), exist_ok=True)
tmp = latest + ".tmp"
with open(tmp, "w", encoding="utf-8") as handle:
    json.dump(obj, handle, indent=2, sort_keys=True)
    handle.write("\n")
os.replace(tmp, latest)
with open(history, "a", encoding="utf-8") as handle:
    handle.write(json.dumps(obj, sort_keys=True) + "\n")
print(json.dumps(obj, sort_keys=True))
PY
}

release_lock() {
  rmdir "$LOCK_DIR" 2>/dev/null || true
}

acquire_lock() {
  if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    if [ -f "$LATEST" ]; then cat "$LATEST"; else printf '{"status":"already_running"}\n'; fi
    exit 0
  fi
  trap release_lock EXIT INT TERM
}

need_command() {
  command -v "$1" >/dev/null 2>&1
}

install_packages() {
  local missing=() pair command package
  for pair in \
    "git:git" \
    "curl:curl" \
    "python3:python" \
    "node:nodejs-lts" \
    "ssh:openssh" \
    "tmux:tmux"; do
    command="${pair%%:*}"
    package="${pair#*:}"
    need_command "$command" || missing+=("$package")
  done
  if [ "${#missing[@]}" -gt 0 ]; then
    need_command pkg || {
      json_receipt bootstrap blocked "Termux pkg is unavailable; required commands are missing" "missing=${missing[*]}"
      return 2
    }
    log "Installing missing bounded runtime packages: ${missing[*]}"
    pkg install -y "${missing[@]}" >>"$LOG" 2>&1
  fi
  for command in git curl python3 node ssh tmux; do
    need_command "$command" || {
      json_receipt bootstrap blocked "Required command remains unavailable" "command=$command"
      return 3
    }
  done
}

resolve_repo() {
  local script_root candidate
  script_root="$(CDPATH= cd -- "$(dirname -- "$SELF_PATH")/.." 2>/dev/null && pwd || true)"
  for candidate in \
    "${HC_REPO_ROOT:-}" \
    "$script_root" \
    "$DEFAULT_REPO_A" \
    "$DEFAULT_REPO_B" \
    "$HOME/home-center"; do
    [ -n "$candidate" ] || continue
    if git -C "$candidate" rev-parse --git-dir >/dev/null 2>&1; then
      REPO_ROOT="$(cd "$candidate" && pwd)"
      export HC_REPO_ROOT="$REPO_ROOT"
      export HC_LIVE_REPO="$REPO_ROOT"
      return 0
    fi
  done
  json_receipt bootstrap blocked "Authenticated home-center repository was not found" \
    "searched=$DEFAULT_REPO_A,$DEFAULT_REPO_B,$HOME/home-center"
  return 4
}

write_contract() {
  python3 - "$CONTRACT" "$OWNER" "$VERSION" <<'PY'
import json, os, sys
path, owner, version = sys.argv[1:]
mission = """FORTRESS ONLINE — CONTINUOUS CREATION

OWNER
Drew Clarke.

OUTCOME
Continuously capture, prioritize, create, repair, verify, deliver, and improve everything Drew has stated that can responsibly be built or made better. This is not a one-time bootstrap and not a request to merely keep services alive. The system must keep bringing treasure home after this chat dies.

INTAKE
Treat Atom commands as binding owner commissions. Continuously mine only authorized durable sources: Home Center state and intake, owner-authorized text intake, Google Drive/Home Center documents, GitHub repositories/issues/receipts, prior campaign artifacts, and visible ChatGPT history available through Chromium Throne. Preserve source, date, owner, exact desired outcome, exclusions, execution lane, evidence standard, delivery surface, and acceptance state. Never silently broaden private access or treat inference as a remembered fact.

EXECUTION
Atom and Vlad on the phone are the operator surface. Chromium Throne is desktop muscle: up to eight visible ChatGPT Pro-reasoning workers, never Instant by default, one bounded non-conflicting slice per worker. Use local deterministic tools for known operations. Use model inference only where ambiguity or creation genuinely requires it. Every model-assisted slice must extract tests, recipes, structured state, or tooling that makes the next execution cheaper and dumber, decaying toward low local inference and then no inference.

PRIORITY
1. Broken or stranded execution organs and anything Drew can use immediately.
2. Accessibility, especially practical use by Drew's blind spouse.
3. Unanswered human intake, safety-relevant continuity, and promises already made.
4. High-leverage reusable infrastructure that unlocks many desires.
5. Creative and product work ordered by deliverability and joy.
Do not polish a turd. Repair or replace the unusable path, then improve it until it is magnificent.

BOUNDARIES
PORTCULLIS LOCKED. Preserve the commissioned outcome, owner, tool/lane, exclusions, evidence standard, and delivery surface. Repository or local implementation is not deployment. Tests prove only what they test. Device receipts prove only the device action observed. Delivery and acceptance are distinct. Never use Drew as command transport when an authorized body is callable. Never substitute an adjacent service or architecture without explicit approval.

REVIEW AND CONTINUITY
Research -> bounded plan -> select relevant Judgment Jars -> antagonize -> Venice plan review -> execute -> tests/device proof -> Venice completion review -> Vlad scarcity/continuity review -> Tetsuya release gate. CONTINUE_REQUIRED keeps the same mission alive. STOP_ALLOWED closes only the bounded slice, not the continuous campaign. A response boundary is never completion. Persist strict six-field handoffs and rotate choked browser threads.

FIRST CAMPAIGN
Build the authoritative desire ledger from durable sources, reconcile duplicates and stale claims, classify requested/intended/implemented/tested/deployed/callable/delivered/accepted state, then execute the highest-priority independent slices. Keep the ledger and receipts durable in Home Center/GitHub, not only inside a ChatGPT thread."""
obj = {
    "schema": "fortress.continuous-creation.contract.v1",
    "version": version,
    "owner": owner,
    "mission": mission,
    "operatorSurface": "Atom/Vlad on primary phone",
    "desktopMuscle": "Chromium Throne",
    "workerModelDefault": "ChatGPT Pro reasoning",
    "instantDefault": False,
    "maxParallelWorkers": 8,
    "localFirst": True,
    "inferenceDecay": ["ChatGPT Pro reasoning", "bounded local inference", "deterministic recipe", "no inference"],
    "neverTerminal": True,
}
os.makedirs(os.path.dirname(path), exist_ok=True)
tmp = path + ".tmp"
with open(tmp, "w", encoding="utf-8") as handle:
    json.dump(obj, handle, indent=2, sort_keys=True)
    handle.write("\n")
os.replace(tmp, path)
PY
  chmod 600 "$CONTRACT"
}

sync_and_repair_phone() {
  local campaign="$REPO_ROOT/tools/fortress_phone_campaign.sh"
  if [ ! -f "$campaign" ]; then
    json_receipt repair degraded "Canonical phone campaign is missing; independent bootstrap continues" "campaign=$campaign"
    return 0
  fi
  log "Running canonical phone repair campaign against an isolated runtime"
  if ! env HC_LIVE_REPO="$REPO_ROOT" bash "$campaign" run >>"$LOG" 2>&1; then
    json_receipt repair degraded "Canonical campaign reported a blocker; independent services will still be installed" \
      "campaign=$campaign"
  fi
}

install_self() {
  local installed="$INSTALL_ROOT/fortress_phone_megabootstrap.sh"
  if [ -f "$SELF_PATH" ]; then
    cp "$SELF_PATH" "$installed"
  elif [ -f "$REPO_ROOT/tools/fortress_phone_megabootstrap.sh" ]; then
    cp "$REPO_ROOT/tools/fortress_phone_megabootstrap.sh" "$installed"
  else
    json_receipt bootstrap blocked "Megabootstrap source cannot be installed durably" "self=$SELF_PATH"
    return 5
  fi
  chmod 700 "$installed"
  cat >"$BIN_ROOT/fortress-online" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
if [ "\$#" -eq 0 ]; then set -- ensure; fi
exec "$installed" "\$@"
EOF
  chmod 700 "$BIN_ROOT/fortress-online"
}

install_dispatcher() {
  cat >"$INSTALL_ROOT/dispatch_atom_to_throne.py" <<'PY'
#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, os, re, subprocess, sys, time
from pathlib import Path

HOME = Path.home()
STATE = Path(os.environ.get("HC_STATE_DIR", str(HOME / ".local/state/home-center"))) / "fortress-continuous"
COMMANDS = Path(os.environ.get("ATOM_STATE_DIR", str(HOME / ".local/state/atom"))) / "commands.jsonl"
CURSOR = STATE / "dispatch-cursor.json"
LOG = STATE / "dispatch.jsonl"
CONTRACT = STATE / "continuous-creation-contract.json"
ENDPOINT = os.environ.get("FORTRESS_CAULDRON_SSH", "dclar@192.168.40.213")
SSH_CONFIG = os.environ.get("FORTRESS_SSH_CONFIG", "")
STATE.mkdir(parents=True, exist_ok=True)

def append(event: dict) -> None:
    event = {"atEpoch": int(time.time()), **event}
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")

def load_cursor() -> dict:
    try:
        value = json.loads(CURSOR.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {"offset": 0}
    except Exception:
        return {"offset": 0}

def save_cursor(offset: int, command_id: str) -> None:
    value = {"offset": offset, "lastCommandId": command_id, "updatedAtEpoch": int(time.time())}
    tmp = CURSOR.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(CURSOR)

def safe_id(value: str, prefix: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9_.:-]+", "-", value or "").strip("-")
    if len(clean) < 6:
        clean = prefix + "-" + hashlib.sha256((value or str(time.time())).encode()).hexdigest()[:20]
    return clean[:170]

def endpoint_args() -> tuple[list[str], str]:
    value = ENDPOINT.strip()
    port = None
    destination = value
    if value.count(":") == 1 and value.rsplit(":", 1)[1].isdigit():
        destination, port_text = value.rsplit(":", 1)
        port = int(port_text)
    args = [
        "ssh", "-o", "BatchMode=yes", "-o", "PasswordAuthentication=no",
        "-o", "KbdInteractiveAuthentication=no", "-o", "StrictHostKeyChecking=accept-new",
        "-o", "ConnectTimeout=5",
    ]
    if SSH_CONFIG:
        args += ["-F", str(Path(SSH_CONFIG).expanduser())]
    if port:
        args += ["-p", str(port)]
    return args, destination

def send(command: dict) -> tuple[bool, dict]:
    raw = json.dumps(command, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    encoded = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    args, destination = endpoint_args()
    # The desktop megabootstrap installs this user-owned wrapper in %USERPROFILE%.
    remote = 'cmd.exe /d /s /c ""%USERPROFILE%\\fortress-throne.cmd" ' + encoded + '"'
    try:
        proc = subprocess.run(args + [destination, remote], text=True, capture_output=True, timeout=30)
    except Exception as exc:
        return False, {"error": f"{type(exc).__name__}: {exc}"}
    output = (proc.stdout or "").strip()
    error = (proc.stderr or "").strip()
    parsed = {}
    if output:
        try:
            parsed = json.loads(output.splitlines()[-1])
        except Exception:
            parsed = {"stdout": output[-4000:]}
    ok = proc.returncode == 0 and parsed.get("ok") is True
    return ok, {"rc": proc.returncode, "result": parsed, "stderr": error[-2000:]}

def build(atom: dict) -> dict:
    command_id = safe_id(str(atom.get("clientCommandId") or ""), "atom")
    text = str(atom.get("text") or "").strip()
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    commission = (
        "PORTCULLIS LOCKED\n\n"
        "OWNER COMMISSION FROM ATOM\n"
        + text
        + "\n\nCONTINUOUS CREATION CONTRACT\n"
        + str(contract.get("mission") or "")
        + "\n\nCURRENT SLICE\n"
        "Interpret the owner commission literally. Research authoritative state, make a bounded plan, run the relevant Judgment Jars and Venice plan gate, then execute the highest-leverage non-conflicting slice through persistent Home Center/GitHub/device lanes. Produce strict receipts and a six-field handoff when more remains. Do not stop merely because this response ends."
    )
    context = json.dumps({
        "source": "Atom primary-phone command queue",
        "createdAt": atom.get("createdAt"),
        "humanInitiated": atom.get("humanInitiated") is True,
        "orchestrator": atom.get("orchestrator") or "Vlad",
        "mode": atom.get("mode") or "deterministic",
        "contractVersion": contract.get("version"),
    }, sort_keys=True)
    return {
        "commandId": command_id,
        "action": "swarm.enqueue",
        "jobs": [{
            "jobId": safe_id(command_id + "-slice-1", "job"),
            "commission": commission[:32000],
            "context": context[:24000],
        }],
    }

def dispatch_once() -> int:
    if not COMMANDS.exists():
        append({"kind": "dispatch.idle", "state": "atom_commands_missing", "path": str(COMMANDS)})
        return 0
    cursor = load_cursor()
    size = COMMANDS.stat().st_size
    offset = int(cursor.get("offset") or 0)
    if offset < 0 or offset > size:
        append({"kind": "dispatch.cursor_reset", "oldOffset": offset, "size": size})
        offset = 0
    with COMMANDS.open("rb") as handle:
        handle.seek(offset)
        while True:
            start = handle.tell()
            raw = handle.readline()
            if not raw:
                return 0
            end = handle.tell()
            try:
                atom = json.loads(raw.decode("utf-8"))
            except Exception as exc:
                append({"kind": "dispatch.invalid_line", "offset": start, "error": str(exc)})
                save_cursor(end, "invalid-line")
                continue
            if atom.get("humanInitiated") is not True or not str(atom.get("text") or "").strip():
                save_cursor(end, str(atom.get("clientCommandId") or "ignored"))
                continue
            command = build(atom)
            ok, result = send(command)
            append({
                "kind": "dispatch.throne",
                "ok": ok,
                "atomCommandId": atom.get("clientCommandId"),
                "throneCommandId": command["commandId"],
                **result,
            })
            if not ok:
                return 2
            save_cursor(end, command["commandId"])

if __name__ == "__main__":
    raise SystemExit(dispatch_once())
PY
  chmod 700 "$INSTALL_ROOT/dispatch_atom_to_throne.py"
  cat >"$BIN_ROOT/fortress-dispatch" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec python3 "$INSTALL_ROOT/dispatch_atom_to_throne.py" "\$@"
EOF
  chmod 700 "$BIN_ROOT/fortress-dispatch"
}

install_supervisor() {
  cat >"$INSTALL_ROOT/supervisor.sh" <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
set -u
umask 077
STATE="${HC_STATE_DIR:-$HOME/.local/state/home-center}/fortress-continuous"
INSTALL="$HOME/.local/share/home-center/fortress-continuous"
RUNTIME="${HC_FORTRESS_RUNTIME:-${PREFIX:-$HOME/.local}/var/lib/fortress-campaign/runtime}"
LOG="$STATE/supervisor.log"
mkdir -p "$STATE"
termux-wake-lock >/dev/null 2>&1 || true

say_status() {
  local text="$1"
  if command -v termux-notification >/dev/null 2>&1; then
    termux-notification \
      --id 6710 \
      --ongoing true \
      --priority high \
      --title 'Fortress Online — Continuous Creation' \
      --content "$text" \
      --button1 'Open Atom' \
      --button1-action "bash -l -c '$HOME/bin/atom-open'" \
      --button2 'Repair' \
      --button2-action "bash -l -c '$HOME/bin/fortress-online ensure'" \
      --button3 'Receipts' \
      --button3-action "bash -l -c '$HOME/bin/fortress-online status | termux-share -a send'" >/dev/null 2>&1 || true
  fi
}

ensure_atom() {
  curl -fsS --max-time 3 http://127.0.0.1:8788/v1/atom/status >/dev/null 2>&1 && return 0
  [ -x "$HOME/.termux/boot/15-atom" ] && "$HOME/.termux/boot/15-atom" >>"$LOG" 2>&1 || true
}

ensure_vlad() {
  pgrep -f '[v]lad_swarm_daemon.py' >/dev/null 2>&1 && return 0
  [ -f "$RUNTIME/tools/setup_vlad_swarm_daemon.sh" ] && bash "$RUNTIME/tools/setup_vlad_swarm_daemon.sh" restart >>"$LOG" 2>&1 || true
}

ensure_relay() {
  pgrep -f '[a]ndroid_phone_home_center_relay.py' >/dev/null 2>&1 && return 0
  if [ -f "$RUNTIME/tools/home_center_phone_relay_recover.sh" ]; then
    HC_PHONE_REPO="$RUNTIME" bash "$RUNTIME/tools/home_center_phone_relay_recover.sh" >>"$LOG" 2>&1 || true
  elif [ -f "$RUNTIME/tools/setup_android_phone_home_center_relay.sh" ]; then
    bash "$RUNTIME/tools/setup_android_phone_home_center_relay.sh" >>"$LOG" 2>&1 || true
  fi
}

write_state() {
  python3 - "$STATE/supervisor.json" <<'PY'
import json, os, subprocess, sys, time
path = sys.argv[1]
def alive(pattern):
    return subprocess.run(["pgrep","-f",pattern],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode == 0
def atom():
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:8788/v1/atom/status", timeout=3) as r:
            return json.load(r)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
obj = {
    "schema": "fortress.phone.supervisor.v1",
    "atEpoch": int(time.time()),
    "atom": atom(),
    "vladAlive": alive("[v]lad_swarm_daemon.py"),
    "relayAlive": alive("[a]ndroid_phone_home_center_relay.py"),
}
tmp = path + ".tmp"
open(tmp,"w",encoding="utf-8").write(json.dumps(obj,indent=2,sort_keys=True)+"\n")
os.replace(tmp,path)
PY
}

say_status 'Starting self-healing phone body and browser-swarm dispatch.'
while :; do
  termux-wake-lock >/dev/null 2>&1 || true
  ensure_atom
  ensure_vlad
  ensure_relay
  python3 "$INSTALL/dispatch_atom_to_throne.py" >>"$LOG" 2>&1 || true
  write_state
  sleep "${FORTRESS_SUPERVISOR_INTERVAL:-15}"
done
EOF
  chmod 700 "$INSTALL_ROOT/supervisor.sh"

  cat >"$BOOT_ROOT/00-fortress-online" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
if ! tmux has-session -t fortress-continuous 2>/dev/null; then
  tmux new-session -d -s fortress-continuous "$INSTALL_ROOT/supervisor.sh"
fi
EOF
  chmod 700 "$BOOT_ROOT/00-fortress-online"
}

start_supervisor() {
  termux-wake-lock >/dev/null 2>&1 || true
  if tmux has-session -t fortress-continuous 2>/dev/null; then
    return 0
  fi
  tmux new-session -d -s fortress-continuous "$INSTALL_ROOT/supervisor.sh"
  sleep 1
  tmux has-session -t fortress-continuous 2>/dev/null
}

initialize_dispatch_cursor() {
  # Historical commands remain authoritative intake for the genesis archaeology
  # worker, but they are not blindly fanned into one worker per old line.
  # Begin direct dispatch at the current EOF, then append the genesis command.
  if [ -f "$DISPATCH_CURSOR" ]; then
    return 0
  fi
  python3 - "$DISPATCH_CURSOR" "${ATOM_STATE_DIR:-$HOME/.local/state/atom}/commands.jsonl" <<'PY'
import json, os, sys, time
cursor, commands = sys.argv[1:]
offset = os.path.getsize(commands) if os.path.exists(commands) else 0
tmp = cursor + ".tmp"
open(tmp, "w", encoding="utf-8").write(json.dumps({
    "offset": offset,
    "lastCommandId": "bootstrap-existing-history-preserved-for-archaeology",
    "updatedAtEpoch": int(time.time()),
}, indent=2, sort_keys=True) + "\n")
os.replace(tmp, cursor)
PY
  chmod 600 "$DISPATCH_CURSOR"
}

seed_atom() {
  local current_hash prior_hash payload response
  current_hash="$(sha256sum "$CONTRACT" | awk '{print $1}')"
  prior_hash="$(cat "$SEED_HASH" 2>/dev/null || true)"
  if [ "$current_hash" = "$prior_hash" ]; then
    return 0
  fi
  for _ in 1 2 3 4 5; do
    curl -fsS --max-time 3 http://127.0.0.1:8788/v1/atom/status >/dev/null 2>&1 && break
    [ -x "$HOME/.termux/boot/15-atom" ] && "$HOME/.termux/boot/15-atom" >>"$LOG" 2>&1 || true
    sleep 1
  done
  payload="$(python3 - "$CONTRACT" "$current_hash" <<'PY'
import json, sys, datetime
path, digest = sys.argv[1:]
contract = json.load(open(path, encoding="utf-8"))
print(json.dumps({
    "clientCommandId": "fortress-continuous-creation-" + digest[:20],
    "text": contract["mission"],
    "createdAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "source": "fortress-phone-megabootstrap",
    "humanInitiated": True,
}))
PY
)"
  if response="$(curl -fsS --max-time 20 -H 'content-type: application/json' -d "$payload" http://127.0.0.1:8788/v1/atom/commands 2>>"$LOG")"; then
    printf '%s\n' "$current_hash" >"$SEED_HASH"
    printf '%s\n' "$response" >"$STATE_ROOT/genesis-atom-receipt.json"
    chmod 600 "$SEED_HASH" "$STATE_ROOT/genesis-atom-receipt.json"
    return 0
  fi
  json_receipt seed degraded "Atom mission could not be seeded yet; supervisor will keep the body alive" \
    "contractSha256=$current_hash"
  return 0
}

status() {
  python3 - "$LATEST" "$STATE_ROOT/supervisor.json" "$STATE_ROOT/genesis-atom-receipt.json" "$DISPATCH_CURSOR" "$CONTRACT" <<'PY'
import json, os, sys
names = ["bootstrap","supervisor","genesis","dispatchCursor","contract"]
out = {"schema":"fortress.phone.status.v1"}
for name,path in zip(names,sys.argv[1:]):
    try: out[name]=json.load(open(path,encoding="utf-8"))
    except Exception: out[name]=None
print(json.dumps(out,indent=2,sort_keys=True))
PY
}

stop_explicit() {
  tmux kill-session -t fortress-continuous 2>/dev/null || true
  termux-wake-unlock >/dev/null 2>&1 || true
  json_receipt supervisor stopped "Continuous creation stopped by explicit operator command"
}

ensure_all() {
  acquire_lock
  json_receipt bootstrap running "Beginning primary-phone continuous creation bootstrap" "owner=$OWNER"
  install_packages
  resolve_repo
  write_contract
  sync_and_repair_phone
  install_self
  install_dispatcher
  install_supervisor
  initialize_dispatch_cursor
  seed_atom
  if start_supervisor; then
    json_receipt bootstrap healthy "Phone body installed, repaired, awake, and dispatching durable Atom commands" \
      "repo=$REPO_ROOT" \
      "runtime=$RUNTIME_ROOT" \
      "tmuxSession=fortress-continuous" \
      "contractSha256=$(sha256sum "$CONTRACT" | awk '{print $1}')"
  else
    json_receipt bootstrap degraded "Bootstrap installed but the continuous supervisor did not remain alive" \
      "repo=$REPO_ROOT"
    return 8
  fi
  status
}

case "$MODE" in
  ensure|repair|run) ensure_all ;;
  supervise)
    exec "$INSTALL_ROOT/supervisor.sh"
    ;;
  dispatch)
    exec python3 "$INSTALL_ROOT/dispatch_atom_to_throne.py"
    ;;
  status|receipts)
    status
    ;;
  stop)
    stop_explicit
    ;;
  *)
    printf 'usage: fortress_phone_megabootstrap.sh [ensure|repair|supervise|dispatch|status|stop]\n' >&2
    exit 64
    ;;
esac
