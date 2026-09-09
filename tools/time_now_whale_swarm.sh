#!/usr/bin/env bash
set -euo pipefail
ROOT="${HC_REPO_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
STATE="${HC_STATE_DIR:-$HOME/.local/state/home-center}/time-now-whale"
mkdir -p "$STATE/prompts" "$STATE/receipts"
CAMPAIGN="$ROOT/campaigns/time-now-skill-census.md"

if command -v codex >/dev/null 2>&1; then WORKER=codex
elif command -v continue >/dev/null 2>&1; then WORKER=continue
else
  printf '%s\n' '{"status":"blocked","reason":"no-local-coding-worker"}' | tee "$STATE/receipts/dispatch.json"
  exit 2
fi

write_prompt(){
  lane="$1"; scope="$2"
  cat >"$STATE/prompts/$lane.txt" <<EOF
Read $CAMPAIGN. You are the bounded $lane lane of the Time Now census.
Scope: $scope
Eat the whale one bite at a time. Inventory before synthesis. Preserve timestamps, authority state, aliases, provenance, memorable names, and evidence. Write only this lane's findings under $STATE/receipts. Do not ask Drew questions. Do not declare global completion. Include a brief joy_note for failures without altering factual evidence.
EOF
}
write_prompt repo 'repository skills, doctrines, organs, jars, contracts and campaigns'
write_prompt library 'Library inventory and receipts, chronology first'
write_prompt drive 'Drive skill, doctrine and index surfaces'
write_prompt thread 'durable thread exports, context dumps and receipts'
write_prompt aliases 'reconcile aliases from lane receipts without guessing'
write_prompt index 'build the chronological Time Now index from receipts'
write_prompt canary 'test Aggregated Synthesis versus Guinness plus Hunger, Thirst and Hair Away/Airway fixtures'

for lane in repo library drive thread aliases index canary; do
  session="tn-whale-$lane"
  tmux has-session -t "$session" 2>/dev/null && continue
  prompt="$STATE/prompts/$lane.txt"
  log="$STATE/receipts/$lane.worker.log"
  if [ "$WORKER" = codex ]; then
    tmux new-session -d -s "$session" "cd '$ROOT' && codex exec --full-auto \"\$(cat '$prompt')\" >'$log' 2>&1"
  else
    tmux new-session -d -s "$session" "cd '$ROOT' && continue \"\$(cat '$prompt')\" >'$log' 2>&1"
  fi
done

printf '{"schema":"time-now-whale-dispatch-v1","status":"dispatched","worker":"%s","acceptance":"lane receipts plus merged index plus passing canary"}\n' "$WORKER" | tee "$STATE/receipts/dispatch.json"
