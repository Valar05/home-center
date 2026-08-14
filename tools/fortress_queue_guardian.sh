#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

BASE="${FORTRESS_QUEUE_BASE:-$HOME/.fortress}"
BIN="$BASE/bin"
STATE="$BASE/state"
LOG="$BASE/log"
MAX_TASK_SECONDS="${FORTRESS_QUEUE_MAX_TASK_SECONDS:-120}"
POLL_SECONDS="${FORTRESS_QUEUE_GUARD_POLL_SECONDS:-10}"
EVENTS="$LOG/queue-guardian.jsonl"
SESSION="${FORTRESS_QUEUE_GUARD_SESSION:-fortress-queue-guardian}"
QUEUE_SESSION="${FORTRESS_QUEUE_SESSION:-fortress}"
MODE="${1:-run}"

mkdir -p "$BIN" "$STATE" "$LOG"

jlog() {
  python3 - "$EVENTS" "$@" <<'PY'
import json,sys,time
path=sys.argv[1]
d={"at_epoch":int(time.time())}
for item in sys.argv[2:]:
    if "=" in item:
        k,v=item.split("=",1)
        d[k]=v
with open(path,"a",encoding="utf-8") as f:
    f.write(json.dumps(d,sort_keys=True)+"\n")
PY
}

queue_daemon_pid() {
  ps -eo pid=,args= 2>/dev/null | awk '
    /fortress-device-queue/ && !/awk/ {print $1; exit}
    /\.fortress\/bin\/fortressd/ && !/awk/ {print $1; exit}
  '
}

queue_daemon_cmd() {
  if command -v fortress-device-queue >/dev/null 2>&1; then
    command -v fortress-device-queue
  elif [ -x "$BIN/fortressd" ]; then
    printf '%s\n' "$BIN/fortressd"
  elif [ -x "$HOME/bin/fortress-device-queue" ]; then
    printf '%s\n' "$HOME/bin/fortress-device-queue"
  else
    return 1
  fi
}

kill_task_tree() {
  local root="$1"
  mapfile -t rows < <(ps -eo pid=,ppid= 2>/dev/null)
  local descendants=("$root") changed row pid ppid known existing seen i
  changed=1
  while [ "$changed" -eq 1 ]; do
    changed=0
    for row in "${rows[@]}"; do
      set -- $row
      pid="${1:-}"; ppid="${2:-}"
      [ -n "$pid" ] && [ -n "$ppid" ] || continue
      for known in "${descendants[@]}"; do
        if [ "$ppid" = "$known" ]; then
          seen=0
          for existing in "${descendants[@]}"; do [ "$pid" = "$existing" ] && seen=1 && break; done
          if [ "$seen" -eq 0 ]; then descendants+=("$pid"); changed=1; fi
          break
        fi
      done
    done
  done
  for ((i=${#descendants[@]}-1; i>=0; i--)); do kill -TERM "${descendants[$i]}" 2>/dev/null || true; done
  sleep 2
  for ((i=${#descendants[@]}-1; i>=0; i--)); do kill -KILL "${descendants[$i]}" 2>/dev/null || true; done
  jlog kind=queue.task.timeout action=kill_task_tree root_pid="$root" max_seconds="$MAX_TASK_SECONDS"
}

ensure_daemon() {
  local pid cmd
  pid="$(queue_daemon_pid || true)"
  [ -n "$pid" ] && return 0
  cmd="$(queue_daemon_cmd || true)"
  if [ -z "$cmd" ]; then
    jlog kind=queue.daemon.missing action=none
    return 1
  fi
  tmux has-session -t "$QUEUE_SESSION" 2>/dev/null && tmux kill-session -t "$QUEUE_SESSION" 2>/dev/null || true
  tmux new-session -d -s "$QUEUE_SESSION" "$cmd"
  sleep 2
  pid="$(queue_daemon_pid || true)"
  if [ -n "$pid" ]; then
    jlog kind=queue.daemon.recovered action=tmux_start pid="$pid" command="$cmd"
    return 0
  fi
  jlog kind=queue.daemon.recovery_failed action=tmux_start command="$cmd"
  return 1
}

watch_once() {
  ensure_daemon || true
  local daemon pid ppid age args
  daemon="$(queue_daemon_pid || true)"
  [ -n "$daemon" ] || return 0
  while read -r pid ppid age args; do
    [ "${ppid:-}" = "$daemon" ] || continue
    [ "${age:-0}" -ge "$MAX_TASK_SECONDS" ] 2>/dev/null || continue
    case "${args:-}" in
      *"timeout 1800 bash"*|*"timeout 1800"*".task"*|*"timeout 1800"*".sh"*)
        jlog kind=queue.task.stuck_detected pid="$pid" ppid="$ppid" age_seconds="$age" command="$args"
        kill_task_tree "$pid"
        ;;
    esac
  done < <(ps -eo pid=,ppid=,etimes=,args= 2>/dev/null)
}

install_guardian() {
  local dest="$BIN/fortress-queue-guardian"
  install -m 700 "$0" "$dest"
  tmux kill-session -t "$SESSION" 2>/dev/null || true
  tmux new-session -d -s "$SESSION" "$dest" run
  sleep 1
  local pid daemon
  pid="$(ps -eo pid=,args= | awk '/fortress-queue-guardian/ && !/awk/ {print $1; exit}')"
  daemon="$(queue_daemon_pid || true)"
  python3 - "$dest" "$pid" "$daemon" "$MAX_TASK_SECONDS" "$POLL_SECONDS" <<'PY'
import json,sys,time
path,pid,daemon,maxs,polls=sys.argv[1:]
print(json.dumps({
  "schema":"fortress.queue-guardian.install.v1",
  "ok":bool(pid),
  "installed":path,
  "guardian_pid":pid or None,
  "queue_daemon_pid":daemon or None,
  "max_task_seconds":int(maxs),
  "poll_seconds":int(polls),
  "at_epoch":int(time.time()),
},sort_keys=True))
PY
}

case "$MODE" in
  install) install_guardian ;;
  once) watch_once ;;
  run)
    while :; do
      watch_once
      sleep "$POLL_SECONDS"
    done
    ;;
  *) echo "usage: $0 {install|once|run}" >&2; exit 64 ;;
esac
