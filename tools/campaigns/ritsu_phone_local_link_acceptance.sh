#!/data/data/com.termux/files/usr/bin/bash
# Owner-run Termux acceptance for Ritsu Local Link; no Home Center cloud traffic.
# No secrets logged. Usage: bash ritsu_phone_local_link_acceptance.sh probe|pair|status|canary
set -u
umask 077
BASE='http://100.68.37.106:19646'
TOKEN_FILE="$HOME/.config/ritsu-local-link/device-token"
RECEIPT="$HOME/.local/state/ritsu-local-link/phone-campaign-receipt.txt"
TURN='2a82d599-1518-41d0-811c-d88f3069f6c0'
TAB='phone_campaign_20261024'
MARKER='RITSU_LOCAL_PHONE_CANARY_20261024_OK'
mode="${1:-probe}"
say(){ printf '%s\n' "$*"; }
fail(){ say "RITSU_CAMPAIGN=FAIL" "REASON=$*"; exit 1; }
need(){ command -v curl >/dev/null 2>&1 || fail 'curl missing; run pkg install curl'; }
receipt(){ mkdir -p "$(dirname "$RECEIPT")"; printf 'mode=%s\nresult=%s\nserver=%s\n' "$mode" "$1" "$BASE" > "$RECEIPT"; chmod 600 "$RECEIPT"; }
health(){
  need
  f="$(mktemp)" || fail 'temporary file unavailable'
  code="$(curl --noproxy '*' -sS --connect-timeout 5 --max-time 12 -H "Authorization: Bearer $token" -o "$f" -w '%{http_code}' "$BASE/v1/ritsu/status" 2>/dev/null)"; rc=$?
  [ "$rc" -eq 0 ] && [ "$code" = 200 ] && grep -Fq '"cloudOps":0' "$f" && grep -Fq '"transport":"tailscale-sse"' "$f" || { rm -f "$f"; fail "authenticated health failed (HTTP $code, curl $rc)"; }
  rm -f "$f"; say 'TAILSCALE_AUTH=PASS' 'CLOUD_OPERATIONS=0'
}
case "$mode" in
 probe)
  need; say "SERVER=$BASE"
  f="$(mktemp)"
  code="$(curl --noproxy '*' -sS --connect-timeout 5 --max-time 10 -o "$f" -w '%{http_code}' "$BASE/v1/ritsu/status" 2>/dev/null)"; rc=$?
  rm -f "$f"
  [ "$rc" -eq 0 ] && [ "$code" = 401 ] || fail "local endpoint unreachable or unexpected (HTTP $code, curl $rc)"
  say 'DIRECT_TAILSCALE=REACHABLE' 'NO_CLOUD_CALLS=1'; receipt 'preflight_pass'
  ;;
 pair)
  need
  say 'Enter the 64-character token obtained locally on THECAULDRON, not in chat.'
  printf 'Device token (hidden): '; IFS= read -r -s token; printf '\n'
  case "$token" in *[!a-f0-9]*|'') fail 'invalid token';; esac
  [ "${#token}" -eq 64 ] || fail 'invalid token length'
  health
  mkdir -p "$(dirname "$TOKEN_FILE")"
  printf '%s' "$token" > "$TOKEN_FILE"; chmod 600 "$TOKEN_FILE"; unset token
  say 'PAIRING=LOCAL_AND_VERIFIED'; receipt 'paired'
  ;;
 status|canary)
  [ -f "$TOKEN_FILE" ] || fail 'not paired: run pair'
  token="$(cat "$TOKEN_FILE")"
  health
  if [ "$mode" = canary ]; then
    body='{"turnId":"2a82d599-1518-41d0-811c-d88f3069f6c0","tabId":"phone_campaign_20261024","text":"Reply with exactly RITSU_LOCAL_PHONE_CANARY_20261024_OK and nothing else."}'
    f="$(mktemp)"
    code="$(curl --noproxy '*' -sS --connect-timeout 5 --max-time 15 -H "Authorization: Bearer $token" -H 'Content-Type: application/json' --data-binary "$body" -o "$f" -w '%{http_code}' "$BASE/v1/ritsu/turn" 2>/dev/null)"; rc=$?
    if [ "$rc" -ne 0 ] || { [ "$code" != 200 ] && [ "$code" != 202 ]; } || ! grep -Fq '"accepted":true' "$f"; then rm -f "$f"; receipt 'submission_uncertain'; fail "turn not confirmed, do not regenerate ID (HTTP $code)"; fi
    rm -f "$f"; say 'TURN=ACCEPTED_OR_IDEMPOTENT'
    f="$(mktemp)"
    curl --noproxy '*' -sS --no-buffer --connect-timeout 5 --max-time 75 -H "Authorization: Bearer $token" "$BASE/v1/ritsu/events?after=0" 2>/dev/null |
      awk -v id="$TURN" -v marker="$MARKER" '
      /^data: / && index($0,id) {
        if(index($0,"\"type\":\"partial\"")) { print "EVENT=PARTIAL"; fflush(); }
        if(index($0,"\"type\":\"uncertain\"")) { print "CANARY=UNCERTAIN"; fflush(); exit; }
        if(index($0,"\"type\":\"complete\"")) {
          if(index($0,marker)) print "CANARY=PASS"; else print "CANARY=WRONG_REPLY";
          fflush(); exit;
        }
      }' | tee "$f"
    if grep -Fq 'CANARY=PASS' "$f"; then receipt 'end_to_end_pass'; else receipt 'no_final'; rm -f "$f"; fail 'end-to-end canary did not complete'; fi
    rm -f "$f"
  else receipt 'authenticated_status_pass'; fi
  ;;
 unpair) rm -f "$TOKEN_FILE"; receipt 'unpaired'; say 'PAIRING=REMOVED';;
 *) fail 'usage: probe|pair|status|canary|unpair';;
esac
say "RECEIPT=$RECEIPT"
