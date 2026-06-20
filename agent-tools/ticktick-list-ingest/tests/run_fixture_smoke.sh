#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/../../.."
out=".tmp/home-center-ticktick-ingest-items.txt"
mkdir -p .tmp
python3 agent-tools/ticktick-list-ingest/ticktick_list_ingest.py echo \
  --fixture agent-tools/ticktick-list-ingest/tests/fixtures/project_data_sample.json \
  --expect-count 3 > "$out"
actual="$(cat "$out")"
expected="eggs
whole milk
bread"
if [ "$actual" != "$expected" ]; then
  echo "unexpected fixture echo:" >&2
  cat "$out" >&2
  exit 1
fi
printf '%s\n' "ticktick-list-ingest fixture: OK"
