#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
STATE="$HOME/.local/state/home-center/venice"
MODEL="${VENICE_REVIEW_MODEL:-qwen2.5-coder:1.5b}"
HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}"
mkdir -p "$STATE"

alive() { curl -fsS "${HOST%/}/api/tags" >/dev/null 2>&1; }

if ! alive; then
  if ! command -v ollama >/dev/null 2>&1; then
    python3 - "$STATE/status.json" <<'PY'
import json,sys,time
obj={'schema':'venice-local-health-v1','ok':False,'error':'ollama_missing','at':int(time.time())}
open(sys.argv[1],'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n')
print(json.dumps(obj))
PY
    exit 2
  fi
  (nohup ollama serve >>"$STATE/ollama.log" 2>&1 </dev/null & echo $! >"$STATE/ollama.pid")
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    alive && break
    sleep 1
  done
fi
alive || { echo 'Venice blocked: Ollama did not become healthy' >&2; exit 3; }

if ! ollama list 2>/dev/null | awk 'NR>1 {print $1}' | grep -Eq "^${MODEL}(:|$)"; then
  ollama pull "$MODEL"
fi

python3 - "$STATE/status.json" "$MODEL" "$HOST" <<'PY'
import json,sys,time
path,model,host=sys.argv[1:]
obj={'schema':'venice-local-health-v1','ok':True,'model':model,'host':host,'at':int(time.time())}
open(path,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n')
print(json.dumps(obj,sort_keys=True))
PY
