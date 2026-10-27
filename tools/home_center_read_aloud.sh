#!/data/data/com.termux/files/usr/bin/sh
set -eu
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
WORKER="$ROOT/tools/pocket_tts_home_center_worker.py"
REQUESTS="${HOME_CENTER_POCKET_TTS_REQUESTS:-/storage/emulated/0/Download/HomeCenter/pocket-tts-requests}"
OUTPUT="${HOME_CENTER_POCKET_TTS_OUTPUT:-/storage/emulated/0/Documents/FortressAudio/HomeCenterPocketTts}"
CAMPAIGN="$OUTPUT/campaign"
MODE_FILE="$CAMPAIGN/backend"
LOG="$CAMPAIGN/worker.log"
HISTORY="$CAMPAIGN/history.jsonl"
SESSION="home-center-read-aloud"
PYTHON="/data/data/com.termux/files/usr/bin/python"
mkdir -p "$REQUESTS" "$OUTPUT" "$CAMPAIGN"
validate_backend() { case "$1" in local) printf '%s\n' local;; *) echo "Home Center read-aloud is local-only" >&2; exit 2;; esac; }
current_backend() { printf '%s\n' local; }
record() { event="$1"; detail="${2:-}"; EVENT="$event" DETAIL="$detail" "$PYTHON" - "$HISTORY" <<'PY2'
import json,os,sys,time
with open(sys.argv[1],'a',encoding='utf-8') as out: out.write(json.dumps({'atMs':int(time.time()*1000),'event':os.environ['EVENT'],'detail':os.environ['DETAIL']},sort_keys=True)+'\n')
PY2
}
start_worker() {
 backend="$(validate_backend "${1:-$(current_backend)}")"; printf '%s\n' "$backend" > "$MODE_FILE"
 HOME_CENTER_POCKET_TTS_BACKEND="$backend" "$PYTHON" "$WORKER" doctor >/dev/null
 if tmux has-session -t "$SESSION" 2>/dev/null; then echo "Home Center read-aloud already running backend=$backend"; return; fi
 if tmux has-session -t home-center-pocket-tts 2>/dev/null; then
  tmux kill-session -t home-center-pocket-tts
  record legacy_worker_retired "home-center-pocket-tts"
 fi
 command -v termux-wake-lock >/dev/null 2>&1 && termux-wake-lock >/dev/null 2>&1 || true
 tmux new-session -d -s "$SESSION" "env HOME_CENTER_POCKET_TTS_BACKEND='$backend' OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 nice -n 10 '$PYTHON' '$WORKER' serve --request-dir '$REQUESTS' >> '$LOG' 2>&1"
 sleep 1; tmux has-session -t "$SESSION" 2>/dev/null || { echo "worker failed; read $LOG" >&2; exit 1; }
 record start "$backend"; echo "Home Center read-aloud started backend=$backend"
}
stop_worker() { tmux kill-session -t "$SESSION" 2>/dev/null || true; record stop "$(current_backend)"; command -v termux-wake-unlock >/dev/null 2>&1 && termux-wake-unlock >/dev/null 2>&1 || true; echo "Home Center read-aloud stopped"; }
status_worker() { if tmux has-session -t "$SESSION" 2>/dev/null; then echo "running backend=$(current_backend) session=$SESSION"; [ -s "$OUTPUT/worker-heartbeat.json" ] && sed -n '1p' "$OUTPUT/worker-heartbeat.json"; else echo "stopped backend=$(current_backend)"; return 1; fi; }
repair_file() {
 file_id="$1"; [ -n "$file_id" ] || { echo "repair requires --file-id" >&2; exit 2; }
 ROOT="$ROOT" OUTPUT="$OUTPUT" FILE_ID="$file_id" "$PYTHON" - <<'PY2'
import json,os,shutil,time
from pathlib import Path
import sys
sys.path.insert(0,str(Path(os.environ['ROOT'])/'tools'))
from pocket_tts_render_v2 import validate_receipt
root=Path(os.environ['OUTPUT']); file_id=os.environ['FILE_ID']; stamp=time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())
quarantine=root/'quarantine'/stamp/file_id; quarantine.mkdir(parents=True,exist_ok=True)
moved=[]; accepted=[]
for wav in sorted(root.glob(f'*{file_id}*.wav')):
    try:
        receipt_data=validate_receipt(wav)
        if receipt_data.get('backend') != 'local': raise ValueError('receipt backend is not local-only')
        accepted.append(str(wav)); continue
    except Exception as exc: reason=str(exc)
    target=quarantine/wav.name; shutil.move(str(wav),target); moved.append({'from':str(wav),'to':str(target),'reason':reason})
    receipt=wav.with_suffix('.json')
    if receipt.exists(): shutil.move(str(receipt),quarantine/receipt.name)
marker=root/'campaign'/f'repair-{file_id}.json'
tmp=marker.with_suffix('.tmp'); tmp.write_text(json.dumps({'contractVersion':'pocket-tts-render-v3','voiceProfileId':'vera-venice-close-mic-v1','fileId':file_id,'createdAtMs':int(time.time()*1000),'quarantined':moved,'acceptedV3':accepted,'status':'ready-for-v3-vera-close-mic-rerender'},indent=2)+'\n'); os.replace(tmp,marker)
print(json.dumps({'status':'ready-for-v3-vera-close-mic-rerender','fileId':file_id,'quarantined':len(moved),'acceptedV3':len(accepted),'marker':str(marker)}))
PY2
 record repair "$file_id"
}
case "${1:-status}" in
 start|init|ensure) start_worker "${2:-$(current_backend)}";;
 restart) stop_worker; start_worker "${2:-$(current_backend)}";;
 stop) stop_worker;;
 status) status_worker;;
 doctor) shift; HOME_CENTER_POCKET_TTS_BACKEND="$(current_backend)" "$PYTHON" "$WORKER" doctor "$@";;
 repair) shift; [ "${1:-}" = "--file-id" ] || { echo "usage: $0 repair --file-id ID" >&2; exit 2; }; repair_file "${2:-}";;
 benchmark) "$PYTHON" "$ROOT/tools/pocket_tts_render_v2_test.py"; "$PYTHON" "$ROOT/tools/pocket_tts_manifest_batch_benchmark.py"; record benchmark "contract-v3-vera-close-mic-v1";;
 receipts) printf '%s\n' "$HISTORY"; [ -f "$HISTORY" ] && tail -n 30 "$HISTORY" || true; find "$CAMPAIGN" -maxdepth 1 -type f -name '*.json' -print;;
 local) stop_worker; start_worker local;;
 *) echo "usage: $0 {start [local]|restart [local]|stop|status|doctor [--wav PATH]|repair --file-id ID|benchmark|receipts|local}" >&2; exit 2;;
esac
