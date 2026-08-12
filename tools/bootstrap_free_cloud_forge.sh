#!/bin/sh
# Home Center free cloud forge bootstrap.
# Real Git forge on an existing free-tier Linux VM; GCS is backup only.
# POSIX sh by design for Termux handoff safety.
set -eu

STATE_DIR="$HOME/.home-center/cloud-forge"
STATE_FILE="$STATE_DIR/state.env"
LOG_FILE="$STATE_DIR/bootstrap.log"
mkdir -p "$STATE_DIR"
: > "$LOG_FILE" 2>/dev/null || true

say(){ printf '\n[forge] %s\n' "$*"; }
ok(){ printf '[ok] %s\n' "$*"; }
warn(){ printf '[warn] %s\n' "$*" >&2; }
fail(){ printf '[blocked] %s\n' "$*" >&2; exit 1; }

have(){ command -v "$1" >/dev/null 2>&1; }

load_state(){
  if [ -f "$STATE_FILE" ]; then
    # shellcheck disable=SC1090
    . "$STATE_FILE"
  fi
  : "${FORGE_HOST:=}"
  : "${FORGE_USER:=ubuntu}"
  : "${FORGE_PORT:=22}"
  : "${GCS_TARGET:=}"
}

save_state(){
  umask 077
  {
    printf 'FORGE_HOST=%s\n' "$FORGE_HOST"
    printf 'FORGE_USER=%s\n' "$FORGE_USER"
    printf 'FORGE_PORT=%s\n' "$FORGE_PORT"
    printf 'GCS_TARGET=%s\n' "$GCS_TARGET"
  } > "$STATE_FILE"
}

ask(){
  var=$1; prompt=$2; def=${3-}
  eval cur='${'"$var"'-}'
  [ -n "$cur" ] && return 0
  if [ -n "$def" ]; then
    printf '%s [%s]: ' "$prompt" "$def"
  else
    printf '%s: ' "$prompt"
  fi
  IFS= read -r ans || true
  [ -n "${ans:-}" ] || ans=$def
  eval "$var=\$ans"
}

ensure_termux_tools(){
  say "Checking Termux prerequisites"
  if ! have ssh || ! have scp || ! have curl; then
    have pkg || fail "Run this from Termux; pkg was not found."
    pkg update -y
    pkg install -y openssh curl
  fi
  have ssh && have scp && have curl || fail "OpenSSH/curl installation did not complete."
  ok "Termux transport tools available"
}

ensure_key(){
  mkdir -p "$HOME/.ssh"
  chmod 700 "$HOME/.ssh"
  if [ ! -f "$HOME/.ssh/id_ed25519" ]; then
    say "Generating phone SSH identity"
    ssh-keygen -q -t ed25519 -f "$HOME/.ssh/id_ed25519" -N '' -C home-center-phone
  fi
  ok "Phone SSH identity ready"
}

collect_target(){
  load_state
  say "Cloud forge target"
  ask FORGE_HOST "Free-tier VM IP or DNS"
  ask FORGE_USER "SSH user" "$FORGE_USER"
  ask FORGE_PORT "SSH port" "$FORGE_PORT"
  [ -n "$FORGE_HOST" ] || fail "A VM host is required. Create the free-tier VM, then rerun this same command."
  case "$FORGE_PORT" in *[!0-9]*|'') fail "SSH port must be numeric.";; esac
  if [ -z "$GCS_TARGET" ]; then
    printf 'Optional GCS backup target (gs://bucket/prefix, Enter to defer): '
    IFS= read -r GCS_TARGET || true
  fi
  save_state
}

ssh_base(){
  ssh -p "$FORGE_PORT" -o ConnectTimeout=12 -o ServerAliveInterval=20 -o ServerAliveCountMax=3 -o StrictHostKeyChecking=accept-new "$FORGE_USER@$FORGE_HOST" "$@"
}

prove_ssh(){
  say "Proving SSH lane"
  if ! ssh_base 'printf "SSH_OK\\n"; uname -srm; command -v sudo >/dev/null'; then
    printf '\nInstall this phone key on the VM user %s:\n\n' "$FORGE_USER"
    cat "$HOME/.ssh/id_ed25519.pub"
    printf '\n'
    fail "SSH is the current manual seam. After the key/network rule is fixed, rerun this same command."
  fi
  ok "SSH lane proven"
}

make_remote(){
  REMOTE="$STATE_DIR/remote-install.sh"
  cat > "$REMOTE" <<'REMOTE_EOF'
#!/bin/sh
set -eu

GCS_TARGET=${GCS_TARGET-}
GITEA_USER=git
GITEA_HOME=/home/git
GITEA_WORK=/var/lib/gitea
GITEA_CFG=/etc/gitea/app.ini
GITEA_BIN=/usr/local/bin/gitea
HTTP_PORT=3000
SSH_PORT=2222
REPORT=/var/tmp/home-center-forge-report.txt

say(){ printf '\n[remote] %s\n' "$*"; }
ok(){ printf '[ok] %s\n' "$*"; }
warn(){ printf '[warn] %s\n' "$*" >&2; }
fail(){ printf '[blocked] %s\n' "$*" >&2; exit 1; }
have(){ command -v "$1" >/dev/null 2>&1; }

sudo true || fail "sudo authorization is required on the VM."

arch=$(uname -m)
case "$arch" in
  x86_64|amd64) garch=amd64 ;;
  aarch64|arm64) garch=arm64 ;;
  *) fail "Unsupported CPU architecture: $arch" ;;
esac

if have apt-get; then
  say "Installing minimal forge dependencies"
  sudo env DEBIAN_FRONTEND=noninteractive apt-get update -y
  sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y git curl ca-certificates sqlite3 openssl unzip
else
  fail "This bootstrap currently requires an Ubuntu/Debian VM."
fi

if ! id "$GITEA_USER" >/dev/null 2>&1; then
  sudo adduser --system --shell /bin/sh --group --disabled-password --home "$GITEA_HOME" "$GITEA_USER"
fi
sudo mkdir -p "$GITEA_WORK"/custom "$GITEA_WORK"/data "$GITEA_WORK"/log /etc/gitea /var/backups/gitea
sudo chown -R "$GITEA_USER:$GITEA_USER" "$GITEA_WORK" "$GITEA_HOME"
sudo chown root:"$GITEA_USER" /etc/gitea

if [ ! -x "$GITEA_BIN" ]; then
  say "Discovering current Gitea release"
  ver=$(curl -fsSL https://dl.gitea.com/gitea/ | sed -n 's/.*href="\([0-9][0-9.]*\)\/.*/\1/p' | sort -V | tail -n 1)
  [ -n "$ver" ] || fail "Could not discover a Gitea release from dl.gitea.com."
  url="https://dl.gitea.com/gitea/$ver/gitea-$ver-linux-$garch"
  tmp=/tmp/gitea.$$
  curl -fL --retry 4 --retry-delay 2 "$url" -o "$tmp"
  chmod 755 "$tmp"
  "$tmp" --version >/dev/null || fail "Downloaded Gitea binary would not execute."
  sudo install -m 0755 "$tmp" "$GITEA_BIN"
  rm -f "$tmp"
else
  ok "Existing Gitea binary preserved"
fi

if [ ! -s "$GITEA_CFG" ]; then
  secret=$(openssl rand -hex 32)
  token=$(openssl rand -hex 32)
  lfs=$(openssl rand -hex 32)
  host=$(hostname -I 2>/dev/null | awk '{print $1}')
  [ -n "$host" ] || host=127.0.0.1
  sudo tee "$GITEA_CFG" >/dev/null <<CFG
APP_NAME = Home Center Forge
RUN_USER = git
RUN_MODE = prod
WORK_PATH = $GITEA_WORK
[repository]
ROOT = $GITEA_WORK/data/gitea-repositories
DEFAULT_BRANCH = main
[database]
DB_TYPE = sqlite3
PATH = $GITEA_WORK/data/gitea.db
[server]
HTTP_ADDR = 0.0.0.0
HTTP_PORT = $HTTP_PORT
ROOT_URL = http://$host:$HTTP_PORT/
START_SSH_SERVER = true
SSH_PORT = $SSH_PORT
SSH_LISTEN_PORT = $SSH_PORT
LFS_START_SERVER = true
LFS_JWT_SECRET = $lfs
[security]
INSTALL_LOCK = true
SECRET_KEY = $secret
INTERNAL_TOKEN = $token
[service]
DISABLE_REGISTRATION = true
REQUIRE_SIGNIN_VIEW = true
[log]
MODE = console
LEVEL = Info
CFG
  sudo chown root:"$GITEA_USER" "$GITEA_CFG"
  sudo chmod 0640 "$GITEA_CFG"
else
  ok "Existing Gitea config preserved"
fi

sudo tee /etc/systemd/system/gitea.service >/dev/null <<SERVICE
[Unit]
Description=Home Center Gitea Forge
After=network-online.target
Wants=network-online.target
[Service]
User=$GITEA_USER
Group=$GITEA_USER
WorkingDirectory=$GITEA_WORK
Environment=HOME=$GITEA_HOME
Environment=GITEA_WORK_DIR=$GITEA_WORK
ExecStart=$GITEA_BIN web --config $GITEA_CFG
Restart=always
RestartSec=3
[Install]
WantedBy=multi-user.target
SERVICE
sudo systemctl daemon-reload
sudo systemctl enable --now gitea
sleep 2
sudo systemctl is-active --quiet gitea || { sudo systemctl status gitea --no-pager || true; fail "Gitea service is not active."; }
curl -fsS --max-time 10 "http://127.0.0.1:$HTTP_PORT/" >/dev/null || fail "Gitea HTTP did not answer locally."
ok "Real Gitea forge is running"

# Create first admin only when the database has no users.
users=$(sudo -u "$GITEA_USER" GITEA_WORK_DIR="$GITEA_WORK" "$GITEA_BIN" admin user list --config "$GITEA_CFG" 2>/dev/null || true)
count=$(printf '%s\n' "$users" | sed '1d;/^[[:space:]]*$/d' | wc -l | tr -d ' ')
if [ "$count" = 0 ]; then
  pass=$(openssl rand -hex 16)
  sudo -u "$GITEA_USER" GITEA_WORK_DIR="$GITEA_WORK" "$GITEA_BIN" admin user create --config "$GITEA_CFG" --username drew --password "$pass" --email drew@local.invalid --admin --must-change-password=true >/dev/null
  sudo sh -c "umask 077; printf '%s\\n' 'username=drew' 'password=$pass' > /root/gitea-initial-admin.txt"
  warn "Initial admin credential stored on VM at /root/gitea-initial-admin.txt"
fi

BACKUP_STATE=deferred
if [ -n "$GCS_TARGET" ]; then
  case "$GCS_TARGET" in gs://*) ;; *) fail "GCS target must start gs://";; esac
  if have gcloud; then
    if gcloud auth list --filter=status:ACTIVE --format='value(account)' 2>/dev/null | grep . >/dev/null 2>&1; then
      say "Testing real Gitea dump -> GCS -> readback"
      tmpdir=$(mktemp -d)
      trap 'rm -rf "$tmpdir"' EXIT HUP INT TERM
      cd "$tmpdir"
      sudo -u "$GITEA_USER" GITEA_WORK_DIR="$GITEA_WORK" "$GITEA_BIN" dump --config "$GITEA_CFG" --file forge.zip >/dev/null
      sha=$(sha256sum forge.zip | awk '{print $1}')
      obj="${GCS_TARGET%/}/forge-$(date -u +%Y%m%dT%H%M%SZ)-${sha}.zip"
      gcloud storage cp forge.zip "$obj" >/dev/null
      gcloud storage cp "$obj" readback.zip >/dev/null
      rsha=$(sha256sum readback.zip | awk '{print $1}')
      [ "$sha" = "$rsha" ] || fail "GCS backup readback SHA mismatch."
      BACKUP_STATE="verified:$obj"
      ok "GCS backup readback verified"
    else
      BACKUP_STATE="blocked:gcloud_not_authenticated"
      warn "Forge is healthy; GCS auth is the remaining seam."
    fi
  else
    BACKUP_STATE="blocked:gcloud_missing"
    warn "Forge is healthy; install/authenticate gcloud on the VM to enable GCS backup."
  fi
fi

public=$(curl -fsS --max-time 5 https://api.ipify.org 2>/dev/null || true)
[ -n "$public" ] || public=UNKNOWN
sudo tee "$REPORT" >/dev/null <<REPORT_EOF
HOME_CENTER_CLOUD_FORGE_V1
result=forge_verified
public_ip=$public
web=http://$public:$HTTP_PORT/
git_ssh=ssh://git@$public:$SSH_PORT/drew/REPO.git
gitea_version=$($GITEA_BIN --version | head -n 1)
gcs_backup=$BACKUP_STATE
manual_next=Allow inbound TCP $HTTP_PORT and $SSH_PORT in the cloud firewall/security list; then open the web URL. If initial admin was created: sudo cat /root/gitea-initial-admin.txt
REPORT_EOF
sudo cat "$REPORT"
REMOTE_EOF
  chmod 700 "$REMOTE"
}

deliver(){
  make_remote
  say "Delivering durable installer to VM"
  scp -P "$FORGE_PORT" -o StrictHostKeyChecking=accept-new "$REMOTE" "$FORGE_USER@$FORGE_HOST:/tmp/home-center-forge-install.sh"
  ok "Remote installer delivered"
  say "Executing remote forge install"
  gcs_q=$(printf "%s" "$GCS_TARGET" | sed "s/'/'\\''/g")
  ssh_base "chmod 700 /tmp/home-center-forge-install.sh && GCS_TARGET='$gcs_q' /tmp/home-center-forge-install.sh"
}

main(){
  ensure_termux_tools
  ensure_key
  collect_target
  prove_ssh
  deliver
  printf '\n[done] Canonical state: %s\n' "$STATE_FILE"
  printf '[done] Log: %s\n' "$LOG_FILE"
  printf '[done] Rerun this same command safely after any reported manual seam.\n'
}

main "$@"
