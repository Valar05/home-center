#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="${HC_REPO_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"
BIN="${PREFIX:-/data/data/com.termux/files/usr}/bin/fortress-resume"
STATE="$HOME/.local/state/home-center"
mkdir -p "$STATE" "$(dirname "$BIN")"
cat > "$BIN" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
exec bash $(printf '%q' "$ROOT/tools/fortress_phone_resume.sh") "\$@"
EOF
chmod 755 "$BIN"
python3 - "$BIN" "$STATE/fortress-resume-install.json" <<'PY'
import hashlib,json,sys,time
p,r=sys.argv[1:]
b=open(p,'rb').read()
obj={'schema':'fortress-resume-install-v1','ok':True,'path':p,'sha256':hashlib.sha256(b).hexdigest(),'installedAtEpoch':int(time.time())}
open(r,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n')
print(json.dumps(obj,indent=2,sort_keys=True))
PY
