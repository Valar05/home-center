#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
STATE_DIR="$HOME/.local/state/home-center/coding-dungeon-v2"
CONFIG_DIR="$HOME/.config/home-center"
REGISTRY="$CONFIG_DIR/dungeon-workspaces.v2.json"

mkdir -p "$HOME/bin" "$STATE_DIR/jobs" "$STATE_DIR/runs" "$STATE_DIR/worktrees" "$STATE_DIR/locks" "$CONFIG_DIR"
pkg install -y python git tmux nodejs >/dev/null

if ! command -v codex >/dev/null 2>&1; then
  npm install -g @openai/codex || printf '%s\n' 'NOTICE: Codex CLI install failed; the fixed local-inference decay path remains available.' >&2
fi

python - "$ROOT" "$REGISTRY" <<'PY'
import json, sys
from pathlib import Path

root = str(Path(sys.argv[1]).resolve())
path = Path(sys.argv[2])
if path.exists():
    value = json.loads(path.read_text(encoding='utf-8'))
    if value.get('schema') != 'home-center.dungeon-workspaces.v2' or not isinstance(value.get('workspaces'), dict):
        raise SystemExit('BLOCKED: existing dungeon workspace registry has an incompatible schema')
else:
    value = {'schema':'home-center.dungeon-workspaces.v2','workspaces':{}}
value['workspaces']['home-center'] = {
    'root': root,
    'baseRef': 'HEAD',
    'verification': {
        'fast': [['node','functions/dungeon_run_contract.test.js'],['python','tools/test_mobile_coding_dungeon_v2.py']],
        'default': [['node','tools/fortress_dungeon_ingress_contract_test.mjs'],['node','functions/dungeon_run_contract.test.js'],['python','tools/test_mobile_coding_dungeon_v2.py']],
        'full': [['sh','tools/home_center_ci_validate.sh']],
    },
}
path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
path.chmod(0o600)
PY

PYTHON_BIN="$(command -v python)"
cat > "$HOME/bin/dungeon-v2" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec '$PYTHON_BIN' '$ROOT/tools/mobile_coding_dungeon_v2.py' "\$@"
EOF
chmod +x "$HOME/bin/dungeon-v2" "$ROOT/tools/mobile_coding_dungeon_v2.py"

python "$ROOT/tools/mobile_coding_dungeon_v2.py" doctor --registry "$REGISTRY"
if [ -f "$CONFIG_DIR/codex-hub.json" ]; then
  bash "$ROOT/tools/setup_android_phone_home_center_relay.sh"
else
  printf '%s\n' 'NOTICE: Home Center pairing is absent; pair once, then restart the phone relay to advertise coding_dungeon_v2.' >&2
fi
printf '%s\n' 'MOBILE CODING DUNGEON V2 INSTALLED.'
printf '%s\n' 'Ingress remains dormant until a typed dungeon_run is admitted through Home Center.'
