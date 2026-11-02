#!/data/data/com.termux/files/usr/bin/bash
# Ritsu existing-identity inventory: READ ONLY. Never request, print, rotate or copy a token.
set -Eeuo pipefail
umask 077
BASE='http://100.68.37.106:19646'
TOKEN_FILE="$HOME/.config/ritsu-local-link/device-token"
RECEIPT="$HOME/.local/state/ritsu-local-link/reuse-inventory.txt"
mkdir -p "$(dirname "$RECEIPT")"
status='UNKNOWN'
detail='NONE'
if [ ! -f "$TOKEN_FILE" ]; then
  status='NO_TERMUX_CREDENTIAL'
  detail='Do not pair yet: inspect existing Android app or another owner-approved credential authority'
elif [ ! -r "$TOKEN_FILE" ]; then
  status='CREDENTIAL_NOT_READABLE'
  detail='Private Termux credential exists but is not readable'
elif ! command -v curl >/dev/null 2>&1; then
  status='CURL_UNAVAILABLE'
  detail='Cannot perform existing-credential verification'
else
  # Read only, never print content, never send to Git/Drive/ChatGPT.
  token="$(cat "$TOKEN_FILE")"
  if [[ ! "$token" =~ ^[a-f0-9]{64}$ ]]; then
    status='CREDENTIAL_FORMAT_INVALID'
    detail='Existing file is not a valid 64-character local-link token'
  else
    tmp="$(mktemp)"
    trap 'rm -f "$tmp"' EXIT
    code="$(curl --noproxy '*' --silent --show-error --connect-timeout 5 --max-time 12 \
      -H "Authorization: Bearer $token" -o "$tmp" -w '%{http_code}' \
      "$BASE/v1/ritsu/status" 2>/dev/null)" || code='NETWORK_ERROR'
    if [ "$code" = '200' ] && grep -Fq '"cloudOps":0' "$tmp" && grep -Fq '"transport":"tailscale-sse"' "$tmp"; then
      status='EXISTING_IDENTITY_AUTHENTICATED'
      detail='Termux credential can be reused without a new pairing ceremony'
    else
      status='EXISTING_CREDENTIAL_NOT_AUTHENTICATED'
      detail="Authentication unavailable or rejected (HTTP $code); do not overwrite or rotate credentials"
    fi
    unset token
  fi
fi
printf 'RITSU_IDENTITY_REUSE=%s\nDETAIL=%s\nPHONE_APP_PAIRING=NOT_INSPECTED\nPAIRING_TOKEN_EXPOSED=NO\n' "$status" "$detail" | tee "$RECEIPT"
chmod 600 "$RECEIPT"
printf 'RECEIPT=%s\n' "$RECEIPT"
