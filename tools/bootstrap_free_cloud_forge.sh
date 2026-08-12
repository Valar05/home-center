#!/bin/sh
# Home Center free cloud forge bootstrap.
# Real Git forge on a free-tier Linux VM; GCS is backup only.
# POSIX sh by design for Termux handoff safety.
set -eu

STATE_DIR="$HOME/.home-center/cloud-forge"
STATE_FILE="$STATE_DIR/state.env"
PROVISIONED_FILE="$STATE_DIR/gcp-provisioned.env"
LOG_FILE="$STATE_DIR/bootstrap.log"
mkdir -p "$STATE_DIR"
: > "$LOG_FILE" 2>/dev/null || true

say(){ printf '\n[forge] %s\n' "$*"; }
ok(){ printf '[ok] %s\n' "$*"; }
warn(){ printf '[warn] %s\n' "$*" >&2; }
fail(){ printf '[blocked] %s\n' "$*" >&2; exit 1; }
have(){ command -v "$1" >/dev/null 2>&1; }

load_state(){
  if [ -f "$STATE_FILE" ]; then . "$STATE_FILE"; fi
  if [ -f "$PROVISIONED_FILE" ]; then . "$PROVISIONED_FILE"; fi
  : "${FORGE_HOST:=}"
  : "${FORGE_USER:=forge}"
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
  if [ -n "$def" ]; then printf '%s [%s]: ' "$prompt" "$def"; else printf '%s: ' "$prompt"; fi
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
  mkdir -p "$HOME/.ssh"; chmod 700 "$HOME/.ssh"
  if [ ! -f "$HOME/.ssh/id_ed25519" ]; then ssh-keygen -q -t ed25519 -f "$HOME/.ssh/id_ed25519" -N '' -C home-center-phone; fi
  ok "Phone SSH identity ready"
}

collect_target(){
  load_state
  say "Cloud forge target"
  [ -n "$FORGE_HOST" ] || fail "No provisioned forge VM found. Run tools/provision_gcp_free_forge_vm.sh first."
  case "$FORGE_PORT" in *[!0-9]*|'') fail "SSH port must be numeric.";; esac
  if [ -z "$GCS_TARGET" ]; then
    printf 'Optional GCS backup target (gs://bucket/prefix, Enter to defer): '
    IFS= read -r GCS_TARGET || true
  fi
  save_state
  ok "Using $FORGE_USER@$FORGE_HOST:$FORGE_PORT"
}

ssh_base(){ ssh -p "$FORGE_PORT" -o ConnectTimeout=12 -o ServerAliveInterval=20 -o ServerAliveCountMax=3 -o StrictHostKeyChecking=accept-new "$FORGE_USER@$FORGE_HOST" "$@"; }

prove_ssh(){
  say "Proving SSH lane"
  tries=0
  while [ "$tries" -lt 12 ]; do
    if ssh_base 'printf "SSH_OK\\n"; uname -srm; command -v sudo >/dev/null'; then ok "SSH lane proven"; return 0; fi
    tries=$((tries + 1)); sleep 5
  done
  fail "VM exists but its startup key/bootstrap is not accepting SSH yet. Rerun this same command; do not recreate the VM."
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
case "$arch" in x86_64|amd64) garch=amd64 ;; aarch64|arm64) garch=arm64 ;; *) fail "Unsupported CPU architecture: $arch" ;; esac
if have apt-get; then
  say "Installing minimal forge dependencies"
  sudo env DEBIAN_FRONTEND=noninteractive apt-get update -y
  sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y git curl ca-certificates sqlite3 openssl unzip
else fail "This bootstrap currently requires an Ubuntu/Debian VM."; fi
if ! id "$GITEA_USER" >/dev/null 2>&1; then sudo adduser --system --shell /bin/sh --group --disabled-password --home "$GITEA_HOME" "$GITEA_USER"; fi
sudo mkdir -p "$GITEA_WORK"/custom "$GITEA_WORK"/data "$GITEA_WORK"/log /etc/gitea /var/backups/gitea
sudo chown -R "$GITEA_USER:$GITEA_USER" "$GITEA_WORK" "$GITEA_HOME"
sudo chown root:"$GITEA_USER" /etc/gitea
if [ ! -x "$GITEA_BIN" ]; then
  say "Discovering current Gitea release"
  ver=$(curl -fsSL https://dl.gitea.com/gitea/ | sed -n 's/.*href="\([0-9][0-9.]*\)\/.*/\1/p' | sort -V | tail -n 1)
  [ -n "$ver" ] || fail "Could not discover a Gitea release from dl.gitea.com."
  url="https://dl.gitea.com/gitea/$ver/gitea-$ver-linux-$garch"; tmp=/tmp/gitea.$$
  curl -fL --retry 4 --retry-delay 2 "$url" -o "$tmp"; chmod 755 "$tmp"; "$tmp" --version >/dev/null || fail "Downloaded Gitea binary would not execute."
  sudo install -m 0755 "$tmp" "$GITEA_BIN"; rm -f "$tmp"
else ok "Existing Gitea binary preserved"; fi
if [ ! -s "$GITEA_CFG" ]; then
  secret=$(openssl rand -hex 32); token=$(openssl rand -hex 32); lfs=$(openssl rand -hex 32)
  host=$(hostname -I 2>/dev/null | awk '{print $1}'); [ -n "$host" ] || host=127.0.0.1
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
  sudo chown root:"$GITEA_USER" "$GITEA_CFG"; sudo chmod 0640 "$GITEA_CFG"
else ok "Existing Gitea config preserved"; fi
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
sudo systemctl daemon-reload; sudo systemctl enable --now gitea; sleep 2
sudo systemctl is-active --quiet gitea || { sudo systemctl status gitea --no-pager || true; fail "Gitea service is not active."; }
curl -fsS --max-time 10 "http://127.0.0.1:$HTTP_PORT/" >/dev/null || fail "Gitea HTTP did not answer locally."
ok "Real Gitea forge is running"
users=$(sudo -u "$GITEA_USER" GITEA_WORK_DIR="$GITEA_WORK" "$GITEA_BIN" admin user list --config "$GITEA_CFG" 2>/dev/null || true)
count=$(printf '%s\n' "$users" | sed '1d;/^[[:space:]]*$/d' | wc -l | tr -d ' ')
if [ "$count" = 0 ]; then
  pass=$(openssl rand -hex 16)
  sudo -u "$GITEA_USER" GITEA_WORK_DIR="$GITEA_WORK" "$GITEA_BIN" admin user create --config "$GITEA_CFG" --username drew --password "$pass" --email drew@local.invalid --admin --must-change-password=true >/dev/null
  sudo sh -c "umask 077; printf '%s\\n' 'username=drew' 'password=$pass' > /root/gitea-initial-admin.txt"
  warn "Initial admin credential stored on VM at /root/gitea-initial-admin.txt"
fi
BACKUP_STATE=deferred
public6=$(ip -6 addr show scope global 2>/dev/null | sed -n 's/.*inet6 \([^/]*\).*/\1/p' | head -n 1 || true)
[ -n "$public6" ] || public6=UNKNOWN
sudo tee "$REPORT" >/dev/null <<REPORT_EOF
HOME_CENTER_CLOUD_FORGE_V2
result=forge_verified
public_ipv6=$public6
web=http://[$public6]:$HTTP_PORT/
git_ssh=ssh://git@[$public6]:$SSH_PORT/drew/REPO.git
gitea_version=$($GITEA_BIN --version | head -n 1)
gcs_backup=$BACKUP_STATE
manual_next=Open the web URL, retrieve /root/gitea-initial-admin.txt once, change password, then create/import repositories. GCS backup remains the next seam if deferred.
REPORT_EOF
sudo cat "$REPORT"
REMOTE_EOF
  chmod 700 "$REMOTE"
}

deliver(){
  make_remote
  say "Delivering durable installer to VM"
  scp -P "$FORGE_PORT" -o StrictHostKeyChecking=accept-new "$REMOTE" "$FORGE_USER@[$FORGE_HOST]:/tmp/home-center-forge-install.sh"
  ok "Remote installer delivered"
  say "Executing remote forge install"
  gcs_q=$(printf "%s" "$GCS_TARGET" | sed "s/'/'\\''/g")
  ssh_base "chmod 700 /tmp/home-center-forge-install.sh && GCS_TARGET='$gcs_q' /tmp/home-center-forge-install.sh"
}

main(){ ensure_termux_tools; ensure_key; collect_target; prove_ssh; deliver; printf '\n[done] Canonical state: %s\n' "$STATE_FILE"; printf '[done] Log: %s\n' "$LOG_FILE"; }
main "$@"
