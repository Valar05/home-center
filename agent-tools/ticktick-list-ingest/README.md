# TickTick List Ingest Agent Tool

This subproject is for agents, not the Android UI. It reads a TickTick project/list through the public Open API and prints active task titles as terminal lines so another agent step can consume the current shopping list directly.


## Store token locally

Use a local prompt so the token is not pasted into chat or shell history:

```sh
sh agent-tools/ticktick-list-ingest/store_ticktick_secret.sh --terminal
python3 agent-tools/ticktick-list-ingest/ticktick_list_ingest.py echo --list shopping --token-file agent-tools/ticktick-list-ingest/.secrets/ticktick_token --expect-count 46
```

Other storage modes:

```sh
sh agent-tools/ticktick-list-ingest/store_ticktick_secret.sh --dialog
sh agent-tools/ticktick-list-ingest/store_ticktick_secret.sh --clipboard
```

The token file is written under `.secrets/`, which is ignored by git. The helper prints only the file path and byte count, never the token.

## Live shopping-list echo

Set a token without putting it in the command history:

```sh
export TICKTICK_TOKEN='...'
python3 agent-tools/ticktick-list-ingest/ticktick_list_ingest.py echo --list shopping --expect-count 46
```

Or keep the token in a local untracked file:

```sh
python3 agent-tools/ticktick-list-ingest/ticktick_list_ingest.py echo --list shopping --token-file /path/to/token.txt --expect-count 46
```

The command prints only item titles to stdout. Status and count checks go to stderr. A count mismatch exits nonzero.

## Cache an ingest

```sh
python3 agent-tools/ticktick-list-ingest/ticktick_list_ingest.py ingest --list shopping --cache agent-tools/ticktick-list-ingest/data/last_ingest.json
python3 agent-tools/ticktick-list-ingest/ticktick_list_ingest.py echo --from-cache --expect-count 46
```

## Offline fixture smoke

```sh
python3 agent-tools/ticktick-list-ingest/ticktick_list_ingest.py echo --fixture agent-tools/ticktick-list-ingest/tests/fixtures/project_data_sample.json --expect-count 3
```

## Token handling

The tool checks `TICKTICK_TOKEN`, `TICKTICK_API_TOKEN`, and `TIKTIK_TOKEN`, or a `--token-file`. It never prints token values. Do not commit token files or cached private shopping output unless the contents are intentionally shareable.
