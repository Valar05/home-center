#!/data/data/com.termux/files/usr/bin/sh
set -eu

PROJECT="${FIREBASE_PROJECT:-home-center-dclar}"
OWNER="${HOME_CENTER_GITHUB_ADMIN_OWNER:-Valar05}"
APP_NAME="${HOME_CENTER_GITHUB_APP_NAME:-Home Center GitHub Admin}"
REDIRECT_URL="${HOME_CENTER_GITHUB_APP_REDIRECT_URL:-https://github.com/Valar05/home-center}"
MODE="${1:-status}"
PRIVATE_STATE_DIR="${HOME_CENTER_GITHUB_ADMIN_PRIVATE_DIR:-${TMPDIR:-/data/data/com.termux/files/usr/tmp}/home-center-github-admin}"
WORK_DIR=""

cleanup() {
  if [ -n "$WORK_DIR" ] && [ -d "$WORK_DIR" ]; then
    find "$WORK_DIR" -type f -exec chmod 600 {} \; 2>/dev/null || true
    rm -f "$WORK_DIR/conversion.json" "$WORK_DIR/app.pem" "$WORK_DIR/installations.json" "$WORK_DIR/app.json"
    rmdir "$WORK_DIR" 2>/dev/null || true
  fi
}
trap cleanup EXIT HUP INT TERM
umask 077

make_work_dir() {
  mkdir -p "$PRIVATE_STATE_DIR"
  chmod 700 "$PRIVATE_STATE_DIR"
  WORK_DIR="$(mktemp -d "$PRIVATE_STATE_DIR/session.XXXXXX")"
  chmod 700 "$WORK_DIR"
}

html_escape() {
  node -e 'process.stdout.write(String(process.argv[1]).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"))' "$1"
}

manifest_code_from_arg() {
  raw="$1"
  node -e '
const raw = process.argv[1] || "";
try {
  const url = new URL(raw);
  process.stdout.write(url.searchParams.get("code") || raw);
} catch (_) {
  const match = raw.match(/[?&]code=([^&#]+)/);
  process.stdout.write(match ? decodeURIComponent(match[1]) : raw);
}
' "$raw"
}

set_secret() {
  name="$1"
  value="$2"
  if gcloud secrets describe "$name" --project "$PROJECT" >/dev/null 2>&1; then
    printf '%s' "$value" | gcloud secrets versions add "$name" --project "$PROJECT" --data-file=- >/dev/null
  else
    printf '%s' "$value" | gcloud secrets create "$name" --project "$PROJECT" --replication-policy=automatic --data-file=- >/dev/null
  fi
  echo "$name stored for $PROJECT"
}

set_secret_from_file() {
  name="$1"
  source_file="$2"
  if gcloud secrets describe "$name" --project "$PROJECT" >/dev/null 2>&1; then
    gcloud secrets versions add "$name" --project "$PROJECT" --data-file="$source_file" >/dev/null
  else
    gcloud secrets create "$name" --project "$PROJECT" --replication-policy=automatic --data-file="$source_file" >/dev/null
  fi
  echo "$name stored for $PROJECT"
}

validate_private_key() {
  key_file="$1"
  node - "$key_file" <<'NODE'
const {createPrivateKey} = require('node:crypto');
const fs = require('node:fs');
const key = fs.readFileSync(process.argv[2], 'utf8');
if (!key.includes('BEGIN') || !key.includes('PRIVATE KEY')) throw new Error('not a PEM private key');
createPrivateKey(key);
NODE
}

load_private_key() {
  supplied_file="${1:-}"
  make_work_dir
  if [ -n "$supplied_file" ]; then
    if [ ! -f "$supplied_file" ]; then echo "Private key file not found: $supplied_file" >&2; exit 2; fi
    cp "$supplied_file" "$WORK_DIR/app.pem"
  else
    gcloud secrets versions access latest --secret=GITHUB_APP_PRIVATE_KEY --project "$PROJECT" > "$WORK_DIR/app.pem"
  fi
  chmod 600 "$WORK_DIR/app.pem"
  validate_private_key "$WORK_DIR/app.pem"
}

make_manifest() {
  cat <<JSON
{
  "name": "$APP_NAME",
  "url": "https://github.com/Valar05/home-center",
  "hook_attributes": {"url": "https://github.com/Valar05/home-center", "active": false},
  "redirect_url": "$REDIRECT_URL",
  "public": false,
  "default_permissions": {
    "metadata": "read",
    "checks": "write",
    "contents": "write",
    "pull_requests": "write",
    "issues": "write",
    "actions": "write",
    "workflows": "write",
    "administration": "write"
  },
  "default_events": ["push", "pull_request", "check_run", "check_suite", "workflow_run", "issues"]
}
JSON
}

write_manifest_form() {
  mkdir -p "$PRIVATE_STATE_DIR"
  chmod 700 "$PRIVATE_STATE_DIR"
  manifest="$(make_manifest)"
  form="$PRIVATE_STATE_DIR/github_app_manifest_form.html"
  escaped_manifest="$(html_escape "$manifest")"
  cat > "$form" <<HTML
<!doctype html>
<html><head><meta charset="utf-8"><title>Home Center GitHub App Manifest</title></head>
<body>
<form action="https://github.com/settings/apps/new?state=home-center-github-admin" method="post">
  <textarea name="manifest" style="display:none">$escaped_manifest</textarea>
  <button type="submit">Create Home Center GitHub App</button>
</form>
<p>After GitHub redirects to the Home Center repo, copy the full browser URL from the address bar and run:</p>
<pre>sh tools/github_admin_gh_bootstrap.sh convert 'FULL_REDIRECT_URL_WITH_CODE'</pre>
</body></html>
HTML
  echo "$form"
}

create_jwt() {
  app_id="$1"
  pem_file="$2"
  node - "$app_id" "$pem_file" <<'NODE'
const {createSign} = require('node:crypto');
const fs = require('node:fs');
const appId = process.argv[2];
const pem = fs.readFileSync(process.argv[3], 'utf8');
const now = Math.floor(Date.now() / 1000);
const enc = (v) => Buffer.from(JSON.stringify(v)).toString('base64url');
const input = `${enc({alg:'RS256',typ:'JWT'})}.${enc({iat:now-60,exp:now+540,iss:String(appId)})}`;
const signer = createSign('RSA-SHA256');
signer.update(input);
signer.end();
process.stdout.write(`${input}.${signer.sign(pem, 'base64url')}`);
NODE
}

case "$MODE" in
  status)
    gh auth status
    gcloud config get-value project 2>/dev/null || true
    ;;
  save-bootstrap)
    token="$(gh auth token)"
    set_secret GITHUB_BOOTSTRAP_TOKEN "$token"
    ;;
  manifest)
    form="$(write_manifest_form)"
    echo "Manifest form written: $form"
    echo "Open it in a browser, submit it, approve the GitHub App, then run:"
    echo "sh tools/github_admin_gh_bootstrap.sh convert CODE_FROM_REDIRECT_URL"
    ;;
  convert)
    code_arg="${2:-}"
    if [ -z "$code_arg" ]; then echo "Usage: sh tools/github_admin_gh_bootstrap.sh convert CODE_OR_FULL_REDIRECT_URL" >&2; exit 2; fi
    code="$(manifest_code_from_arg "$code_arg")"
    make_work_dir
    gh api --method POST "/app-manifests/$code/conversions" > "$WORK_DIR/conversion.json"
    chmod 600 "$WORK_DIR/conversion.json"
    app_id="$(node -e 'const fs=require("fs"); const j=JSON.parse(fs.readFileSync(process.argv[1],"utf8")); process.stdout.write(String(j.id||""));' "$WORK_DIR/conversion.json")"
    node -e 'const fs=require("fs"); const j=JSON.parse(fs.readFileSync(process.argv[1],"utf8")); if(!j.pem) process.exit(2); process.stdout.write(String(j.pem));' "$WORK_DIR/conversion.json" > "$WORK_DIR/app.pem"
    chmod 600 "$WORK_DIR/app.pem"
    html_url="$(node -e 'const fs=require("fs"); const j=JSON.parse(fs.readFileSync(process.argv[1],"utf8")); process.stdout.write(String(j.html_url||""));' "$WORK_DIR/conversion.json")"
    if [ -z "$app_id" ] || [ ! -s "$WORK_DIR/app.pem" ]; then echo "GitHub manifest conversion did not return app id and pem." >&2; exit 1; fi
    validate_private_key "$WORK_DIR/app.pem"
    set_secret GITHUB_APP_ID "$app_id"
    set_secret_from_file GITHUB_APP_PRIVATE_KEY "$WORK_DIR/app.pem"
    echo "GitHub App created: $html_url"
    echo "Install it for $OWNER, then run: sh tools/github_admin_gh_bootstrap.sh installation"
    ;;
  ingest-key)
    pem_file="${2:-}"
    if [ -z "$pem_file" ]; then echo "Usage: sh tools/github_admin_gh_bootstrap.sh ingest-key PRIVATE_KEY_PEM" >&2; exit 2; fi
    load_private_key "$pem_file"
    set_secret_from_file GITHUB_APP_PRIVATE_KEY "$WORK_DIR/app.pem"
    echo "Private key ingested without persisting a repository copy."
    ;;
  installations)
    load_private_key "${2:-}"
    app_id="$(gcloud secrets versions access latest --secret=GITHUB_APP_ID --project "$PROJECT")"
    jwt="$(create_jwt "$app_id" "$WORK_DIR/app.pem")"
    gh api -H "Authorization: Bearer $jwt" -H "Accept: application/vnd.github+json" /app > "$WORK_DIR/app.json"
    gh api -H "Authorization: Bearer $jwt" -H "Accept: application/vnd.github+json" /app/installations > "$WORK_DIR/installations.json"
    node -e 'const fs=require("fs"); const app=JSON.parse(fs.readFileSync(process.argv[1],"utf8")); const rows=JSON.parse(fs.readFileSync(process.argv[2],"utf8")); process.stdout.write(JSON.stringify({app:{name:app.name||"",slug:app.slug||"",installUrl:app.slug?`https://github.com/apps/${app.slug}/installations/new`:""},installations:(Array.isArray(rows)?rows:[]).map((x)=>({id:String(x.id||""),account:x.account&&x.account.login||"",targetType:x.target_type||"",repositorySelection:x.repository_selection||""}))},null,2));' "$WORK_DIR/app.json" "$WORK_DIR/installations.json"
    ;;
  installation)
    load_private_key "${2:-}"
    app_id="$(gcloud secrets versions access latest --secret=GITHUB_APP_ID --project "$PROJECT")"
    jwt="$(create_jwt "$app_id" "$WORK_DIR/app.pem")"
    gh api -H "Authorization: Bearer $jwt" -H "Accept: application/vnd.github+json" /app/installations > "$WORK_DIR/installations.json"
    installation_id="$(node -e 'const fs=require("fs"); const owner=process.argv[2]; const j=JSON.parse(fs.readFileSync(process.argv[1],"utf8")); const hit=(Array.isArray(j)?j:[]).find(x=>x.account&&x.account.login===owner); process.stdout.write(hit?String(hit.id):"");' "$WORK_DIR/installations.json" "$OWNER")"
    if [ -z "$installation_id" ]; then echo "No installation found for $OWNER. Install the app first, then rerun this command." >&2; exit 1; fi
    set_secret GITHUB_APP_INSTALLATION_ID "$installation_id"
    ;;
  *)
    echo "Usage: sh tools/github_admin_gh_bootstrap.sh status|save-bootstrap|manifest|convert CODE|ingest-key PRIVATE_KEY_PEM|installations [pem_file]|installation [pem_file]" >&2
    exit 2
    ;;
esac
