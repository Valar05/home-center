#!/data/data/com.termux/files/usr/bin/sh
set -eu

PROJECT="${FIREBASE_PROJECT:-home-center-dclar}"
OWNER="${HOME_CENTER_GITHUB_ADMIN_OWNER:-Valar05}"
APP_NAME="${HOME_CENTER_GITHUB_APP_NAME:-Home Center GitHub Admin}"
REDIRECT_URL="${HOME_CENTER_GITHUB_APP_REDIRECT_URL:-https://github.com/Valar05/home-center}"
MODE="${1:-status}"

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
  mkdir -p generated/github_admin
  manifest="$(make_manifest)"
  form="generated/github_admin/github_app_manifest_form.html"
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
    tmp="$(mktemp)"
    gh api --method POST "/app-manifests/$code/conversions" > "$tmp"
    app_id="$(node -e 'const fs=require("fs"); const j=JSON.parse(fs.readFileSync(process.argv[1],"utf8")); process.stdout.write(String(j.id||""));' "$tmp")"
    pem="$(node -e 'const fs=require("fs"); const j=JSON.parse(fs.readFileSync(process.argv[1],"utf8")); process.stdout.write(String(j.pem||""));' "$tmp")"
    html_url="$(node -e 'const fs=require("fs"); const j=JSON.parse(fs.readFileSync(process.argv[1],"utf8")); process.stdout.write(String(j.html_url||""));' "$tmp")"
    if [ -z "$app_id" ] || [ -z "$pem" ]; then echo "GitHub manifest conversion did not return app id and pem." >&2; exit 1; fi
    set_secret GITHUB_APP_ID "$app_id"
    set_secret GITHUB_APP_PRIVATE_KEY "$pem"
    mkdir -p generated/github_admin
    printf '%s' "$pem" > generated/github_admin/github-app.private-key.pem
    chmod 600 generated/github_admin/github-app.private-key.pem
    echo "GitHub App created: $html_url"
    echo "Install it for $OWNER, then run: sh tools/github_admin_gh_bootstrap.sh installation generated/github_admin/github-app.private-key.pem"
    ;;
  installation)
    pem_file="${2:-generated/github_admin/github-app.private-key.pem}"
    if [ ! -f "$pem_file" ]; then
      echo "Private key file not found: $pem_file" >&2
      echo "Use: sh tools/github_admin_gh_bootstrap.sh installation generated/github_admin/github-app.private-key.pem" >&2
      exit 2
    fi
    app_id="$(gcloud secrets versions access latest --secret=GITHUB_APP_ID --project "$PROJECT")"
    jwt="$(create_jwt "$app_id" "$pem_file")"
    tmp="$(mktemp)"
    gh api -H "Authorization: Bearer $jwt" -H "Accept: application/vnd.github+json" /app/installations > "$tmp"
    installation_id="$(node -e 'const fs=require("fs"); const owner=process.argv[2]; const j=JSON.parse(fs.readFileSync(process.argv[1],"utf8")); const hit=(Array.isArray(j)?j:[]).find(x=>x.account&&x.account.login===owner); process.stdout.write(hit?String(hit.id):"");' "$tmp" "$OWNER")"
    if [ -z "$installation_id" ]; then echo "No installation found for $OWNER. Install the app first, then rerun this command." >&2; exit 1; fi
    set_secret GITHUB_APP_INSTALLATION_ID "$installation_id"
    ;;
  *)
    echo "Usage: sh tools/github_admin_gh_bootstrap.sh status|save-bootstrap|manifest|convert CODE|installation [pem_file]" >&2
    exit 2
    ;;
esac
