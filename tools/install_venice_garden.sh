#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE="${HC_VENICE_GARDEN_STATE:-$HOME/.local/state/home-center/venice-garden}"
BIN="${HC_VENICE_GARDEN_BIN:-$HOME/.local/bin}"
mkdir -p "$STATE" "$BIN"

cat > "$BIN/venice-garden" <<EOF
#!/usr/bin/env bash
exec "${PYTHON:-python3}" "$ROOT/tools/venice_garden.py" "\$@"
EOF
chmod +x "$BIN/venice-garden"

if command -v systemctl >/dev/null 2>&1 && systemctl --user show-environment >/dev/null 2>&1; then
  UNIT_DIR="$HOME/.config/systemd/user"
  mkdir -p "$UNIT_DIR"
  cat > "$UNIT_DIR/home-center-venice-garden.service" <<EOF
[Unit]
Description=Home Center Venice Garden
After=default.target

[Service]
Type=simple
WorkingDirectory=$ROOT
ExecStart=${PYTHON:-python3} $ROOT/tools/venice_garden.py daemon
Restart=always
RestartSec=15
Environment=HC_VENICE_GARDEN_STATE=$STATE

[Install]
WantedBy=default.target
EOF
  systemctl --user daemon-reload
  systemctl --user enable --now home-center-venice-garden.service
  mode="systemd-user"
elif command -v tmux >/dev/null 2>&1; then
  tmux has-session -t venice-governor-core 2>/dev/null || \
    tmux new-session -d -s venice-governor-core "cd '$ROOT' && '${PYTHON:-python3}' tools/venice_garden.py daemon"
  mode="tmux"
else
  nohup "${PYTHON:-python3}" "$ROOT/tools/venice_garden.py" daemon >>"$STATE/governor.log" 2>&1 &
  printf '%s\n' "$!" > "$STATE/governor.pid"
  mode="nohup"
fi

"${PYTHON:-python3}" "$ROOT/tools/venice_garden.py" observe >/dev/null
printf '{"schema":"home-center.venice-garden-install.v1","ok":true,"mode":"%s","state":"%s","command":"%s"}\n' "$mode" "$STATE" "$BIN/venice-garden"
