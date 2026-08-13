#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

umask 077

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(CDPATH= cd -- "${SCRIPT_DIR}/.." && pwd)"
SOURCE_FILE="${REPOSITORY_ROOT}/tools/spotify_radio.py"
LIB_DIR="${HOME}/.local/lib/home-center/spotify-radio"
INSTALLED_FILE="${LIB_DIR}/spotify_radio.py"
BIN_DIR="${HOME}/bin"
RADIO_FILE="${BIN_DIR}/spotify-radio"
SERVICE_FILE="${BIN_DIR}/spotify-radio-service"
SERVICE_STATE_DIR="${HOME}/.local/state/home-center/spotify-radio"
BOOT_DIR="${HOME}/.termux/boot"
BOOT_FILE="${BOOT_DIR}/spotify-radio"

if [[ ! -f "${SOURCE_FILE}" ]]; then
  printf 'Spotify radio source is missing: %s\n' "${SOURCE_FILE}" >&2
  exit 1
fi

PYTHONPYCACHEPREFIX="${TMPDIR:-${HOME}/.cache}/home-center-pycache" \
  python3 -m py_compile "${SOURCE_FILE}"

cleanup_install_temps() {
  rm -f -- \
    "${INSTALLED_FILE}.tmp.$$" \
    "${RADIO_FILE}.tmp.$$" \
    "${SERVICE_FILE}.tmp.$$" \
    "${BOOT_FILE}.tmp.$$"
}
trap cleanup_install_temps EXIT

mkdir -p "${LIB_DIR}" "${BIN_DIR}" "${SERVICE_STATE_DIR}" "${BOOT_DIR}"
chmod 700 "${LIB_DIR}" "${BIN_DIR}" "${SERVICE_STATE_DIR}" "${BOOT_DIR}"

cp -- "${SOURCE_FILE}" "${INSTALLED_FILE}.tmp.$$"
chmod 600 "${INSTALLED_FILE}.tmp.$$"
mv -f -- "${INSTALLED_FILE}.tmp.$$" "${INSTALLED_FILE}"

cat >"${RADIO_FILE}.tmp.$$" <<'SPOTIFY_RADIO_WRAPPER'
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

exec python3 "${HOME}/.local/lib/home-center/spotify-radio/spotify_radio.py" "$@"
SPOTIFY_RADIO_WRAPPER
chmod 700 "${RADIO_FILE}.tmp.$$"
mv -f -- "${RADIO_FILE}.tmp.$$" "${RADIO_FILE}"

cat >"${SERVICE_FILE}.tmp.$$" <<'SPOTIFY_RADIO_SERVICE'
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

umask 077

SPOTIFY_RADIO="${HOME}/bin/spotify-radio"
STATE_DIR="${HOME}/.local/state/home-center/spotify-radio"
PID_FILE="${STATE_DIR}/service.pid"
LOG_FILE="${STATE_DIR}/service.log"
LOCK_DIR="${STATE_DIR}/service.lock"
LOCK_OWNER="${LOCK_DIR}/owner.pid"
LOCK_HELD=false

ensure_private_layout() {
  mkdir -p "${STATE_DIR}"
  chmod 700 "${STATE_DIR}"
  touch "${LOG_FILE}"
  chmod 600 "${LOG_FILE}"
}

pid_is_running() {
  local pid="${1:-}"
  [[ "${pid}" =~ ^[1-9][0-9]*$ ]] && kill -0 "${pid}" 2>/dev/null
}

read_process_cmdline() {
  local pid="${1:-}"
  [[ -r "/proc/${pid}/cmdline" ]] || return 1
  tr '\000' ' ' <"/proc/${pid}/cmdline" 2>/dev/null
}

pid_is_service() {
  local pid="${1:-}"
  local command_line=""
  pid_is_running "${pid}" || return 1
  command_line="$(read_process_cmdline "${pid}")" || return 1
  [[ "${command_line}" == *"${HOME}/.local/lib/home-center/spotify-radio/spotify_radio.py daemon"* ]]
}

pid_is_lock_owner() {
  local pid="${1:-}"
  local command_line=""
  pid_is_running "${pid}" || return 1
  command_line="$(read_process_cmdline "${pid}")" || return 1
  [[ "${command_line}" == *"${HOME}/bin/spotify-radio-service"* ]]
}

read_service_pid() {
  local pid=""
  if [[ -f "${PID_FILE}" ]]; then
    IFS= read -r pid <"${PID_FILE}" || true
  fi
  printf '%s' "${pid}"
}

release_lock() {
  if [[ "${LOCK_HELD}" == true ]]; then
    rm -f -- "${LOCK_OWNER}"
    rmdir -- "${LOCK_DIR}" 2>/dev/null || true
    LOCK_HELD=false
  fi
}

acquire_lock() {
  local owner=""
  if ! mkdir -- "${LOCK_DIR}" 2>/dev/null; then
    if [[ -f "${LOCK_OWNER}" ]]; then
      IFS= read -r owner <"${LOCK_OWNER}" || true
    fi
    if pid_is_lock_owner "${owner}"; then
      printf '{"schema":"home-center.spotify-radio-service.v1","status":"busy"}\n' >&2
      return 1
    fi
    rm -f -- "${LOCK_OWNER}"
    rmdir -- "${LOCK_DIR}" 2>/dev/null || true
    if ! mkdir -- "${LOCK_DIR}" 2>/dev/null; then
      printf '{"schema":"home-center.spotify-radio-service.v1","status":"busy"}\n' >&2
      return 1
    fi
  fi
  printf '%s\n' "$$" >"${LOCK_OWNER}"
  chmod 600 "${LOCK_OWNER}"
  LOCK_HELD=true
  trap release_lock EXIT
}

start_service() {
  local pid=""
  local launched_pid=""

  ensure_private_layout
  acquire_lock
  pid="$(read_service_pid)"
  if pid_is_service "${pid}"; then
    printf '{"schema":"home-center.spotify-radio-service.v1","status":"already_running","pid":%s}\n' "${pid}"
    return 0
  fi
  if pid_is_running "${pid}"; then
    printf '{"schema":"home-center.spotify-radio-service.v1","status":"stale_pid_rejected","pid":%s}\n' "${pid}" >&2
  fi

  rm -f -- "${PID_FILE}"
  nohup "${SPOTIFY_RADIO}" daemon --interval 20 >>"${LOG_FILE}" 2>&1 </dev/null &
  launched_pid=$!
  printf '%s\n' "${launched_pid}" >"${PID_FILE}.tmp.$$"
  chmod 600 "${PID_FILE}.tmp.$$"
  mv -f -- "${PID_FILE}.tmp.$$" "${PID_FILE}"

  sleep 1
  if ! pid_is_service "${launched_pid}"; then
    rm -f -- "${PID_FILE}"
    printf '{"schema":"home-center.spotify-radio-service.v1","status":"start_failed"}\n' >&2
    return 1
  fi

  printf '{"schema":"home-center.spotify-radio-service.v1","status":"started","pid":%s}\n' "${launched_pid}"
}

stop_service() {
  local pid=""
  local attempt=0

  ensure_private_layout
  acquire_lock
  pid="$(read_service_pid)"
  if ! pid_is_running "${pid}"; then
    rm -f -- "${PID_FILE}"
    printf '{"schema":"home-center.spotify-radio-service.v1","status":"already_stopped"}\n'
    return 0
  fi
  if ! pid_is_service "${pid}"; then
    rm -f -- "${PID_FILE}"
    printf '{"schema":"home-center.spotify-radio-service.v1","status":"stale_pid_rejected","pid":%s}\n' "${pid}"
    return 0
  fi

  kill "${pid}"
  while pid_is_service "${pid}" && (( attempt < 50 )); do
    sleep 0.1
    ((attempt += 1))
  done
  if pid_is_service "${pid}"; then
    printf '{"schema":"home-center.spotify-radio-service.v1","status":"stop_timeout","pid":%s}\n' "${pid}" >&2
    return 1
  fi

  rm -f -- "${PID_FILE}"
  printf '{"schema":"home-center.spotify-radio-service.v1","status":"stopped"}\n'
}

status_service() {
  local pid=""

  ensure_private_layout
  acquire_lock
  pid="$(read_service_pid)"
  if pid_is_service "${pid}"; then
    printf '{"schema":"home-center.spotify-radio-service.v1","status":"running","pid":%s}\n' "${pid}"
    return 0
  fi
  if pid_is_running "${pid}"; then
    rm -f -- "${PID_FILE}"
    printf '{"schema":"home-center.spotify-radio-service.v1","status":"stale_pid_rejected","pid":%s}\n' "${pid}"
    return 3
  fi

  rm -f -- "${PID_FILE}"
  printf '{"schema":"home-center.spotify-radio-service.v1","status":"stopped"}\n'
  return 3
}

case "${1:-}" in
  start)
    start_service
    ;;
  stop)
    stop_service
    ;;
  status)
    status_service
    ;;
  *)
    printf 'Usage: %s {start|stop|status}\n' "${0##*/}" >&2
    exit 64
    ;;
esac
SPOTIFY_RADIO_SERVICE
chmod 700 "${SERVICE_FILE}.tmp.$$"
mv -f -- "${SERVICE_FILE}.tmp.$$" "${SERVICE_FILE}"

cat >"${BOOT_FILE}.tmp.$$" <<'SPOTIFY_RADIO_BOOT'
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

"${HOME}/bin/spotify-radio-service" start
SPOTIFY_RADIO_BOOT
chmod 700 "${BOOT_FILE}.tmp.$$"
mv -f -- "${BOOT_FILE}.tmp.$$" "${BOOT_FILE}"

SOURCE_SHA256="$(sha256sum "${SOURCE_FILE}" | awk '{print $1}')"
INSTALLED_SHA256="$(sha256sum "${INSTALLED_FILE}" | awk '{print $1}')"
if [[ "${SOURCE_SHA256}" != "${INSTALLED_SHA256}" ]]; then
  printf 'Installed Spotify radio SHA256 does not match source.\n' >&2
  exit 1
fi

"${SERVICE_FILE}" start >/dev/null

printf '{"schema":"home-center.spotify-radio-install.v1","sourceSha256":"%s","installedSha256":"%s","sha256Equal":true,"backgroundDaemon":true,"termuxBoot":true,"activityLaunchUsed":false,"genericMediaKeyUsed":false,"screenAutomationUsed":false,"pidIdentityVerified":true}\n' \
  "${SOURCE_SHA256}" "${INSTALLED_SHA256}"
