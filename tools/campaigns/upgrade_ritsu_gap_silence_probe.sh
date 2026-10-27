#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail
BASE="$HOME/.local/share/ritsu-phone-gap"
ENTRY="$PREFIX/bin/ritsu-gap"
OLD="9fbc3cfbb6ecd29009e2f07dac9b4348462112cb"
NEW="00ab7f1f453847c09f88b830f1259edd8b1c1be3"
URL="https://raw.githubusercontent.com/Valar05/home-center"
FILES=(ritsu_phone_gap_campaign.py test_ritsu_phone_gap_campaign.py ritsu_pcm_silence_guard.py test_ritsu_pcm_silence_guard.py)
TMP=""; STAGE="preflight"
receipt() {
  printf '%s\n' "$1"
  command -v termux-clipboard-set >/dev/null 2>&1 && printf '%s\n' "$1" | termux-clipboard-set >/dev/null 2>&1 || true
}
onerror() { rc="$?"; trap - ERR; receipt "RITSU_SILENCE_UPGRADE_FAILED stage=$STAGE exit=$rc; receiver unchanged"; exit "$rc"; }
cleanup() { [[ -z "$TMP" || ! -d "$TMP" ]] || rm -rf -- "$TMP"; }
trap onerror ERR
trap cleanup EXIT
for tool in curl python3 cmp mktemp; do
  command -v "$tool" >/dev/null 2>&1 || { receipt "RITSU_SILENCE_UPGRADE_FAILED missing=$tool"; exit 9; }
done
[[ -f "$BASE/ritsu_phone_gap_campaign.py" && -f "$ENTRY" ]] || { receipt 'RITSU_SILENCE_UPGRADE_FAILED campaign not installed'; exit 10; }
if "$ENTRY" status | grep -Fxq 'WORKER_ALIVE=True'; then receipt 'RITSU_SILENCE_UPGRADE_PAUSED worker running'; exit 11; fi
TMP="$(mktemp -d "$BASE/.silence-candidate.XXXXXXXX")"
chmod 700 "$TMP"
STAGE="download"
for f in "${FILES[@]}"; do
  curl -fLsS --retry 2 "$URL/$NEW/tools/campaigns/$f" -o "$TMP/$f"
done
for f in ritsu_phone_gap_campaign.py test_ritsu_phone_gap_campaign.py; do
  curl -fLsS --retry 2 "$URL/$OLD/tools/campaigns/$f" -o "$TMP/old-$f"
done
STAGE="protect"
for f in ritsu_phone_gap_campaign.py test_ritsu_phone_gap_campaign.py; do
  [[ -f "$BASE/$f" ]] || { receipt "RITSU_SILENCE_RECONCILE missing=$f"; exit 12; }
  cmp -s "$BASE/$f" "$TMP/old-$f" || cmp -s "$BASE/$f" "$TMP/$f" || { receipt "RITSU_SILENCE_RECONCILE local edit=$f; no overwrite"; exit 13; }
done
for f in ritsu_pcm_silence_guard.py test_ritsu_pcm_silence_guard.py; do
  [[ ! -e "$BASE/$f" ]] || cmp -s "$BASE/$f" "$TMP/$f" || { receipt "RITSU_SILENCE_RECONCILE local edit=$f; no overwrite"; exit 14; }
done
STAGE="tests"
python3 -m py_compile "$TMP/"*.py
(cd "$TMP" && python3 test_ritsu_phone_gap_campaign.py && python3 test_ritsu_pcm_silence_guard.py) > "$TMP/tests.log" 2>&1 || { tail -n 30 "$TMP/tests.log" >&2; false; }
STAGE="backup"
BACKUP="$BASE/backups/silence-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BACKUP"
for f in ritsu_phone_gap_campaign.py test_ritsu_phone_gap_campaign.py; do cp -p "$BASE/$f" "$BACKUP/$f"; done
STAGE="install"
for f in "${FILES[@]}"; do
  cp "$TMP/$f" "$BASE/.new-$f.$$"; chmod 600 "$BASE/.new-$f.$$"; mv -f "$BASE/.new-$f.$$" "$BASE/$f"
done
printf 'RITSU_SILENCE_PROBE_INSTALLED=1\nBACKUP=%s\n' "$BACKUP"
exec "$ENTRY" silence
