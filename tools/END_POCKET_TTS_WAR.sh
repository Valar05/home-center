#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

say='Android asks: is Adam asexual? She-Ra says: irrelevant. Pocket TTS is alive.'
ROOT=''
for d in "$HOME/home-center" /storage/emulated/0/Documents/GodotProjects/home-center /storage/emulated/0/Documents/GodotProjects/home-center-phone-hands; do
  if [ -f "$d/tools/fortress_read_aloud.py" ]; then ROOT="$d"; break; fi
done

logdir=/storage/emulated/0/Documents/FortressReceipts
mkdir -p "$logdir"
receipt="$logdir/pocket-tts-war-$(date +%Y%m%d-%H%M%S).log"
exec > >(tee -a "$receipt") 2>&1

echo "FORTRESS_POCKET_TTS_WAR_START $(date -Iseconds)"
echo "DEVICE=$(getprop ro.product.model 2>/dev/null || true)"
echo "SERIAL=$(getprop ro.serialno 2>/dev/null || true)"

if [ -z "$ROOT" ]; then
  echo 'RED_BUILD fortress_read_aloud.py not found in known Home Center roots'
  exit 20
fi
cd "$ROOT"
echo "ROOT=$ROOT"

# Known-good body, not rediscovery.
if [ ! -x "$HOME/bin/pocket-tts-phone" ]; then
  echo 'RED_BUILD ~/bin/pocket-tts-phone missing or not executable'
  exit 21
fi

# Find the already-installed rish body without requiring PATH magic.
RISH=''
for p in "$HOME/bin/rish" "$HOME/rish" /storage/emulated/0/Android/data/moe.shizuku.privileged.api/files/rish /storage/emulated/0/Documents/rish /storage/emulated/0/Download/rish; do
  if [ -f "$p" ]; then RISH="$p"; break; fi
done
if [ -z "$RISH" ]; then
  echo 'RED_BUILD Shizuku rish body not found'
  exit 22
fi
export RISH

echo "RISH=$RISH"

# Hunger: only doctor -> speak -> receipt. No install, no redesign, no alternate TTS.
python3 tools/fortress_read_aloud.py --doctor | tee "$logdir/pocket-tts-doctor-latest.json"

# Hyperbolic: irreducible end-to-end canary through the real engine and Android playback activity.
set +e
out="$(timeout 240 python3 tools/fortress_read_aloud.py --provider pocket "$say" 2>&1)"
rc=$?
set -e
printf '%s\n' "$out"
if [ "$rc" -ne 0 ]; then
  echo "RED_BUILD pocket playback rc=$rc"
  exit "$rc"
fi

python3 - "$out" <<'PY'
import json,sys
raw=sys.argv[1]
line=next((x for x in reversed(raw.splitlines()) if x.lstrip().startswith('{')), '')
if not line:
    raise SystemExit('RED_BUILD no JSON playback receipt')
r=json.loads(line)
assert r.get('ok') is True, r
assert r.get('provider') == 'pocket-home-center', r
assert r.get('engine') == 'pocket-tts-phone', r
assert r.get('outputComponent') == 'com.dclar.homecenter/.PocketTtsPlaybackActivity', r
assert r.get('playbackVerified') is True, r
assert r.get('systemFallbackUsed') is False, r
assert r.get('cloudFallbackUsed') is False, r
prs=r.get('playbackReceipts') or []
assert prs and all(x.get('playStartObserved') and x.get('playCompletedObserved') for x in prs), r
print('FORTRESS_POCKET_TTS_PHYSICAL_PASS')
PY

echo "FORTRESS_POCKET_TTS_WAR_END $(date -Iseconds)"
echo "RECEIPT=$receipt"
