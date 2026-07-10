#!/data/data/com.termux/files/usr/bin/sh
set -eu

SECRET_NAME="ELEVENLABS_API_KEY"
SECRET_ENV="${HOME}/.secrets/shell.env"
FIREBASE_PROJECT=""
READ_STDIN=0
SHELL_ONLY=0
VERIFY_ONLY=0

usage() {
  cat <<'EOF'
Usage: sh tools/ingest_elevenlabs_key.sh [options]

Safely ingest an ElevenLabs API key for Home Center without printing it.

Options:
  --firebase-project PROJECT   Also set Google Secret Manager secret ELEVENLABS_API_KEY for Firebase Functions.
  --shell-only                 Only write ~/.secrets/shell.env; do not call gcloud.
  --stdin                      Read the key from stdin instead of hidden terminal input.
  --verify                     Verify configured locations without prompting for a key.
  -h, --help                   Show this help.

Examples:
  sh tools/ingest_elevenlabs_key.sh
  sh tools/ingest_elevenlabs_key.sh --firebase-project home-center-dclar
  printf '%s' "$ELEVENLABS_API_KEY" | sh tools/ingest_elevenlabs_key.sh --stdin --firebase-project home-center-dclar
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --firebase-project)
      FIREBASE_PROJECT="${2:-}"
      if [ -z "$FIREBASE_PROJECT" ]; then echo "--firebase-project requires a value." >&2; exit 2; fi
      shift 2
      ;;
    --shell-only) SHELL_ONLY=1; shift ;;
    --stdin) READ_STDIN=1; shift ;;
    --verify) VERIFY_ONLY=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

mask_status() {
  if [ "$1" -gt 0 ]; then echo "present length=$1 sha256_prefix=$2"; else echo "missing"; fi
}

verify_shell_secret() {
  python3 - "$SECRET_ENV" "$SECRET_NAME" <<'PY'
import hashlib, os, re, sys
path, name = sys.argv[1], sys.argv[2]
value = ''
if os.path.exists(path):
    for line in open(path, encoding='utf-8'):
        m = re.match(r'^(?:export\s+)?' + re.escape(name) + r'=(.*)$', line.strip())
        if m:
            raw = m.group(1).strip()
            if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
                raw = raw[1:-1]
            value = raw
if value:
    print(f'present length={len(value)} sha256_prefix={hashlib.sha256(value.encode()).hexdigest()[:10]}')
else:
    print('missing')
PY
}

verify_gcloud_secret() {
  project="$1"
  if ! command -v gcloud >/dev/null 2>&1; then
    echo "gcloud CLI missing; cannot verify Google Secret Manager secret." >&2
    exit 127
  fi
  out="${TMPDIR:-/data/data/com.termux/files/usr/tmp}/home_center_elevenlabs_secret_verify.$$"
  err="${TMPDIR:-/data/data/com.termux/files/usr/tmp}/home_center_elevenlabs_secret_verify_err.$$"
  if ! gcloud secrets versions access latest --secret="$SECRET_NAME" --project="$project" >"$out" 2>"$err"; then
    echo "gcloud secret $SECRET_NAME: missing or inaccessible for project $project" >&2
    sed -n '1,4p' "$err" >&2 || true
    rm -f "$out" "$err"
    exit 1
  fi
  bytes="$(wc -c < "$out" | tr -d ' ')"
  hash_prefix="$(sha256sum "$out" | awk '{print substr($1,1,10)}')"
  rm -f "$out" "$err"
  printf 'gcloud %s: %s\n' "$SECRET_NAME" "$(mask_status "$bytes" "$hash_prefix")"
}

if [ "$VERIFY_ONLY" -eq 1 ]; then
  printf 'shell %s: ' "$SECRET_NAME"
  verify_shell_secret
  if [ -n "$FIREBASE_PROJECT" ]; then verify_gcloud_secret "$FIREBASE_PROJECT"; fi
  exit 0
fi

if [ "$READ_STDIN" -eq 1 ]; then
  KEY_VALUE="$(cat)"
elif [ -n "${ELEVENLABS_API_KEY:-}" ]; then
  KEY_VALUE="$ELEVENLABS_API_KEY"
else
  printf 'Paste ElevenLabs API key. Input is hidden: ' >&2
  old_stty="$(stty -g 2>/dev/null || true)"
  stty -echo 2>/dev/null || true
  IFS= read -r KEY_VALUE
  if [ -n "$old_stty" ]; then stty "$old_stty" 2>/dev/null || true; fi
  printf '\n' >&2
fi

KEY_VALUE="$(printf '%s' "$KEY_VALUE" | tr -d '\r\n')"
if [ -z "$KEY_VALUE" ]; then echo "No key was provided." >&2; exit 2; fi
case "$KEY_VALUE" in *[[:space:]]*) echo "Refusing key with whitespace." >&2; exit 2 ;; esac

mkdir -p "$(dirname "$SECRET_ENV")"
chmod 700 "$(dirname "$SECRET_ENV")" 2>/dev/null || true
TMP_FILE="${SECRET_ENV}.tmp.$$"
export SECRET_ENV SECRET_NAME KEY_VALUE TMP_FILE
python3 - <<'PY'
import os, re
path = os.environ['SECRET_ENV']
name = os.environ['SECRET_NAME']
value = os.environ['KEY_VALUE']
tmp = os.environ['TMP_FILE']
lines = []
if os.path.exists(path):
    with open(path, encoding='utf-8') as handle:
        lines = handle.read().splitlines()
pattern = re.compile(r'^(?:export\s+)?' + re.escape(name) + r'=')
out = [line for line in lines if not pattern.match(line.strip())]
out.append(f'export {name}={value}')
with open(tmp, 'w', encoding='utf-8') as handle:
    handle.write('\n'.join(out) + '\n')
os.chmod(tmp, 0o600)
os.replace(tmp, path)
os.chmod(path, 0o600)
PY
unset KEY_VALUE

echo "Stored $SECRET_NAME in $SECRET_ENV without printing the value."
printf 'shell %s: ' "$SECRET_NAME"
verify_shell_secret

if [ "$SHELL_ONLY" -eq 1 ]; then exit 0; fi

if [ -n "$FIREBASE_PROJECT" ]; then
  if ! command -v gcloud >/dev/null 2>&1; then
    echo "gcloud CLI is not installed; shell secret was stored only." >&2
    exit 127
  fi
  . "$SECRET_ENV"
  if [ -z "${ELEVENLABS_API_KEY:-}" ]; then echo "Stored shell secret could not be loaded." >&2; exit 1; fi
  if gcloud secrets describe "$SECRET_NAME" --project="$FIREBASE_PROJECT" >/dev/null 2>&1; then
    printf '%s\n' "$ELEVENLABS_API_KEY" | gcloud secrets versions add "$SECRET_NAME" --data-file=- --project="$FIREBASE_PROJECT"
  else
    printf '%s\n' "$ELEVENLABS_API_KEY" | gcloud secrets create "$SECRET_NAME" --replication-policy=automatic --data-file=- --project="$FIREBASE_PROJECT"
  fi
  unset ELEVENLABS_API_KEY
  echo "Set Google Secret Manager secret $SECRET_NAME for project $FIREBASE_PROJECT."
else
  echo "Cloud secret not set. Re-run with: sh tools/ingest_elevenlabs_key.sh --firebase-project home-center-dclar"
fi
