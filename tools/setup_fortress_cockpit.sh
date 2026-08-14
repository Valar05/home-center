#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
PROP="$HOME/.termux/termux.properties"
mkdir -p "$HOME/.termux" "$HOME/.config/home-center" "$HOME/bin"

if [ -f "$PROP" ]; then
  if grep -q '^allow-external-apps=' "$PROP"; then
    sed -i 's/^allow-external-apps=.*/allow-external-apps=true/' "$PROP"
  else
    printf '\nallow-external-apps=true\n' >> "$PROP"
  fi
else
  printf 'allow-external-apps=true\n' > "$PROP"
fi

cat > "$HOME/bin/fortress" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec python '$ROOT/tools/fortress_prompt.py' "\$@"
EOF
chmod +x "$HOME/bin/fortress"

python "$ROOT/tools/fortress_prompt.py" --catalog-json >/dev/null

echo 'FORTRESS COCKPIT TERMUX BRIDGE READY'
echo "config=$HOME/.config/home-center/fortress-prompt.json"
echo 'Android still must grant Fortress Cockpit: Run commands in Termux environment.'
echo 'APK installation is a separate deployment boundary; this script does not claim it.'
