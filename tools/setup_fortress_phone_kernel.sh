#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
REPO="${FORTRESS_HOME_CENTER:-/storage/emulated/0/Documents/GodotProjects/home-center}"
BRANCH="${FORTRESS_PHONE_BRANCH:-feat/fortress-cockpit-android}"
STATE="$HOME/.local/state/home-center/fortress-phone-kernel"
BIN="$HOME/bin"
BOOT="$HOME/.termux/boot"
REQUIRE_VOICE="${FORTRESS_REQUIRE_VOICE:-0}"
SUPERVISOR="${FORTRESS_KERNEL_SUPERVISOR:-external}"

cd "$REPO"
git fetch origin "$BRANCH"
git checkout "origin/$BRANCH" -- \
  tools/fortress_prompt.py \
  tools/fortress_cli.py \
  tools/fortress_phone_kernel.py \
  tools/fortress_read_aloud.py \
  tools/android_phone_status_tts.py \
  config/fortress-prompt.json \
  config/fortress-phone-kernel.json \
  config/fortress-adam-voice.json

for required in \
  tools/fortress_prompt.py \
  tools/fortress_cli.py \
  tools/fortress_phone_kernel.py \
  config/fortress-prompt.json \
  config/fortress-phone-kernel.json; do
  test -s "$REPO/$required" || { echo "BLOCKED: missing runtime file: $required" >&2; exit 2; }
done

mkdir -p "$STATE" "$BIN" "$BOOT" "$HOME/.config/home-center"
python -m py_compile \
  "$REPO/tools/fortress_prompt.py" \
  "$REPO/tools/fortress_phone_kernel.py" \
  "$REPO/tools/fortress_cli.py"
python -m json.tool "$REPO/config/fortress-prompt.json" >/dev/null
python -m json.tool "$REPO/config/fortress-phone-kernel.json" >/dev/null

cat > "$BIN/fortress-kernel" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec python "$REPO/tools/fortress_phone_kernel.py" "\$@"
EOF
cat > "$BIN/fortress" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec python "$REPO/tools/fortress_cli.py" "\$@"
EOF
chmod 700 "$BIN/fortress-kernel" "$BIN/fortress"

if [ "$REQUIRE_VOICE" = "1" ]; then
  for required in tools/fortress_read_aloud.py tools/android_phone_status_tts.py config/fortress-adam-voice.json; do
    test -s "$REPO/$required" || { echo "BLOCKED: voice runtime file missing: $required" >&2; exit 3; }
  done
  test -x "$HOME/bin/pocket-tts-phone" || { echo 'BLOCKED: existing PocketTTS phone wrapper missing: ~/bin/pocket-tts-phone' >&2; exit 3; }
  test -x /system/bin/am || { echo 'BLOCKED: Android activity launcher unavailable' >&2; exit 3; }
  mkdir -p /storage/emulated/0/Documents/FortressAudio
  python -m py_compile "$REPO/tools/fortress_read_aloud.py" "$REPO/tools/android_phone_status_tts.py"
  python -m json.tool "$REPO/config/fortress-adam-voice.json" >/dev/null
  cat > "$BIN/fortress-read" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec python "$REPO/tools/fortress_read_aloud.py" "\$@"
EOF
  chmod 700 "$BIN/fortress-read"
fi

if [ "$SUPERVISOR" = "legacy" ]; then
  cat > "$BOOT/30-fortress-phone-kernel" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
set -eu
STATE="\$HOME/.local/state/home-center/fortress-phone-kernel"
mkdir -p "\$STATE"
PID="\$STATE/kernel.pid"
if [ -s "\$PID" ] && kill -0 "\$(cat "\$PID")" 2>/dev/null; then exit 0; fi
nohup python "$REPO/tools/fortress_phone_kernel.py" daemon >>"\$STATE/daemon.log" 2>&1 &
echo \$! > "\$PID"
EOF
  chmod 700 "$BOOT/30-fortress-phone-kernel"
  "$BOOT/30-fortress-phone-kernel"
  sleep 1
else
  rm -f "$BOOT/30-fortress-phone-kernel"
fi

hash -r 2>/dev/null || true
"$BIN/fortress" --status

if [ "$REQUIRE_VOICE" = "1" ]; then
  VOICE_DOCTOR="$($BIN/fortress-read --doctor)"
  echo "$VOICE_DOCTOR"
  python - "$VOICE_DOCTOR" <<'PY'
import json,sys
r=json.loads(sys.argv[1])
if not r.get('ok') or r.get('preferred')!='pocket-home-center':
    raise SystemExit('BLOCKED: shared Pocket/Home Center voice transport is not callable: '+str(r.get('blockedReason') or r))
PY
  "$BIN/fortress-read" --profile
fi
