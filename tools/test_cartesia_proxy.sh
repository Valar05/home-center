#!/data/data/com.termux/files/usr/bin/sh
set -eu

BASE_URL="${CARTESIA_PROXY_BASE_URL:-http://127.0.0.1:8787}"
OUT_DIR="${TMPDIR:-/tmp}"
OUT="$OUT_DIR/home-center-cartesia-test.pcm"
rm -f "$OUT"

curl -fsS   -H 'Content-Type: application/json'   -X POST   --data '{"text":"Home Center Cartesia proxy smoke test. This should produce audible PCM data."}'   "$BASE_URL/tts"   -o "$OUT"

if [ ! -s "$OUT" ]; then
  echo "Cartesia proxy test failed: empty output $OUT" >&2
  exit 1
fi

bytes=$(wc -c < "$OUT" | tr -d ' ')
echo "Cartesia proxy test: OK bytes=$bytes output=$OUT"
