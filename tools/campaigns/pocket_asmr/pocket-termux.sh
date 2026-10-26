#!/usr/bin/env bash
set -Eeuo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export POCKET_ASMR_URL="${POCKET_ASMR_URL:-https://thecauldron-2.tail574fdf.ts.net:8443}"
export POCKET_ASMR_TOKEN="${POCKET_ASMR_TOKEN:-$HOME/.config/pocket-asmr/token}"
CAULDRON="${POCKET_CAULDRON_COMMAND:-cauldron}"
CMD='C:\Users\dclar\PocketASMRGit\tools\campaigns\pocket_asmr\pocket-service.cmd'
step="startup"
trap 'rc=$?; echo "POCKET_RESULT=FAIL STEP=$step EXIT=$rc" >&2' ERR
remote(){ command -v "$CAULDRON" >/dev/null || { echo "BLOCKED: cauldron missing" >&2; return 2; }; "$CAULDRON" "$1"; }
pair(){
 step=pair
 mkdir -p "$(dirname "$POCKET_ASMR_TOKEN")"
 umask 077
 tmp="$(mktemp)"
 trap 'rm -f "$tmp"' RETURN
 remote 'cmd /d /c type C:\Users\dclar\PocketASMR\gateway-token.txt' >"$tmp"
 python - "$tmp" "$POCKET_ASMR_TOKEN" <<'PY'
import os,re,sys,pathlib
raw=pathlib.Path(sys.argv[1]).read_bytes().decode("utf-8","replace")
clean=re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]","",raw)
clean=re.sub(r"\x1b\][^\x07]*(?:\x07|\x1b\\)","",clean)
candidates=re.findall(r"(?<![A-Za-z0-9_+/=-])[A-Za-z0-9_+/=-]{43}(?![A-Za-z0-9_+/=-])",clean)
unique=list(dict.fromkeys(candidates))
if len(unique)!=1:
 raise SystemExit("PAIR=BLOCKED CANDIDATES="+str(len(unique))+" (no credentials displayed)")
p=pathlib.Path(sys.argv[2])
temporary=p.with_name(p.name+".new")
temporary.write_text(unique[0]+"\n")
os.chmod(temporary,0o600)
temporary.replace(p)
print("PAIR=STORED_PRIVATE")
PY
}
doctor(){
 step=doctor
 python - "$POCKET_ASMR_URL" "$POCKET_ASMR_TOKEN" <<'PY'
import json,urllib.request,urllib.error,pathlib,sys
url,tokenfile=sys.argv[1:]
token=pathlib.Path(tokenfile)
if not token.is_file():raise SystemExit("DOCTOR=BLOCKED NO_TOKEN; run pocket pair")
req=urllib.request.Request(url+"/asmr/health",headers={"Authorization":"Bearer "+token.read_text().strip()})
try:
 with urllib.request.urlopen(req,timeout=15) as r:
  obj=json.load(r)
  print("HTTPS=PASS CODE="+str(r.status))
  print("GATEWAY="+str(obj.get("gateway","unknown")))
  print("UPSTREAM="+str(obj.get("upstream","unknown"))[:250])
except urllib.error.HTTPError as e:
 print("DOCTOR=BLOCKED HTTP="+str(e.code))
 raise SystemExit(2)
except Exception as e:raise SystemExit("DOCTOR=BLOCKED "+type(e).__name__+" "+str(e)[:120])
PY
}
sample(){
 step=sample
 python - "$HERE/pocket-api-client.py" <<'PY'
import sys,pathlib,tempfile,time,importlib.util
path=pathlib.Path(tempfile.gettempdir())/"pocket-asmr-probe.txt"
path.write_text("Hello. This is Ritsu, checking the Pocket ASMR audio connection.",encoding="utf-8")
spec=importlib.util.spec_from_file_location("pocket_api_client",sys.argv[1])
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
job=module.submit(str(path),"whisper")
print("CANARY_JOB="+job,flush=True)
for attempt in range(36):
 time.sleep(5)
 if module.check(job):
  module.pull(job)
  print("CANARY_AUDIO=DOWNLOADED",flush=True)
  break
else:
 raise SystemExit("CANARY=INCOMPLETE JOB="+job+" (resume: pocket status "+job+")")

PY
}
case "${1:-go}" in
 install)
  step=install
  mkdir -p "${PREFIX:-$HOME/.local}/bin"
  printf '#!/usr/bin/env bash\nexec bash "%s/pocket-termux.sh" "$@"\n' "$HERE" > "${PREFIX:-$HOME/.local}/bin/pocket"
  chmod 700 "${PREFIX:-$HOME/.local}/bin/pocket"
  echo 'POCKET=INSTALLED' ;;
 go)
  pair
  doctor
  sample
  echo 'POCKET_GO=PASS_CANARY_DOWNLOADED' ;;
 pair) pair ;;
 doctor) doctor ;;
 on|off|service-status)
  step=service
  mode="$1"; [[ "$mode" == service-status ]] && mode=status
  remote "cmd /d /c call $CMD $mode" ;;
 asmr)
  shift
  if [[ "${1:-}" == "" || "${1:-}" == --voice ]];then set -- "$HERE/asmr.txt" "$@";fi
  exec python "$HERE/pocket-api-client.py" asmr "$@" ;;
 status|pull)
  mode="$1";shift;exec python "$HERE/pocket-api-client.py" "$mode" "$@" ;;
 *) echo 'Usage: pocket install|go|pair|doctor|on|off|asmr|status JOB|pull JOB';exit 2;;
esac