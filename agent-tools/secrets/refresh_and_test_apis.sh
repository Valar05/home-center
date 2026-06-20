#!/usr/bin/env sh
set -eu
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
RC="${HOME}/.bashrc"
SECRETS="${HOME}/.secrets/shell.env"

cd "$ROOT"
python3 agent-tools/secrets/convert_bashrc_secrets.py --apply

# Load the freshly written secrets into this process without printing values.
set -a
. "$SECRETS"
set +a

python3 agent-tools/secrets/test_api_secrets.py --rc "$RC" --secrets "$SECRETS"
