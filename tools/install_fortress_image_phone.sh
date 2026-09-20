#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
DEST="$HOME/.local/share/fortress-image"
BIN="$HOME/bin"
STATE="${HC_STATE_DIR:-$HOME/.local/state/home-center}/fortress-image"
mkdir -p "$BIN" "$STATE"

required=(
  tools/venice_fleshpunk_phone.sh
  tools/fortress_image_cli.py
  tools/fortress_image_presets.json
  tools/fortress_image_cauldron.ps1
  tools/fortress_image_entry.sh
  tools/accept_fortress_image_phone.sh
  tools/accept_venice_fleshpunk_phone.sh
  tools/ssh_axis.py
  tools/resolve_cauldron_ssh.py
)
for rel in "${required[@]}"; do
  [ -f "$ROOT/$rel" ] || { echo "BLOCKED: image runtime source missing: $ROOT/$rel" >&2; exit 2; }
done

rm -rf "$DEST.new"
mkdir -p "$DEST.new/tools"
for rel in "${required[@]}"; do
  cp "$ROOT/$rel" "$DEST.new/tools/"
done
chmod 700 "$DEST.new/tools/"*.sh "$DEST.new/tools/"*.py
rm -rf "$DEST.old"
[ ! -d "$DEST" ] || mv "$DEST" "$DEST.old"
mv "$DEST.new" "$DEST"

cat > "$BIN/fortress-image" <<'EOF'
#!/data/data/com.termux/files/usr/bin/sh
exec python "$HOME/.local/share/fortress-image/tools/fortress_image_cli.py" "$@"
EOF
chmod 700 "$BIN/fortress-image"

cat > "$BIN/fortress-image-accept" <<'EOF'
#!/data/data/com.termux/files/usr/bin/sh
exec bash "$HOME/.local/share/fortress-image/tools/accept_fortress_image_phone.sh" "$@"
EOF
chmod 700 "$BIN/fortress-image-accept"

cat > "$BIN/venice-image" <<'EOF'
#!/data/data/com.termux/files/usr/bin/sh
export FORTRESS_IMAGE_PROFILE=fleshpunk
exec bash "$HOME/.local/share/fortress-image/tools/fortress_image_entry.sh" "$@"
EOF
chmod 700 "$BIN/venice-image"

cat > "$BIN/venice-image-accept" <<'EOF'
#!/data/data/com.termux/files/usr/bin/sh
exec bash "$HOME/.local/share/fortress-image/tools/accept_venice_fleshpunk_phone.sh" "$@"
EOF
chmod 700 "$BIN/venice-image-accept"

# Optional convenience UI. Termux:API may be absent; transport remains usable.
cat > "$BIN/fortress-image-ui" <<'EOF'
#!/data/data/com.termux/files/usr/bin/sh
set -eu
STATE="${HC_STATE_DIR:-$HOME/.local/state/home-center}/venice-fleshpunk-image"
command -v termux-dialog >/dev/null 2>&1 || {
  echo 'Optional UI unavailable: termux-dialog is not installed. Background image transport remains available.' >&2
  exit 2
}
RAW="$(termux-dialog text -t 'Improper image' -i 'Describe any legal image to generate locally on THECAULDRON')"
PROMPT="$(printf '%s' "$RAW" | python -c 'import json,sys; d=json.load(sys.stdin); print(d.get("text","") if int(d.get("code",-2)) in (-1,0) else "")')"
[ -n "$PROMPT" ] || exit 0
if "$HOME/bin/fortress-image" generate "$PROMPT"; then
  PUBLIC="$(python - "$STATE/latest.json" <<'PY'
import json,sys
try: print(json.load(open(sys.argv[1],encoding='utf-8')).get('publicPhonePath',''))
except Exception: print('')
PY
)"
  if command -v termux-toast >/dev/null 2>&1; then termux-toast 'Image delivered to Pictures/Fortress' >/dev/null 2>&1 || true; fi
  if command -v termux-open >/dev/null 2>&1 && [ -n "$PUBLIC" ] && [ -f "$PUBLIC" ]; then termux-open "$PUBLIC" >/dev/null 2>&1 || true; fi
else
  rc=$?
  if command -v termux-toast >/dev/null 2>&1; then termux-toast "Image generation failed. Exit $rc." >/dev/null 2>&1 || true; fi
  exit "$rc"
fi
EOF
chmod 700 "$BIN/fortress-image-ui"

if command -v termux-notification >/dev/null 2>&1; then
  termux-notification \
    --id 6502 \
    --ongoing true \
    --priority high \
    --title 'Fortress Image' \
    --content 'Local image generation: THECAULDRON -> verified PNG -> Pictures/Fortress. Shizuku not required.' \
    --button1 'Improper Image' \
    --button1-action "bash -l -c '$BIN/fortress-image-ui'" >/dev/null 2>&1 || true
fi

python - "$DEST" "$BIN" <<'PY'
import json,sys
print(json.dumps({
  'schema':'fortress-image-phone-install.v1','ok':True,
  'runtimeRoot':sys.argv[1],
  'command':sys.argv[2]+'/fortress-image',
  'acceptCommand':sys.argv[2]+'/fortress-image-accept',
  'uiOptional':True,
  'shizukuRequired':False,
  'atomRequired':False,
  'vladRequired':False,
  'endpointPolicy':'verified-ssh-axis-dynamic',
  'presetRegistry':sys.argv[1]+'/tools/fortress_image_presets.json',
  'deterministicCli':sys.argv[1]+'/tools/fortress_image_cli.py',
  'cauldronRuntime':sys.argv[1]+'/tools/fortress_image_cauldron.ps1',
},sort_keys=True))
PY
