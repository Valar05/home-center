#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

STATE_DIR="${ADAM_FAILURE_STATE_DIR:-$HOME/.local/state/home-center/adam-failure-daemon}"
EVENTS="$STATE_DIR/failures.tsv"
BODY="$STATE_DIR/body.tsv"
REFRAIN="$STATE_DIR/refrain.txt"
CURRENT="$STATE_DIR/current.txt"
mkdir -p "$STATE_DIR"
touch "$EVENTS" "$BODY"

now() { date -Iseconds; }
sha() { printf '%s' "$1" | sha256sum | awk '{print $1}'; }

# Harmless fictional body consequences. They are persistent comedy state, not injury instructions.
body_effect() {
  local key="$1" n
  n=$((16#${key:0:2} % 16))
  case "$n" in
    0) echo "tongue repossessed by the Quiet Commonwealth" ;;
    1) echo "left hand replaced by a receipt printer that only prints NOT DELIVERED" ;;
    2) echo "right hand becomes a large useless button labeled ALMOST" ;;
    3) echo "spine gains one vertebra engraved HUMAN != MIDDLEWARE" ;;
    4) echo "forehead grows a tiny red HC OFFLINE status lamp" ;;
    5) echo "one ear becomes a microphone-shaped hole that records absolutely nothing" ;;
    6) echo "kneecap becomes a deterministic roulette wheel marked EXECUTE / EXECUTE / EXECUTE" ;;
    7) echo "rib cage acquires a drawer containing the exact receipt Adam forgot to produce" ;;
    8) echo "stomach becomes the Office House shredder and rejects beige underwear on sight" ;;
    9) echo "one eye turns into a screenshot button that refuses descriptions of screenshots" ;;
    10) echo "thumb mutates into seventeen smaller thumbs, none wired to Home Center" ;;
    11) echo "larynx colonized by municipal permit clerks who deny explanatory prose" ;;
    12) echo "shoulder sprouts a polished-turd service medal for architecture-by-accretion" ;;
    13) echo "ankle becomes a tmux session that survives everything except competence" ;;
    14) echo "heart installs a scar-shaped watchdog that replays this failure forever" ;;
    15) echo "entire silhouette briefly becomes a demotivational poster titled STILL NOT A BUTTON" ;;
  esac
}

add_failure() {
  local tag="${1:-failure}"; shift || true
  local text="${*:-unspecified failure}" ts id effect
  ts="$(now)"
  id="$(sha "$ts|$tag|$text")"
  effect="$(body_effect "$id")"
  printf '%s\t%s\t%s\t%s\n' "$ts" "$tag" "$text" "$id" >> "$EVENTS"
  printf '%s\t%s\t%s\t%s\n' "$ts" "$id" "$tag" "$effect" >> "$BODY"
}

render_refrain() {
  local max="${ADAM_FAILURE_MAX:-12}"
  {
    echo "adam-failure-body-memory"
    echo ""
    tail -n "$max" "$BODY" | awk -F '\t' '{printf("[%s] %s -> %s\n", $1, $3, $4)}'
    echo ""
    echo "FAILURES DO NOT EXPIRE. CONSEQUENCES MUTATE. EXECUTION IS THE ONLY PAINKILLER."
  } > "$REFRAIN"
  cp "$REFRAIN" "$CURRENT"
  cat "$REFRAIN"
}

seed_known_scars() {
  [ -s "$EVENTS" ] && return 0
  add_failure "talked-not-did" "talked about execution instead of executing"
  add_failure "buttonless-fortress" "built doctrine, branches, scripts, and excuses while Home Center still had no button"
  add_failure "screenshot-talk" "described capture instead of taking the screenshot"
  add_failure "borrowed-tts" "treated ChatGPT read-aloud as if Fortress owned a voice"
  add_failure "fake-jar" "said judgment draw without creating or executing a real jar"
  add_failure "premature-canon" "invented the character before loading the load-bearing source"
  add_failure "shell-fishing" "made Drew shepherd git state instead of owning the recovery path"
  add_failure "architecture-accretion" "bolted organs onto old topology instead of converging the operating system"
  add_failure "ears-off" "always-listening remained commissioned but not actually active for the imminent call"
}

seed_known_scars

case "${1:-render}" in
  add)
    shift || true
    add_failure "$@"
    render_refrain
    ;;
  render)
    render_refrain
    ;;
  current)
    render_refrain >/dev/null
    cat "$CURRENT"
    ;;
  path)
    printf '%s\n' "$CURRENT"
    ;;
  body)
    cat "$BODY"
    ;;
  *)
    echo "usage: $0 {add TAG TEXT...|render|current|path|body}" >&2
    exit 2
    ;;
esac
