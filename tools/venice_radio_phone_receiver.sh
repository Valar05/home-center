#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ENDPOINT="${VENICE_RADIO_ENDPOINT:-https://us-central1-home-center-dclar.cloudfunctions.net/veniceRadioApi}"
STATION="${VENICE_RADIO_STATION:-venice-asmr-primary}"
TOKEN_CONFIG="${HOME_CENTER_TOKEN_CONFIG:-$HOME/.config/home-center/codex-hub.json}"
STATE_DIR="${VENICE_RADIO_STATE_DIR:-$HOME/.local/state/home-center/venice-radio}"
CACHE="$STATE_DIR/cache"
STATE="$STATE_DIR/receiver.json"
STOP="$STATE_DIR/STOP"
LOG="$STATE_DIR/receiver.log"
CACHE_SEGMENTS="${VENICE_RADIO_CACHE_SEGMENTS:-8}"
mkdir -p "$CACHE"
rm -f "$STOP"

log(){ printf '%s %s\n' "$(date -Iseconds)" "$*" | tee -a "$LOG"; }
need(){ command -v "$1" >/dev/null 2>&1 || { log "missing command: $1"; exit 2; }; }
for c in curl python sha256sum base64 termux-media-player; do need "$c"; done
[ -s "$TOKEN_CONFIG" ] || { log "missing Home Center token config: $TOKEN_CONFIG"; exit 3; }

refresh_token(){
  python - "$TOKEN_CONFIG" <<'PY'
import json,sys,time,urllib.request
p=sys.argv[1]
x=json.load(open(p))
now=int(time.time()*1000)
if x.get('accessToken') and int(x.get('expiresAtMs') or 0) > now+60000:
    print(x['accessToken']); raise SystemExit
refresh=x.get('refreshToken') or ''
if not refresh: raise SystemExit('refreshToken missing')
base=(x.get('gatewayBase') or 'https://us-central1-home-center-dclar.cloudfunctions.net').rstrip('/')
req=urllib.request.Request(base+'/termuxTokenRefresh',data=json.dumps({'refreshToken':refresh}).encode(),headers={'content-type':'application/json'},method='POST')
with urllib.request.urlopen(req,timeout=30) as r: body=json.loads(r.read())
token=body.get('access_token') or ''
if not token: raise SystemExit('access token refresh failed')
x['accessToken']=token
x['expiresAtMs']=now+int(body.get('expires_in') or 3600)*1000
with open(p+'.tmp','w') as f: json.dump(x,f,indent=2); f.write('\n')
import os; os.replace(p+'.tmp',p); os.chmod(p,0o600)
print(token)
PY
}

TOKEN="$(refresh_token)"
radio(){
  local body="$1"
  curl -fsS --connect-timeout 15 --max-time 45 \
    -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
    --data "$body" "$ENDPOINT"
}

status_json(){ radio "{\"action\":\"radio.station.status\",\"stationId\":\"$STATION\"}"; }

segment_json(){ local seq="$1"; radio "{\"action\":\"radio.station.segment\",\"stationId\":\"$STATION\",\"sequence\":$seq}"; }

player_status(){
  termux-media-player info 2>/dev/null | awk -F': ' '/^Status:/{print tolower($2); exit}' || true
}

write_state(){
  local seq="$1" sha="$2" mode="$3"
  python - "$STATE" "$STATION" "$seq" "$sha" "$mode" <<'PY'
import json,os,sys,datetime
p,station,seq,sha,mode=sys.argv[1:]
x={'status':'playing','stationId':station,'lastSequence':int(seq),'sha256':sha,'mode':mode,'updatedAt':datetime.datetime.now(datetime.timezone.utc).isoformat()}
with open(p+'.tmp','w') as f: json.dump(x,f,indent=2); f.write('\n')
os.replace(p+'.tmp',p)
PY
}

trim_cache(){
  ls -1t "$CACHE"/segment-*.wav 2>/dev/null | tail -n "+$((CACHE_SEGMENTS+1))" | xargs -r rm -f --
}

S="$(status_json)"
HEAD="$(printf '%s' "$S" | python -c 'import json,sys; x=json.load(sys.stdin); print(int(x.get("headSequence") or 0))')"
GEN="$(printf '%s' "$S" | python -c 'import json,sys; x=json.load(sys.stdin); print(int(x.get("generation") or 0))')"
[ "$HEAD" -gt 0 ] || { log "station has no segments"; exit 4; }
if [ -s "$STATE" ]; then
  LAST="$(python - "$STATE" <<'PY'
import json,sys
try: print(int(json.load(open(sys.argv[1])).get('lastSequence') or 0))
except: print(0)
PY
)"
else LAST=0; fi
if [ "$LAST" -gt 0 ] && [ "$LAST" -lt "$HEAD" ]; then NEXT=$((LAST+1)); else NEXT=$(( HEAD>1 ? HEAD-1 : HEAD )); fi
log "receiver start station=$STATION generation=$GEN head=$HEAD next=$NEXT"

while [ ! -e "$STOP" ]; do
  S="$(status_json || true)"
  if [ -z "$S" ]; then sleep 2; TOKEN="$(refresh_token)"; continue; fi
  HEAD="$(printf '%s' "$S" | python -c 'import json,sys; x=json.load(sys.stdin); print(int(x.get("headSequence") or 0))')"
  if [ "$NEXT" -gt "$HEAD" ]; then sleep 0.5; continue; fi

  J="$(segment_json "$NEXT" || true)"
  if [ -z "$J" ]; then sleep 1; TOKEN="$(refresh_token)"; continue; fi
  META="$CACHE/segment-$(printf '%010d' "$NEXT").json"
  WAV="$CACHE/segment-$(printf '%010d' "$NEXT").wav"
  printf '%s' "$J" > "$META"
  python - "$META" "$WAV" <<'PY'
import base64,json,sys
x=json.load(open(sys.argv[1])); open(sys.argv[2],'wb').write(base64.b64decode(x['audioBase64']))
PY
  EXP="$(python - "$META" -c '' 2>/dev/null || true)"
  EXP="$(python - "$META" <<'PY'
import json,sys; print(json.load(open(sys.argv[1]))['sha256'])
PY
)"
  ACT="$(sha256sum "$WAV" | awk '{print $1}')"
  [ "$EXP" = "$ACT" ] || { log "hash mismatch seq=$NEXT"; rm -f "$WAV" "$META"; sleep 1; continue; }
  DUR="$(python - "$META" <<'PY'
import json,sys; print(int(json.load(open(sys.argv[1])).get('durationMs') or 4000))
PY
)"

  termux-media-player play "$WAV" >/dev/null
  write_state "$NEXT" "$ACT" texture
  log "playing seq=$NEXT sha=$ACT bytes=$(wc -c < "$WAV")"
  START_MS="$(date +%s%3N)"
  while [ ! -e "$STOP" ]; do
    PS="$(player_status)"
    NOW_MS="$(date +%s%3N)"; ELAPSED=$((NOW_MS-START_MS))
    case "$PS" in
      paused) sleep 0.25; continue ;;
      playing) sleep 0.20; continue ;;
      stopped|"")
        if [ "$ELAPSED" -lt $((DUR*3/4)) ]; then
          log "media stop received seq=$NEXT elapsedMs=$ELAPSED; stopping receiver"
          touch "$STOP"
        fi
        break ;;
      *) sleep 0.20 ;;
    esac
  done
  rm -f "$META"
  trim_cache
  NEXT=$((NEXT+1))
done

termux-media-player stop >/dev/null 2>&1 || true
python - "$STATE" <<'PY'
import json,os,sys,datetime
p=sys.argv[1]
try:x=json.load(open(p))
except:x={}
x['status']='stopped';x['updatedAt']=datetime.datetime.now(datetime.timezone.utc).isoformat()
with open(p+'.tmp','w') as f:json.dump(x,f,indent=2);f.write('\n')
os.replace(p+'.tmp',p)
PY
log 'receiver stopped'
