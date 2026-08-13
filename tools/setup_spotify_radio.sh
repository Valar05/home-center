#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
SOURCE="$ROOT/tools/spotify_radio.py"
TARGET="$HOME/.local/lib/home-center/spotify-radio"
BIN="$HOME/bin"
BOOT="$HOME/.termux/boot"
STATE="$HOME/.local/state/home-center/spotify-radio"
RECEIPT="$STATE/install-receipt.json"

[ -f "$SOURCE" ] || { echo "BLOCKED: $SOURCE missing" >&2; exit 2; }
command -v python3 >/dev/null 2>&1 || { echo "BLOCKED: python3 missing" >&2; exit 3; }

mkdir -p "$TARGET" "$BIN" "$BOOT" "$STATE"
install -m 700 "$SOURCE" "$TARGET/spotify_radio.py"
cat > "$BIN/spotify-radio" <<'EOF'
#!/data/data/com.termux/files/usr/bin/sh
exec python3 "$HOME/.local/lib/home-center/spotify-radio/spotify_radio.py" "$@"
EOF
chmod 700 "$BIN/spotify-radio"

cat > "$BOOT/home-center-spotify-radio.sh" <<'EOF'
#!/data/data/com.termux/files/usr/bin/sh
"$HOME/bin/spotify-radio" ensure >>"$HOME/.local/state/home-center/spotify-radio/boot.log" 2>&1 || true
EOF
chmod 700 "$BOOT/home-center-spotify-radio.sh"

DOCTOR_JSON="$("$BIN/spotify-radio" doctor || true)"
python3 - "$RECEIPT" "$SOURCE" "$TARGET/spotify_radio.py" "$DOCTOR_JSON" <<'PY'
import hashlib
import json
import pathlib
import sys
import time

receipt_path, source_path, target_path, doctor_text = sys.argv[1:]
source = pathlib.Path(source_path).read_bytes()
target = pathlib.Path(target_path).read_bytes()
doctor = {}
try:
    doctor = json.loads(doctor_text)
except Exception:
    doctor = {"ok": False, "raw": doctor_text[-2000:]}
receipt = {
    "schema": "home-center.spotify-radio-install.v1",
    "ok": source == target and doctor.get("ok") is True,
    "sourcePath": source_path,
    "runtimePath": target_path,
    "sourceSha256": hashlib.sha256(source).hexdigest(),
    "runtimeSha256": hashlib.sha256(target).hexdigest(),
    "bytes": len(target),
    "doctor": doctor,
    "bootHook": str(pathlib.Path.home() / ".termux/boot/home-center-spotify-radio.sh"),
    "wrapper": str(pathlib.Path.home() / "bin/spotify-radio"),
    "installedAtMs": int(time.time() * 1000),
}
pathlib.Path(receipt_path).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(receipt, sort_keys=True))
raise SystemExit(0 if receipt["ok"] else 4)
PY

"$BIN/spotify-radio" ensure || true
