#!/bin/bash
set -euo pipefail
GITEA_VERSION="$1"
RUNNER_VERSION="$2"
FORGE_NAME="$3"
CLOUD_RUNNER_LABEL="$4"

GITEA_USER=git
GITEA_HOME=/home/git
GITEA_WORK=/var/lib/gitea
GITEA_CFG=/etc/gitea/app.ini
GITEA_BIN=/usr/local/bin/gitea
RUNNER_USER=gitea-runner
RUNNER_HOME=/var/lib/gitea-runner
RUNNER_BIN=/usr/local/bin/gitea-runner

say(){ printf '\n[forge-remote] %s\n' "$*"; }
ok(){ printf '[ok] %s\n' "$*"; }
die(){ printf '[blocked] %s\n' "$*" >&2; exit 1; }

sudo true
arch="$(uname -m)"
case "$arch" in x86_64|amd64) garch=amd64 ;; aarch64|arm64) garch=arm64 ;; *) die "Unsupported CPU: $arch" ;; esac

say "Installing forge runtime dependencies"
sudo env DEBIAN_FRONTEND=noninteractive apt-get update -y
sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y \
  git curl ca-certificates sqlite3 openssl python3 nodejs npm openjdk-17-jdk-headless unzip

if ! command -v tailscale >/dev/null 2>&1; then
  say "Installing Tailscale"
  curl -fsSL https://tailscale.com/install.sh | sh
fi
sudo systemctl enable --now tailscaled
if ! sudo tailscale status >/dev/null 2>&1; then
  say "Tailscale needs one authorization. Open the URL it prints; this command resumes automatically."
  if [ -n "${HC_TAILSCALE_AUTH_KEY:-}" ]; then
    sudo tailscale up --hostname="$FORGE_NAME" --auth-key="$HC_TAILSCALE_AUTH_KEY"
  else
    sudo tailscale up --hostname="$FORGE_NAME"
  fi
else
  sudo tailscale set --hostname="$FORGE_NAME" >/dev/null 2>&1 || true
fi
TS_IP="$(sudo tailscale ip -4 | head -n1)"
TS_DNS="$(sudo tailscale status --json | python3 -c 'import json,sys; d=json.load(sys.stdin); print((d.get("Self") or {}).get("DNSName","").rstrip("."))')"
[ -n "$TS_IP" ] || die "Tailscale is up but no IPv4 tailnet address was returned."
[ -n "$TS_DNS" ] || TS_DNS="$FORGE_NAME"

if ! id "$GITEA_USER" >/dev/null 2>&1; then
  sudo adduser --system --shell /bin/bash --group --disabled-password --home "$GITEA_HOME" "$GITEA_USER"
fi
sudo mkdir -p "$GITEA_WORK"/{custom,data,log} /etc/gitea /var/backups/gitea
sudo chown -R "$GITEA_USER:$GITEA_USER" "$GITEA_WORK" "$GITEA_HOME"
sudo chown root:"$GITEA_USER" /etc/gitea

say "Installing Gitea $GITEA_VERSION"
tmp="/tmp/gitea-$GITEA_VERSION-linux-$garch"
curl -fL --retry 4 "https://dl.gitea.com/gitea/$GITEA_VERSION/gitea-$GITEA_VERSION-linux-$garch" -o "$tmp"
curl -fL --retry 4 "https://dl.gitea.com/gitea/$GITEA_VERSION/gitea-$GITEA_VERSION-linux-$garch.sha256" -o "$tmp.sha256"
( cd /tmp; sha256sum -c "$(basename "$tmp.sha256")" )
chmod 755 "$tmp"
sudo install -m 0755 "$tmp" "$GITEA_BIN"

if [ ! -s "$GITEA_CFG" ]; then
  secret="$(openssl rand -hex 32)"
  internal="$(openssl rand -hex 32)"
  lfs="$(openssl rand -hex 32)"
  sudo tee "$GITEA_CFG" >/dev/null <<CFG
APP_NAME = Home Center Forge
RUN_USER = $GITEA_USER
RUN_MODE = prod
WORK_PATH = $GITEA_WORK
[repository]
ROOT = $GITEA_WORK/data/gitea-repositories
DEFAULT_BRANCH = main
FORCE_PRIVATE = true
[database]
DB_TYPE = sqlite3
PATH = $GITEA_WORK/data/gitea.db
[server]
DOMAIN = $TS_IP
HTTP_ADDR = $TS_IP
HTTP_PORT = 3000
ROOT_URL = http://$TS_IP:3000/
START_SSH_SERVER = true
SSH_DOMAIN = $TS_IP
SSH_LISTEN_HOST = $TS_IP
SSH_LISTEN_PORT = 2222
SSH_PORT = 2222
LFS_START_SERVER = true
LFS_JWT_SECRET = $lfs
[security]
INSTALL_LOCK = true
SECRET_KEY = $secret
INTERNAL_TOKEN = $internal
[service]
DISABLE_REGISTRATION = true
REQUIRE_SIGNIN_VIEW = true
DEFAULT_KEEP_EMAIL_PRIVATE = true
[actions]
ENABLED = true
[log]
MODE = console
LEVEL = Info
CFG
  sudo chown root:"$GITEA_USER" "$GITEA_CFG"
  sudo chmod 0640 "$GITEA_CFG"
else
  sudo python3 - "$GITEA_CFG" "$TS_IP" "$TS_DNS" <<'PY'
import configparser,sys
p,ip,dns=sys.argv[1:]
c=configparser.ConfigParser(interpolation=None, strict=False)
c.optionxform=str
c.read(p)
for sec in ('server','actions','service','repository'):
    if not c.has_section(sec): c.add_section(sec)
c['server']['DOMAIN']=ip
c['server']['HTTP_ADDR']=ip
c['server']['HTTP_PORT']='3000'
c['server']['ROOT_URL']=f'http://{ip}:3000/'
c['server']['START_SSH_SERVER']='true'
c['server']['SSH_DOMAIN']=ip
c['server']['SSH_LISTEN_HOST']=ip
c['server']['SSH_LISTEN_PORT']='2222'
c['server']['SSH_PORT']='2222'
c['actions']['ENABLED']='true'
c['service']['DISABLE_REGISTRATION']='true'
c['service']['REQUIRE_SIGNIN_VIEW']='true'
c['repository']['FORCE_PRIVATE']='true'
with open(p,'w') as f:c.write(f)
PY
fi

sudo tee /etc/systemd/system/gitea.service >/dev/null <<SERVICE
[Unit]
Description=Home Center private Gitea forge
After=network-online.target tailscaled.service
Wants=network-online.target
Requires=tailscaled.service
[Service]
User=$GITEA_USER
Group=$GITEA_USER
WorkingDirectory=$GITEA_WORK
Environment=HOME=$GITEA_HOME
Environment=GITEA_WORK_DIR=$GITEA_WORK
ExecStart=$GITEA_BIN web --config $GITEA_CFG
Restart=always
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true
[Install]
WantedBy=multi-user.target
SERVICE
sudo systemctl daemon-reload
sudo systemctl enable --now gitea
sleep 2
sudo systemctl is-active --quiet gitea || { sudo journalctl -u gitea -n 80 --no-pager; exit 1; }
curl -fsS --max-time 10 "http://$TS_IP:3000/" >/dev/null

users="$(sudo -u "$GITEA_USER" GITEA_WORK_DIR="$GITEA_WORK" "$GITEA_BIN" admin user list --config "$GITEA_CFG" 2>/dev/null || true)"
if ! printf '%s\n' "$users" | grep -qE '(^|[[:space:]])drew([[:space:]]|$)'; then
  pass="$(openssl rand -hex 18)"
  sudo -u "$GITEA_USER" GITEA_WORK_DIR="$GITEA_WORK" "$GITEA_BIN" admin user create \
    --config "$GITEA_CFG" --username drew --password "$pass" \
    --email drew@local.invalid --admin --must-change-password=false >/dev/null
  sudo sh -c "umask 077; printf '%s\n' 'GITEA_ADMIN_USER=drew' 'GITEA_ADMIN_PASSWORD=$pass' > /root/gitea-admin.env"
fi

if ! id "$RUNNER_USER" >/dev/null 2>&1; then
  sudo useradd --system --create-home --home-dir "$RUNNER_HOME" --shell /bin/bash "$RUNNER_USER"
fi
sudo install -d -m 700 -o "$RUNNER_USER" -g "$RUNNER_USER" "$RUNNER_HOME"

say "Installing Gitea Runner $RUNNER_VERSION"
rtmp="/tmp/gitea-runner-$RUNNER_VERSION-linux-$garch"
curl -fL --retry 4 "https://dl.gitea.com/gitea-runner/$RUNNER_VERSION/gitea-runner-$RUNNER_VERSION-linux-$garch" -o "$rtmp"
curl -fL --retry 4 "https://dl.gitea.com/gitea-runner/$RUNNER_VERSION/gitea-runner-$RUNNER_VERSION-linux-$garch.sha256" -o "$rtmp.sha256"
( cd /tmp; sha256sum -c "$(basename "$rtmp.sha256")" )
chmod 755 "$rtmp"
sudo install -m 0755 "$rtmp" "$RUNNER_BIN"

if [ ! -s "$RUNNER_HOME/.runner" ]; then
  token="$(sudo -u "$GITEA_USER" GITEA_WORK_DIR="$GITEA_WORK" "$GITEA_BIN" \
    actions generate-runner-token --config "$GITEA_CFG")"
  sudo -u "$RUNNER_USER" bash -lc "
    cd '$RUNNER_HOME'
    '$RUNNER_BIN' register --no-interactive \
      --instance 'http://$TS_IP:3000/' \
      --token '$token' \
      --name '$CLOUD_RUNNER_LABEL' \
      --labels '$CLOUD_RUNNER_LABEL:host'
  "
fi

sudo tee /etc/systemd/system/gitea-runner.service >/dev/null <<SERVICE
[Unit]
Description=Home Center Gitea free-compute runner
After=gitea.service
Requires=gitea.service
[Service]
User=$RUNNER_USER
Group=$RUNNER_USER
WorkingDirectory=$RUNNER_HOME
Environment=HOME=$RUNNER_HOME
ExecStart=$RUNNER_BIN daemon --labels $CLOUD_RUNNER_LABEL:host
Restart=always
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
MemoryMax=600M
CPUQuota=90%
[Install]
WantedBy=multi-user.target
SERVICE
sudo systemctl daemon-reload
sudo systemctl enable --now gitea-runner
sleep 2
sudo systemctl is-active --quiet gitea-runner || { sudo journalctl -u gitea-runner -n 80 --no-pager; exit 1; }

cat <<REPORT
HOME_CENTER_PRIVATE_FORGE_V3
result=forge_verified
tailscale_ip=$TS_IP
tailscale_dns=$TS_DNS
web=http://$TS_IP:3000/
git_ssh=ssh://git@$TS_IP:2222/drew/REPO.git
gitea_version=$("$GITEA_BIN" --version | head -n1)
runner_version=$("$RUNNER_BIN" --version | head -n1)
cloud_runner=$CLOUD_RUNNER_LABEL
gitea_active=$(systemctl is-active gitea)
runner_active=$(systemctl is-active gitea-runner)
REPORT
