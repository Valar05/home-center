#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="${HC_REPO_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"
STATE="$HOME/.local/state/home-center/atom-vlad-install"
mkdir -p "$STATE"

cd "$ROOT"

sh tools/install_atom_phone.sh
bash tools/setup_vlad_swarm_daemon.sh

ATOM_STATUS="$(curl -fsS http://127.0.0.1:8788/v1/atom/status)"
python3 - "$ATOM_STATUS" "$STATE/receipt.json" <<'PY'
import json,sys,time
status=json.loads(sys.argv[1])
vlad=status.get('vlad') or {}
ok=(status.get('ok') is True and status.get('service')=='Atom' and vlad.get('loaded') is True)
receipt={
  'schema':'atom-vlad-phone-install-v1',
  'ok':ok,
  'installedAtEpoch':int(time.time()),
  'atom':{'online':status.get('state')=='online','service':status.get('service')},
  'vlad':vlad,
  'operatorSurface':'Atom',
  'daemon':'vlad-swarm',
}
open(sys.argv[2],'w',encoding='utf-8').write(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps(receipt,sort_keys=True))
raise SystemExit(0 if ok else 2)
PY
