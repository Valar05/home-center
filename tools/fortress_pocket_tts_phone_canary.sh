#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail
umask 077

ID="${FORTRESS_POCKET_TTS_CANARY_ID:-pocket-tts-nightcore-pr317-canary}"
REPO="${FORTRESS_HOME_CENTER:-$HOME/home-center}"
REMOTE_BRANCH="${FORTRESS_POCKET_TTS_REMOTE_BRANCH:-fortress/pocket-tts-nightcore}"
EXPECTED_HEAD="${FORTRESS_POCKET_TTS_EXPECTED_HEAD:-}"
CAND="$HOME/.local/state/home-center/pocket-tts-canary/$ID"
mkdir -p "$CAND"

fail(){
  python3 - "$ID" "$1" <<'PY'
import json,sys
print(json.dumps({"schema":"fortress.pocket-tts-canary.v1","ok":False,"commandId":sys.argv[1],"stage":sys.argv[2]},sort_keys=True))
PY
  exit 1
}

[ -d "$REPO/.git" ] || fail repo_missing
export GIT_TERMINAL_PROMPT=0
if ! timeout 30 git -C "$REPO" fetch --no-tags --quiet origin "$REMOTE_BRANCH" 2>"$CAND/fetch.err"; then
  cat "$CAND/fetch.err" >&2
  fail git_fetch
fi
HEAD="$(git -C "$REPO" rev-parse FETCH_HEAD)"
if [ -n "$EXPECTED_HEAD" ] && [ "$HEAD" != "$EXPECTED_HEAD" ]; then
  fail unexpected_head
fi

git -C "$REPO" show "$HEAD:tools/fortress_status_read.py" > "$CAND/fortress_status_read.py"
git -C "$REPO" show "$HEAD:config/fortress-pocket-tts-performance.json" > "$CAND/fortress-pocket-tts-performance.json"
git -C "$REPO" show "$HEAD:docs/evidence/nightcore-design/hunger-hyperbolic-profile-20260814.json" > "$CAND/hunger-hyperbolic-profile.json"
chmod 700 "$CAND/fortress_status_read.py"

# Candidate evaluation MUST NOT mutate the tracked last-known-good config.
# Compile the design-side first canary into only this ephemeral copy, preserving
# engine/provider/playback locks and the evidence-before-promotion law.
python3 - "$CAND/fortress-pocket-tts-performance.json" "$CAND/hunger-hyperbolic-profile.json" "$CAND/candidate.json" <<'PY'
import copy,hashlib,json,sys
config_path,design_path,out_path=sys.argv[1:]
config=json.load(open(config_path,encoding='utf-8'))
design=json.load(open(design_path,encoding='utf-8'))
candidate_id=design.get('implementationReadyProfile',{}).get('firstCanary')
if not candidate_id:
    raise SystemExit('design artifact missing implementationReadyProfile.firstCanary')
candidates={c.get('id'):c for c in design.get('candidates',[]) if isinstance(c,dict)}
candidate=candidates.get(candidate_id)
if not candidate:
    raise SystemExit(f'design candidate missing: {candidate_id}')
compiled=copy.deepcopy(config)
for target,source_key in [('orandroid67','orandroid67'),('she-ra','sheRa')]:
    src=candidate[source_key]
    dst=compiled['personas'][target]
    dst['status']='CANDIDATE_PHYSICAL_CANARY'
    dst['tempo']=float(src['rate'])
    dst['pitchSemitones']=float(src['pitchSemitones'])
    dst['pauseDensity']=float(src['pauseDensity'])
    dst['utteranceMaxChars']=int(src['utteranceMaxChars'])
    dst['roastDensity']=float(src['roastDensity'])
    dst['postProcessing']={'kind':'ffmpeg-nightcore','reversible':True}
compiled['activeCandidate']={
    'id':candidate_id,
    'source':'docs/evidence/nightcore-design/hunger-hyperbolic-profile-20260814.json',
    'runtimeStatus':'CANDIDATE_NOT_PROMOTED',
    'physicalEvidenceRequired':True,
}
open(config_path,'w',encoding='utf-8').write(json.dumps(compiled,indent=2,sort_keys=True)+'\n')
raw=open(design_path,'rb').read()
out={
  'candidateId':candidate_id,
  'runtimeStatus':'CANDIDATE_NOT_PROMOTED',
  'designArtifactSha256':hashlib.sha256(raw).hexdigest(),
  'orandroid67':candidate['orandroid67'],
  'sheRa':candidate['sheRa'],
  'promotionRule':design.get('implementationReadyProfile',{}).get('promotionRule'),
}
open(out_path,'w',encoding='utf-8').write(json.dumps(out,indent=2,sort_keys=True)+'\n')
PY

export FORTRESS_HOME_CENTER="$REPO"
export FORTRESS_POCKET_TTS_PERFORMANCE_CONFIG="$CAND/fortress-pocket-tts-performance.json"

python3 - "$CAND/device.json" <<'PY'
import json,subprocess,sys

def cmd(args):
    try:
        p=subprocess.run(args,text=True,capture_output=True,timeout=3,check=False)
        return (p.stdout or p.stderr).strip()
    except Exception as e:
        return f"{type(e).__name__}:{e}"
obj={
  "hostname":cmd(["hostname"]),
  "manufacturer":cmd(["getprop","ro.product.manufacturer"]),
  "model":cmd(["getprop","ro.product.model"]),
  "device":cmd(["getprop","ro.product.device"]),
  "android":cmd(["getprop","ro.build.version.release"]),
}
open(sys.argv[1],"w",encoding="utf-8").write(json.dumps(obj,sort_keys=True)+"\n")
PY

timeout 45 python3 "$CAND/fortress_status_read.py" --doctor --persona orandroid67 > "$CAND/doctor-orandroid.json"
timeout 45 python3 "$CAND/fortress_status_read.py" --doctor --persona she-ra > "$CAND/doctor-shera.json"
python3 - "$CAND/doctor-orandroid.json" "$CAND/doctor-shera.json" <<'PY'
import json,sys
for path in sys.argv[1:]:
    data=json.load(open(path,encoding='utf-8'))
    if data.get('ok') is not True:
        raise SystemExit(f"doctor failed: {path}: {data}")
PY

timeout 240 python3 "$CAND/fortress_status_read.py" --persona orandroid67 \
  "Pocket TTS physical canary. Verifying Nightcore playback on the primary phone. No operator action required." \
  > "$CAND/orandroid.json"
timeout 240 python3 "$CAND/fortress_status_read.py" --persona she-ra \
  "She-Ra canary. Playback verification follows. You very small administrative tragedy." \
  > "$CAND/shera.json"
timeout 45 "$HOME/bin/fortress-read" --doctor > "$CAND/final-health.json"

python3 - "$ID" "$HEAD" "$CAND" <<'PY'
import hashlib,json,pathlib,sys
ID,head,cand=sys.argv[1:]
p=pathlib.Path(cand)
def load(name): return json.load(open(p/name,encoding='utf-8'))
def slim(d):
    return {
      "ok":d.get("ok") is True,
      "playbackVerified":d.get("playbackVerified") is True,
      "persona":d.get("persona"),
      "transcript":d.get("transcript"),
      "voice":d.get("voice"),
      "audioSeconds":d.get("audioSeconds"),
      "processingReceipts":d.get("processingReceipts",[]),
      "playbackReceipts":[{
        "audioSeconds":r.get("audioSeconds"),
        "activityLaunchAcknowledged":r.get("activityLaunchAcknowledged"),
        "playStartObserved":r.get("playStartObserved"),
        "playCompletedObserved":r.get("playCompletedObserved"),
        "component":r.get("component"),
        "logTag":r.get("logTag"),
      } for r in d.get("playbackReceipts",[])],
      "provider":d.get("provider"),
      "engine":d.get("engine"),
      "transport":d.get("transport"),
      "outputComponent":d.get("outputComponent"),
      "systemFallbackUsed":d.get("systemFallbackUsed"),
      "cloudFallbackUsed":d.get("cloudFallbackUsed"),
    }
dev=load("device.json"); do=load("doctor-orandroid.json"); ds=load("doctor-shera.json")
o=load("orandroid.json"); s=load("shera.json"); fh=load("final-health.json"); candidate=load("candidate.json")
ok=(do.get('ok') is True and ds.get('ok') is True and o.get('playbackVerified') is True and s.get('playbackVerified') is True and fh.get('ok') is True)
script=(p/'fortress_status_read.py').read_bytes(); cfg=(p/'fortress-pocket-tts-performance.json').read_bytes()
print(json.dumps({
  "schema":"fortress.pocket-tts-nightcore.physical-canary.v1",
  "commandId":ID,"ok":ok,
  "source":{"repo":"Valar05/home-center","pr":317,"head":head,"scriptSha256":hashlib.sha256(script).hexdigest(),"ephemeralConfigSha256":hashlib.sha256(cfg).hexdigest()},
  "candidate":candidate,
  "device":dev,
  "doctor":{"orandroid67":{"ok":do.get('ok'),"corePath":do.get('corePath'),"ffmpeg":do.get('ffmpeg'),"provider":do.get('provider'),"engine":do.get('engine'),"outputComponent":do.get('outputComponent')},"she-ra":{"ok":ds.get('ok'),"corePath":ds.get('corePath'),"ffmpeg":ds.get('ffmpeg'),"provider":ds.get('provider'),"engine":ds.get('engine'),"outputComponent":ds.get('outputComponent')}},
  "orandroid67":slim(o),"she-ra":slim(s),
  "finalHealth":{"ok":fh.get('ok'),"preferred":fh.get('preferred'),"canonicalProvider":fh.get('canonicalProvider'),"playbackComponent":fh.get('playbackComponent'),"systemFallbackAllowed":fh.get('systemFallbackAllowed'),"cloudFallback":fh.get('cloudFallback')},
  "trackedLastKnownGoodMutated":False,
  "holocronAcknowledged":False,
},separators=(',',':'),ensure_ascii=False))
raise SystemExit(0 if ok else 2)
PY
