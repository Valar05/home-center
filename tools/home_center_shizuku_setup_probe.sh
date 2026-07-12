#!/data/data/com.termux/files/usr/bin/sh
set -u

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
OUT_DIR="${HOME_CENTER_SHIZUKU_REPORT_DIR:-$ROOT/generated/shizuku_setup}"
REPORT="${HOME_CENTER_SHIZUKU_REPORT:-$OUT_DIR/home_center_shizuku_readiness.json}"
CODEX_PACKAGE="${CODEX_PACKAGE:-@mmmbuto/codex-cli-termux}"
INSTALL_APPROVED=0
INSTALL_CODEX_APPROVED=0
AUTO_PAIR=0
REPORT_ONLY=0
NO_NETWORK_INSTALL=0
PAIR_LOG=""
PAIR_ATTEMPTED=0
PAIR_OK=0

for arg in "$@"; do
  case "$arg" in
    --install-approved) INSTALL_APPROVED=1 ;;
    --install-codex-approved) INSTALL_CODEX_APPROVED=1 ;;
    --auto-pair) AUTO_PAIR=1 ;;
    --report-only) REPORT_ONLY=1 ;;
    --no-network-install) NO_NETWORK_INSTALL=1 ;;
  esac
done

mkdir -p "$OUT_DIR"

json_bool() { [ "$1" = "1" ] && printf true || printf false; }
json_escape() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g' | tr '\n' ' '
}
has_cmd() { command -v "$1" >/dev/null 2>&1; }
add_blocker() { BLOCKERS="$BLOCKERS|$1"; }
add_action() { ACTIONS="$ACTIONS|$1"; }

BLOCKERS=""
ACTIONS=""
PKG_LOG=""
CODEX_LOG=""
RISH_LOG=""
PACKAGE_INSPECTION=0
FOREGROUND_INSPECTION=0
RISH_PROBE=0
RISH_INSTALLED=0
SHIZUKU_INSTALLED=0
SHIZUKU_RUNNING=0
SHIZUKU_AUTHORIZED=0
TERMUX_INSTALLED=1
TERMUX_SOURCE_OK=1
PACKAGES_OK=0
CODEX_INSTALLED=0
HOME_CENTER_RUNNER_OK=0

if [ "$INSTALL_APPROVED" = "1" ]; then
  if has_cmd pkg; then
    if [ "$NO_NETWORK_INSTALL" = "1" ]; then
      PKG_LOG="network install skipped by --no-network-install"
    else
      pkg update -y >/dev/null 2>&1 || PKG_LOG="pkg update failed"
      pkg install -y git nodejs gh jq curl >/dev/null 2>&1 || PKG_LOG="pkg install failed"
    fi
  else
    add_blocker "pkg command not found; open this in Termux, not Android shell"
  fi
fi

if has_cmd git && has_cmd node && has_cmd npm && has_cmd gh && has_cmd curl; then
  PACKAGES_OK=1
else
  add_action "Run setup with --install-approved in Termux to install git nodejs gh jq curl"
fi

if [ "${HC_FAKE_MISSING_CODEX:-0}" = "1" ]; then
  CODEX_INSTALLED=0
elif has_cmd codex; then
  CODEX_INSTALLED=1
  CODEX_LOG="$(codex --version 2>/dev/null | head -1)"
elif [ "$INSTALL_CODEX_APPROVED" = "1" ] && has_cmd npm; then
  if [ "$NO_NETWORK_INSTALL" = "1" ]; then
    add_action "Install Codex with human approval: npm install -g $CODEX_PACKAGE"
  else
    npm install -g "$CODEX_PACKAGE" >/dev/null 2>&1 && CODEX_INSTALLED=1 || add_blocker "Codex npm install failed for $CODEX_PACKAGE"
    if has_cmd codex; then CODEX_LOG="$(codex --version 2>/dev/null | head -1)"; fi
  fi
else
  add_action "Install Codex with human approval: npm install -g $CODEX_PACKAGE"
fi

if [ -f "$ROOT/tools/home_center_codex_pair.mjs" ] && has_cmd node; then
  HOME_CENTER_RUNNER_OK=1
else
  add_blocker "Home Center Codex pairing helper is missing or node is unavailable"
fi

if has_cmd pm; then
  if [ "${HC_FAKE_MISSING_TERMUX:-0}" = "1" ]; then
    TERMUX_INSTALLED=0
  else
    pm path com.termux >/dev/null 2>&1 || TERMUX_INSTALLED=0
  fi
  if [ "${HC_FAKE_MISSING_SHIZUKU:-0}" = "1" ]; then
    SHIZUKU_INSTALLED=0
  else
    pm path moe.shizuku.privileged.api >/dev/null 2>&1 && SHIZUKU_INSTALLED=1 || SHIZUKU_INSTALLED=0
  fi
else
  add_action "Android package inspection unavailable; run from Termux on the device"
fi

find_rish() {
  if [ "${HC_FAKE_MISSING_RISH:-0}" = "1" ]; then return 1; fi
  if [ -n "${RISH:-}" ] && [ -f "$RISH" ]; then printf '%s\n' "$RISH"; return 0; fi
  if has_cmd rish; then command -v rish; return 0; fi
  for candidate in "$HOME/rish" "$HOME/bin/rish" "$HOME/.local/bin/rish" \
    "/storage/emulated/0/Android/data/moe.shizuku.privileged.api/files/rish" \
    "/storage/emulated/0/Documents/rish" "/storage/emulated/0/Download/rish"; do
    [ -f "$candidate" ] && { printf '%s\n' "$candidate"; return 0; }
  done
  return 1
}

RISH_BIN="$(find_rish 2>/dev/null || true)"
if [ -n "$RISH_BIN" ]; then
  RISH_INSTALLED=1
  chmod +x "$RISH_BIN" 2>/dev/null || true
  RISH_OUTPUT="$("$RISH_BIN" -c 'id; pm path moe.shizuku.privileged.api; dumpsys window 2>/dev/null | grep -E "mCurrentFocus|mFocusedApp" | head -2' 2>&1)"
  RISH_STATUS=$?
  RISH_LOG="$RISH_OUTPUT"
  if [ "$RISH_STATUS" = "0" ]; then
    RISH_PROBE=1
    SHIZUKU_RUNNING=1
    SHIZUKU_AUTHORIZED=1
    printf '%s\n' "$RISH_OUTPUT" | grep -q 'package:' && { PACKAGE_INSPECTION=1; SHIZUKU_INSTALLED=1; }
    printf '%s\n' "$RISH_OUTPUT" | grep -Eq 'mCurrentFocus|mFocusedApp' && FOREGROUND_INSPECTION=1
  else
    add_blocker "rish exists but the harmless probe failed; start Shizuku and authorize Termux"
  fi
else
  add_action "Export rish from Shizuku into Termux, then rerun this probe"
fi

if [ "$TERMUX_INSTALLED" != "1" ]; then add_action "Install Termux from F-Droid or official GitHub releases"; fi
if [ "$SHIZUKU_INSTALLED" != "1" ]; then add_action "Install Shizuku from https://shizuku.rikka.app/download/"; fi
if [ "$SHIZUKU_RUNNING" != "1" ]; then add_action "Start Shizuku through Wireless debugging pairing"; fi
if [ "$HOME_CENTER_RUNNER_OK" = "1" ] && [ "$CODEX_INSTALLED" = "1" ]; then :; else add_action "Run Home Center Termux pairing after readiness is green"; fi

STATUS="ready"
if [ -n "$BLOCKERS" ]; then STATUS="blocked"; elif [ -n "$ACTIONS" ] || [ "$RISH_PROBE" != "1" ] || [ "$PACKAGES_OK" != "1" ] || [ "$CODEX_INSTALLED" != "1" ]; then STATUS="partial"; fi

if [ "$AUTO_PAIR" = "1" ] && [ "$REPORT_ONLY" != "1" ]; then
  PAIR_ATTEMPTED=1
  if [ "$STATUS" = "ready" ]; then
    RAW_PAIR_LOG="$(HOME_CENTER_PAIRING_FAKE="${HOME_CENTER_PAIRING_FAKE:-0}" HC_FAKE_AM_FAIL="${HC_FAKE_AM_FAIL:-0}" node "$ROOT/tools/home_center_codex_pair.mjs" --launch-home-center 2>&1)"
    printf '%s\n' "$RAW_PAIR_LOG" | grep -q 'Paired Home Center' && PAIR_OK=1
    if [ "$PAIR_OK" = "1" ]; then
      PAIR_LOG="Paired Home Center through Shizuku; config saved under ~/.config/home-center/codex-hub.json."
    else
      PAIR_LOG="$(printf '%s\n' "$RAW_PAIR_LOG" | sed -E 's/Pairing ID: [A-Za-z0-9_-]+/Pairing ID: [redacted]/g; s/Code: [0-9]+/Code: [redacted]/g; s/for [^ ]+@[^ ]+/for [redacted-email]/g')"
    fi
  else
    PAIR_LOG="Auto-pair skipped because readiness status is $STATUS."
  fi
fi

json_array_from_pipe() {
  value="$1"
  first=1
  printf '['
  oldifs="$IFS"; IFS='|'
  for item in $value; do
    [ -z "$item" ] && continue
    [ "$first" = "1" ] || printf ','
    first=0
    printf '"%s"' "$(json_escape "$item")"
  done
  IFS="$oldifs"
  printf ']'
}

{
  printf '{\n'
  printf '  "status": "%s",\n' "$STATUS"
  printf '  "generated_at": "%s",\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date)"
  printf '  "termux": {"installed": %s, "source_ok": %s, "packages_ok": %s},\n' "$(json_bool $TERMUX_INSTALLED)" "$(json_bool $TERMUX_SOURCE_OK)" "$(json_bool $PACKAGES_OK)"
  printf '  "codex": {"installed": %s, "package": "%s", "version": "%s", "home_center_runner_ok": %s},\n' "$(json_bool $CODEX_INSTALLED)" "$(json_escape "$CODEX_PACKAGE")" "$(json_escape "$CODEX_LOG")" "$(json_bool $HOME_CENTER_RUNNER_OK)"
  printf '  "shizuku": {"installed": %s, "service_running": %s, "authorized": %s},\n' "$(json_bool $SHIZUKU_INSTALLED)" "$(json_bool $SHIZUKU_RUNNING)" "$(json_bool $SHIZUKU_AUTHORIZED)"
  printf '  "rish": {"installed": %s, "probe_ok": %s, "path": "%s"},\n' "$(json_bool $RISH_INSTALLED)" "$(json_bool $RISH_PROBE)" "$(json_escape "$RISH_BIN")"
  printf '  "automation_probe": {"package_inspection_ok": %s, "foreground_inspection_ok": %s},\n' "$(json_bool $PACKAGE_INSPECTION)" "$(json_bool $FOREGROUND_INSPECTION)"
  printf '  "pairing": {"attempted": %s, "paired": %s},\n' "$(json_bool $PAIR_ATTEMPTED)" "$(json_bool $PAIR_OK)"
  printf '  "human_actions_required": '; json_array_from_pipe "$ACTIONS"; printf ',\n'
  printf '  "blockers": '; json_array_from_pipe "$BLOCKERS"; printf ',\n'
  printf '  "diagnostics": {"pkg_log": "%s", "rish_log": "%s", "pair_log": "%s"},\n' "$(json_escape "$PKG_LOG")" "$(json_escape "$RISH_LOG")" "$(json_escape "$PAIR_LOG")"
  printf '  "diagnostics_path": "%s"\n' "$REPORT"
  printf '}\n'
} > "$REPORT"

cat "$REPORT"
printf '\nReadiness report: %s\n' "$REPORT"
