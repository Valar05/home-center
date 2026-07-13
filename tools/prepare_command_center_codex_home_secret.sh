#!/data/data/com.termux/files/usr/bin/sh
set -eu

PROJECT="${1:-${FIREBASE_PROJECT:-home-center-dclar}}"
SECRET="${COMMAND_CENTER_CODEX_HOME_SECRET:-COMMAND_CENTER_CODEX_HOME_TGZ}"
CODEX_SOURCE_HOME="${CODEX_SOURCE_HOME:-$HOME/.codex}"
TMP_ROOT="${TMPDIR:-/data/data/com.termux/files/usr/tmp}/command-center-codex-home-secret-$$"
STAGE="$TMP_ROOT/codex-home"
ARCHIVE="$TMP_ROOT/codex-home.tgz"
PAYLOAD="$TMP_ROOT/codex-home.tgz.b64"

cleanup() {
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT INT TERM

umask 077
mkdir -p "$STAGE"

for rel in auth.json config.toml; do
  src="$CODEX_SOURCE_HOME/$rel"
  if [ ! -f "$src" ]; then
    echo "Missing required Codex auth file: $CODEX_SOURCE_HOME/$rel" >&2
    exit 2
  fi
  cp "$src" "$STAGE/$rel"
  chmod 600 "$STAGE/$rel"
done

(cd "$STAGE" && tar -czf "$ARCHIVE" auth.json config.toml)
SHA256="$(sha256sum "$ARCHIVE" | awk '{print $1}')"
base64 -w 0 "$ARCHIVE" > "$PAYLOAD"

if ! gcloud secrets describe "$SECRET" --project "$PROJECT" >/dev/null 2>&1; then
  gcloud secrets create "$SECRET" --project "$PROJECT" --replication-policy automatic >/dev/null
fi

gcloud secrets versions add "$SECRET" --project "$PROJECT" --data-file "$PAYLOAD" >/dev/null

cat <<EOF
Command Center Codex auth bundle stored.
  project: $PROJECT
  secret: $SECRET
  files: auth.json config.toml
  archive_sha256: $SHA256
  transport: base64-wrapped-tgz
  contents_printed: false
EOF
