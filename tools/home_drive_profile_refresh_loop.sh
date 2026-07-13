#!/data/data/com.termux/files/usr/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"

INTERVAL_SECONDS="${HOME_DRIVE_PROFILE_REFRESH_INTERVAL_SECONDS:-21600}"
INPUT_DIR="${HOME_DRIVE_PROFILE_SCAN_INPUT:-generated/home_drive_voice_profiles/drive_exports}"
OUTPUT_FILE="${HOME_DRIVE_PROFILE_REFRESH_OUTPUT:-generated/home_drive_voice_profiles/latest_refresh_profiles.md}"
LOG_FILE="${HOME_DRIVE_PROFILE_REFRESH_LOG:-generated/home_drive_voice_profiles/refresh.log}"
REGISTRY_FILE="${HOME_DRIVE_PROFILE_REGISTRY:-app/src/main/assets/home_drive_character_voice_registry.md}"
GATEWAY="${HOME_DRIVE_PROFILE_GATEWAY:-https://us-central1-home-center-dclar.cloudfunctions.net}"
VOICE_LIMIT="${HOME_DRIVE_PROFILE_VOICE_LIMIT:-80}"
ONCE="${HOME_DRIVE_PROFILE_REFRESH_ONCE:-0}"

case "${1:-}" in
  --once) ONCE=1 ;;
  --help|-h)
    cat <<USAGE
Usage: sh tools/home_drive_profile_refresh_loop.sh [--once]

Environment overrides:
  HOME_DRIVE_PROFILE_REFRESH_INTERVAL_SECONDS  Default: 21600
  HOME_DRIVE_PROFILE_SCAN_INPUT                Default: generated/home_drive_voice_profiles/drive_exports
  HOME_DRIVE_PROFILE_REFRESH_OUTPUT            Default: generated/home_drive_voice_profiles/latest_refresh_profiles.md
  HOME_DRIVE_PROFILE_REFRESH_LOG               Default: generated/home_drive_voice_profiles/refresh.log
  HOME_DRIVE_PROFILE_REGISTRY                  Default: app/src/main/assets/home_drive_character_voice_registry.md
  HOME_DRIVE_PROFILE_GATEWAY                   Default: Home Center Firebase gateway
  HOME_DRIVE_PROFILE_VOICE_LIMIT               Default: 80
USAGE
    exit 0
    ;;
esac

mkdir -p "$(dirname -- "$OUTPUT_FILE")" "$(dirname -- "$LOG_FILE")" "$INPUT_DIR"

log() {
  printf '%s %s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$*" | tee -a "$LOG_FILE"
}

run_once() {
  if ! find "$INPUT_DIR" -type f \( -name '*.txt' -o -name '*.md' -o -name '*.json' \) -print -quit | grep -q .; then
    log "no exported Drive docs found in $INPUT_DIR; waiting for app/MCP exports"
    return 0
  fi

  log "refresh started input=$INPUT_DIR output=$OUTPUT_FILE registry=$REGISTRY_FILE"
  if python3 tools/home_drive_speaker_profile_scan.py "$INPUT_DIR" \
      --registry "$REGISTRY_FILE" \
      --output "$OUTPUT_FILE" \
      --gateway "$GATEWAY" \
      --voice-limit "$VOICE_LIMIT" \
      --merge >>"$LOG_FILE" 2>&1; then
    log "refresh completed"
    return 0
  else
    status=$?
    log "refresh failed status=$status"
    return "$status"
  fi
}

while :; do
  run_once || true
  if [ "$ONCE" = "1" ]; then
    exit 0
  fi
  log "sleeping ${INTERVAL_SECONDS}s"
  sleep "$INTERVAL_SECONDS"
done
