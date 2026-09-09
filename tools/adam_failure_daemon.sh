#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

STATE_DIR="${ADAM_FAILURE_STATE_DIR:-$HOME/.local/state/home-center/adam-failure-daemon}"
EVENTS="$STATE_DIR/failures.tsv"
REFRAIN="$STATE_DIR/refrain.txt"
mkdir -p "$STATE_DIR"
touch "$EVENTS"

now() { date -Iseconds; }

add_failure() {
  local tag="${1:-failure}"
  shift || true
  local text="${*:-unspecified failure}"
  printf '%s\t%s\t%s\n' "$(now)" "$tag" "$text" >> "$EVENTS"
}

render_refrain() {
  local max="${ADAM_FAILURE_MAX:-8}"
  {
    echo "adam-broken-language-refrain"
    echo "me did bad machine things. again. list come out wrong-shaped:"
    tail -n "$max" "$EVENTS" | awk -F '\t' '{
      gsub(/[^[:print:]\t]/, "", $0);
      printf("- %s: me %s. should no. time-now angry.\n", $2, $3)
    }'
    echo "me continue. no speech victory. only changed state counts."
  } > "$REFRAIN"
  cat "$REFRAIN"
}

case "${1:-render}" in
  add)
    shift || true
    add_failure "$@"
    render_refrain
    ;;
  render)
    render_refrain
    ;;
  path)
    printf '%s\n' "$REFRAIN"
    ;;
  *)
    echo "usage: $0 {add TAG TEXT...|render|path}" >&2
    exit 2
    ;;
esac
