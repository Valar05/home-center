#!/data/data/com.termux/files/usr/bin/bash
# Read-only Android installed-package continuity inspection. No credentials read.
set -u
umask 077
out="$HOME/.local/state/ritsu-control/installed-identity-readonly.txt"
mkdir -p "$(dirname "$out")"
{
  printf 'RITSU_ANDROID_IDENTITY_INSPECTION=v1\n'
  printf 'UTC=%s\n' "$(date -u +%FT%TZ)"
  printf 'OS=%s\n' "$(getprop ro.build.version.release 2>/dev/null || echo unknown)"
  printf 'TERMUX_TOKEN_PRESENT='
  if [ -s "$HOME/.config/ritsu-local-link/device-token" ]; then echo YES; else echo NO; fi
  for id in com.homecenter.ritsucontrol com.homecenter.ritsucontrol.connected com.homecenter.ritsucontrol.campaign com.homecenter.ritsucontrol.outbox com.homecenter.ritsucontrol.bridge com.homecenter.ritsucontrol.live com.homecenter.ritsucontrol.phone com.homecenter.ritsucontrol.sticky; do
    printf 'PACKAGE=%s\n' "$id"
    if command -v pm >/dev/null 2>&1; then
      result="$(pm path "$id" 2>&1)"
      case "$result" in *'package:'*) echo 'INSTALLED=YES';; *) echo 'INSTALLED=NOT_OBSERVABLE_OR_ABSENT';; esac
    else echo 'INSTALLED=PM_UNAVAILABLE'; fi
  done
  echo 'NOTE=Do not uninstall, clear app data, rotate keys or enter pairing code based on this inventory'
} | tee "$out"
chmod 600 "$out"
printf 'RECEIPT=%s\n' "$out"
