#!/data/data/com.termux/files/usr/bin/bash
# Install the bounded, read-only Ritsu phone-gap campaign on Termux.
# No audio receiver changes, voice model changes, or relay restarts.
set -Eeuo pipefail

SOURCE_REF="9fbc3cfbb6ecd29009e2f07dac9b4348462112cb"
SOURCE_BASE="https://raw.githubusercontent.com/Valar05/home-center/$SOURCE_REF/tools/campaigns"
CAMPAIGN_HOME="$HOME/.local/share/ritsu-phone-gap"
SCRIPT="$CAMPAIGN_HOME/ritsu_phone_gap_campaign.py"
TESTS="$CAMPAIGN_HOME/test_ritsu_phone_gap_campaign.py"
ENTRY="$PREFIX/bin/ritsu-gap"
TEMP=""
STAGE="download"
receipt() {
  local message="$1"
  printf '%s\n' "$message"
  if command -v termux-clipboard-set >/dev/null 2>&1; then
    printf '%s\n' "$message" | termux-clipboard-set >/dev/null 2>&1 ||
      printf 'RITSU_GAP_CLIPBOARD_UNAVAILABLE\n'
  else
    printf 'RITSU_GAP_CLIPBOARD_UNAVAILABLE\n'
  fi
}
failure() {
  local code="$?"
  trap - ERR
  receipt "RITSU_GAP_INSTALL_FAILED
STAGE=$STAGE
EXIT_CODE=$code
SCRIPT=$SCRIPT
NO_AUDIO_CHANGES=1"
  exit "$code"
}
cleanup() {
  if [[ -n "$TEMP" && -d "$TEMP" ]]; then rm -rf -- "$TEMP"; fi
}
trap failure ERR
trap cleanup EXIT

for command in curl python3 cmp mktemp; do
  if ! command -v "$command" >/dev/null 2>&1; then
    receipt "RITSU_GAP_INSTALL_FAILED
STAGE=preflight
MISSING=$command
NO_AUDIO_CHANGES=1"
    exit 10
  fi
done
mkdir -p "$CAMPAIGN_HOME" "$PREFIX/bin"
TEMP="$(mktemp -d "$CAMPAIGN_HOME/.candidate.XXXXXXXX")"
chmod 700 "$TEMP"
STAGE="download-pinned-source"
curl --fail --location --silent --show-error --retry 2 \
  "$SOURCE_BASE/ritsu_phone_gap_campaign.py" -o "$TEMP/ritsu_phone_gap_campaign.py"
curl --fail --location --silent --show-error --retry 2 \
  "$SOURCE_BASE/test_ritsu_phone_gap_campaign.py" -o "$TEMP/test_ritsu_phone_gap_campaign.py"

STAGE="validate-source"
python3 -m py_compile "$TEMP/ritsu_phone_gap_campaign.py" "$TEMP/test_ritsu_phone_gap_campaign.py"
python3 "$TEMP/test_ritsu_phone_gap_campaign.py" >"$TEMP/tests.log" 2>&1 ||
  { tail -n 30 "$TEMP/tests.log" >&2; false; }

STAGE="preserve-existing-installation"
for basename in ritsu_phone_gap_campaign.py test_ritsu_phone_gap_campaign.py; do
  if [[ -e "$CAMPAIGN_HOME/$basename" ]] &&
     ! cmp -s "$CAMPAIGN_HOME/$basename" "$TEMP/$basename"; then
    receipt "RITSU_GAP_INSTALL_RECONCILIATION_REQUIRED
EXISTING=$CAMPAIGN_HOME/$basename
REFUSED_TO_OVERWRITE=1
NO_AUDIO_CHANGES=1"
    exit 11
  fi
done
if [[ -e "$ENTRY" ]] && ! grep -Fq 'ritsu_phone_gap_campaign.py' "$ENTRY"; then
  receipt "RITSU_GAP_INSTALL_RECONCILIATION_REQUIRED
EXISTING=$ENTRY
REFUSED_TO_OVERWRITE=1
NO_AUDIO_CHANGES=1"
  exit 12
fi

STAGE="install-atomic"
for basename in ritsu_phone_gap_campaign.py test_ritsu_phone_gap_campaign.py; do
  if [[ ! -e "$CAMPAIGN_HOME/$basename" ]]; then
    mv -- "$TEMP/$basename" "$CAMPAIGN_HOME/$basename"
    chmod 600 "$CAMPAIGN_HOME/$basename"
  fi
done
if [[ ! -e "$ENTRY" ]]; then
  printf '#!/data/data/com.termux/files/usr/bin/bash\nexec python3 "$HOME/.local/share/ritsu-phone-gap/ritsu_phone_gap_campaign.py" "$@"\n' \
    >"$TEMP/ritsu-gap"
  chmod 700 "$TEMP/ritsu-gap"
  mv -- "$TEMP/ritsu-gap" "$ENTRY"
fi

STAGE="start-readonly-inspection"
"$ENTRY" run
receipt "RITSU_GAP_CAMPAIGN_INSTALLED=1
PINNED_COMMIT=$SOURCE_REF
COMMAND=ritsu-gap
NEXT=ritsu-gap status
RECEIPTS=ritsu-gap receipts
STOP=ritsu-gap stop
NO_AUDIO_CHANGES=1
NOTE=LAUNCHED_NOT_HEARD"
