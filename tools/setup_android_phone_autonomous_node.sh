#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
CFG="$HOME/.config/home-center"
STATE="$HOME/.local/state/home-center"
MODELS="$HOME/.local/share/home-center/models"
mkdir -p "$CFG" "$STATE" "$MODELS"
chmod 700 "$CFG"

echo '[1/6] Installing Termux dependencies'
pkg update -y
pkg install -y python curl jq termux-api llama-cpp

if ! command -v llama-server >/dev/null 2>&1; then
  echo 'BLOCKED: llama-server was not installed by the Termux llama-cpp package.' >&2
  echo 'Install/build llama.cpp using its official Android/Termux instructions, then rerun.' >&2
  exit 2
fi

MODEL="$MODELS/qwen2.5-0.5b-instruct-q4_k_m.gguf"
if [ ! -s "$MODEL" ]; then
  echo '[2/6] Downloading Qwen2.5 0.5B Q4_K_M (~400 MB class)'
  curl -fL --retry 3 \
    'https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf?download=true' \
    -o "$MODEL.part"
  mv "$MODEL.part" "$MODEL"
else
  echo '[2/6] Model already present'
fi

ENV="$CFG/phone-node.env"
if [ ! -f "$ENV" ]; then
  cat > "$ENV" <<EOF
HC_PHONE_LLM_MODEL='local-phone'
HC_PHONE_LLM_URL='http://127.0.0.1:8790/v1/chat/completions'
HC_PHONE_LLM_MODEL_PATH='$MODEL'
HC_PHONE_WAKE_WORD='venice'
HC_PHONE_REQUIRE_WAKE_WORD='1'
HC_PHONE_LISTEN_SECONDS='6'
HC_PHONE_EXEC_MAX_STEPS='6'
HC_PHONE_STT_CMD=''
HC_PHONE_TTS_CMD=''
HC_PHONE_VLAD_CMD=''
EOF
  chmod 600 "$ENV"
fi

echo '[3/6] Verifying Shizuku/rish'
RISH_BIN="${RISH:-$(command -v rish 2>/dev/null || true)}"
[ -n "$RISH_BIN" ] || RISH_BIN="$HOME/bin/rish"
[ -x "$RISH_BIN" ] || { echo 'BLOCKED: rish missing.' >&2; exit 3; }
"$RISH_BIN" -c 'id; dumpsys window 2>/dev/null | grep -E "mCurrentFocus|mFocusedApp" | head -1' >/dev/null

echo '[4/6] Creating launchers'
cat > "$HOME/bin/home-center-phone-brain" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
source '$ENV'
export HC_PHONE_LLM_MODEL HC_PHONE_LLM_URL HC_PHONE_LLM_MODEL_PATH HC_PHONE_WAKE_WORD HC_PHONE_REQUIRE_WAKE_WORD HC_PHONE_LISTEN_SECONDS HC_PHONE_EXEC_MAX_STEPS HC_PHONE_STT_CMD HC_PHONE_TTS_CMD HC_PHONE_VLAD_CMD
# Do not force --jinja here. llama.cpp has had response_format/Jinja
# incompatibilities; Qwen2.5 GGUF carries a usable chat template already.
exec llama-server -m "\$HC_PHONE_LLM_MODEL_PATH" --host 127.0.0.1 --port 8790 -c 4096 -t "\$(nproc)"
EOF
chmod +x "$HOME/bin/home-center-phone-brain"

cat > "$HOME/bin/home-center-phone-ask" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
source '$ENV'
export HC_PHONE_LLM_MODEL HC_PHONE_LLM_URL HC_PHONE_LLM_MODEL_PATH HC_PHONE_EXEC_MAX_STEPS
cd '$ROOT/tools'
exec python '$ROOT/tools/android_phone_local_executive.py' "\$@"
EOF
chmod +x "$HOME/bin/home-center-phone-ask"

cat > "$HOME/bin/home-center-phone-voice" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
source '$ENV'
export HC_PHONE_LLM_MODEL HC_PHONE_LLM_URL HC_PHONE_LLM_MODEL_PATH HC_PHONE_WAKE_WORD HC_PHONE_REQUIRE_WAKE_WORD HC_PHONE_LISTEN_SECONDS HC_PHONE_EXEC_MAX_STEPS HC_PHONE_STT_CMD HC_PHONE_TTS_CMD HC_PHONE_VLAD_CMD
cd '$ROOT/tools'
exec python '$ROOT/tools/android_phone_voice_assistant.py'
EOF
chmod +x "$HOME/bin/home-center-phone-voice"

echo '[5/6] Starting local model'
LOG="$STATE/phone-brain.log"
PIDFILE="$STATE/phone-brain.pid"
if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  kill "$(cat "$PIDFILE")" 2>/dev/null || true
  sleep 1
fi
nohup "$HOME/bin/home-center-phone-brain" >"$LOG" 2>&1 &
echo $! > "$PIDFILE"

for i in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:8790/health >/dev/null 2>&1; then break; fi
  sleep 1
done
curl -fsS http://127.0.0.1:8790/health >/dev/null || { echo "BLOCKED: local model failed; inspect $LOG" >&2; exit 4; }

echo '[6/6] Local executive smoke test'
cd "$ROOT/tools"
python android_phone_local_executive.py 'Observe my phone and tell me what app is foregrounded. Do not take any action.' | tee "$STATE/phone-executive-smoke.json"

echo
echo 'AUTONOMOUS PHONE CORE READY.'
echo 'Text command: home-center-phone-ask "go home"'
echo 'Voice loop:   home-center-phone-voice'
echo 'VAD adapter:  HC_PHONE_VLAD_CMD — codename Vlad the Impalementer.'
