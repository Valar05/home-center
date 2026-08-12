#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
REPO="${FORTRESS_HOME_CENTER:-/storage/emulated/0/Documents/GodotProjects/home-center}"
STATE="$HOME/.local/state/home-center/fortress-phone-kernel"
BIN="$HOME/bin"
BOOT="$HOME/.termux/boot"
mkdir -p "$STATE" "$BIN" "$BOOT" "$HOME/.config/home-center"
python -m py_compile "$REPO/tools/fortress_phone_kernel.py" "$REPO/tools/fortress_cli.py"
cat > "$BIN/fortress-kernel" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec python "$REPO/tools/fortress_phone_kernel.py" "\$@"
EOF
cat > "$BIN/fortress" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec python "$REPO/tools/fortress_cli.py" "\$@"
EOF
chmod 700 "$BIN/fortress-kernel" "$BIN/fortress"
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
"$BIN/fortress" --status
