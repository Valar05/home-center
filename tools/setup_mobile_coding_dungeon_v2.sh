#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
umask 077

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
STATE_DIR="$HOME/.local/state/home-center/coding-dungeon-v2"
CONFIG_DIR="$HOME/.config/home-center"
REGISTRY="$CONFIG_DIR/dungeon-workspaces.v2.json"

mkdir -p "$HOME/bin" "$STATE_DIR/jobs" "$STATE_DIR/runs" "$STATE_DIR/worktrees" "$STATE_DIR/locks" "$CONFIG_DIR"
pkg install -y python git tmux nodejs >/dev/null

if ! git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  printf '%s\n' 'BLOCKED: Coding Dungeon must be installed from a Git worktree.' >&2
  exit 2
fi
SOURCE_COMMIT="$(git -C "$ROOT" rev-parse HEAD)"
SOURCE_BRANCH="$(git -C "$ROOT" symbolic-ref --quiet --short HEAD || true)"
if [ "$SOURCE_BRANCH" != "main" ]; then
  printf '%s\n' 'BLOCKED: Coding Dungeon phone installation requires the reviewed main branch.' >&2
  exit 2
fi
if [ -n "$(git -C "$ROOT" status --porcelain=v1 --untracked-files=no)" ]; then
  printf '%s\n' 'BLOCKED: tracked phone checkout changes must be reviewed before Coding Dungeon installation.' >&2
  exit 2
fi

if ! command -v codex >/dev/null 2>&1; then
  npm install -g @openai/codex || printf '%s\n' 'NOTICE: Codex CLI install failed; the fixed local-inference decay path remains available.' >&2
fi

python - "$ROOT" "$REGISTRY" "$SOURCE_COMMIT" "$SOURCE_BRANCH" <<'PY'
import json, os, sys
from pathlib import Path

root = str(Path(sys.argv[1]).resolve())
path = Path(sys.argv[2])
source_commit = sys.argv[3].strip().lower()
source_branch = sys.argv[4].strip()
if len(source_commit) != 40 or any(ch not in '0123456789abcdef' for ch in source_commit):
    raise SystemExit('BLOCKED: source commit is not an exact Git SHA')
if source_branch != 'main':
    raise SystemExit('BLOCKED: source branch must be main')
if path.exists():
    value = json.loads(path.read_text(encoding='utf-8'))
    if value.get('schema') != 'home-center.dungeon-workspaces.v2' or not isinstance(value.get('workspaces'), dict):
        raise SystemExit('BLOCKED: existing dungeon workspace registry has an incompatible schema')
else:
    value = {'schema':'home-center.dungeon-workspaces.v2','workspaces':{}}
value['workspaces']['home-center'] = {
    'root': root,
    'baseRef': source_commit,
    'sourceCommit': source_commit,
    'sourceBranch': source_branch,
    'verification': {
        'fast': [['node','functions/dungeon_run_contract.test.js'],['python','tools/test_mobile_coding_dungeon_v2.py']],
        'default': [['node','tools/fortress_dungeon_ingress_contract_test.mjs'],['node','functions/dungeon_run_contract.test.js'],['python','tools/test_mobile_coding_dungeon_v2.py']],
        'full': [['sh','tools/home_center_ci_validate.sh']],
    },
}
tmp = path.with_suffix(path.suffix + f'.{os.getpid()}.tmp')
with tmp.open('w', encoding='utf-8') as handle:
    handle.write(json.dumps(value, indent=2) + '\n')
    handle.flush()
    os.fsync(handle.fileno())
os.replace(tmp, path)
directory = os.open(path.parent, os.O_RDONLY)
try:
    os.fsync(directory)
finally:
    os.close(directory)
path.chmod(0o600)
PY

PYTHON_BIN="$(command -v python)"
cat > "$HOME/bin/dungeon-v2" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec '$PYTHON_BIN' '$ROOT/tools/mobile_coding_dungeon_v2.py' "\$@"
EOF
chmod +x "$HOME/bin/dungeon-v2"

python "$ROOT/tools/mobile_coding_dungeon_v2.py" doctor --registry "$REGISTRY"
if [ -f "$CONFIG_DIR/codex-hub.json" ]; then
  bash "$ROOT/tools/setup_android_phone_home_center_relay.sh"
else
  printf '%s\n' 'NOTICE: Home Center pairing is absent; pair once, then restart the phone relay to advertise coding_dungeon_v2.' >&2
fi
printf '%s\n' 'MOBILE CODING DUNGEON V2 INSTALLED.'
printf '%s\n' 'Ingress remains dormant until a typed dungeon_run is admitted through Home Center.'
