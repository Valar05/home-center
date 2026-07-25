#!/data/data/com.termux/files/usr/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"
PROJECT="${FIREBASE_PROJECT:-home-center-dclar}"
OUT_JSON="generated/doctor/home_center_doctor_latest.json"
OUT_MD="generated/doctor/home_center_doctor_latest.md"
mkdir -p "$(dirname -- "$OUT_JSON")"

yesno() { if "$@" >/dev/null 2>&1; then printf true; else printf false; fi; }
cmd_path() { if command -v "$1" >/dev/null 2>&1; then command -v "$1"; else printf ''; fi; }
secret_state() {
  name="$1"
  if ! command -v gcloud >/dev/null 2>&1; then printf unknown; return; fi
  if gcloud secrets describe "$name" --project "$PROJECT" >/dev/null 2>&1; then printf present; else printf missing; fi
}
http_status() {
  url="$1"
  if command -v curl >/dev/null 2>&1; then curl -sS -o /dev/null -w '%{http_code}' "$url" || printf error; else printf unknown; fi
}

gh_logged_in=false
if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then gh_logged_in=true; fi
active_gcloud_account=""
if command -v gcloud >/dev/null 2>&1; then active_gcloud_account="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' 2>/dev/null | head -n 1 || true)"; fi
branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
head="$(git rev-parse HEAD 2>/dev/null || true)"
dirty_count="$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
mcp_status="$(http_status "https://us-central1-${PROJECT}.cloudfunctions.net/homeCenterMcp/auth-challenge")"

export DOCTOR_PROJECT="$PROJECT"
export DOCTOR_OUT_JSON="$OUT_JSON"
export DOCTOR_OUT_MD="$OUT_MD"
export DOCTOR_GH_PATH="$(cmd_path gh)"
export DOCTOR_GCLOUD_PATH="$(cmd_path gcloud)"
export DOCTOR_FIREBASE_PATH="$(cmd_path firebase)"
export DOCTOR_NODE_PATH="$(cmd_path node)"
export DOCTOR_GRADLE_PATH="$(cmd_path gradle)"
export DOCTOR_GH_LOGGED_IN="$gh_logged_in"
export DOCTOR_GCLOUD_ACCOUNT="$active_gcloud_account"
export DOCTOR_BRANCH="$branch"
export DOCTOR_HEAD="$head"
export DOCTOR_DIRTY_COUNT="$dirty_count"
export DOCTOR_MCP_STATUS="$mcp_status"
export DOCTOR_SECRET_GITHUB_TOKEN="$(secret_state GITHUB_TOKEN)"
export DOCTOR_SECRET_GITHUB_BOOTSTRAP_TOKEN="$(secret_state GITHUB_BOOTSTRAP_TOKEN)"
export DOCTOR_SECRET_GITHUB_APP_ID="$(secret_state GITHUB_APP_ID)"
export DOCTOR_SECRET_GITHUB_APP_INSTALLATION_ID="$(secret_state GITHUB_APP_INSTALLATION_ID)"
export DOCTOR_SECRET_GITHUB_APP_PRIVATE_KEY="$(secret_state GITHUB_APP_PRIVATE_KEY)"
export DOCTOR_SECRET_GOOGLE_OAUTH_CLIENT_ID="$(secret_state GOOGLE_OAUTH_CLIENT_ID)"
export DOCTOR_SECRET_GOOGLE_OAUTH_CLIENT_SECRET="$(secret_state GOOGLE_OAUTH_CLIENT_SECRET)"
export DOCTOR_SECRET_CARTESIA_API_KEY="$(secret_state CARTESIA_API_KEY)"
node - <<'NODE'
const fs = require('fs');
const env = process.env;
const data = {
  generatedAt: new Date().toISOString(),
  project: env.DOCTOR_PROJECT || '',
  commands: {
    gh: env.DOCTOR_GH_PATH || '',
    gcloud: env.DOCTOR_GCLOUD_PATH || '',
    firebase: env.DOCTOR_FIREBASE_PATH || '',
    node: env.DOCTOR_NODE_PATH || '',
    gradle: env.DOCTOR_GRADLE_PATH || '',
  },
  auth: {
    ghLoggedIn: env.DOCTOR_GH_LOGGED_IN === 'true',
    gcloudAccount: env.DOCTOR_GCLOUD_ACCOUNT || '',
  },
  git: {
    branch: env.DOCTOR_BRANCH || '',
    head: env.DOCTOR_HEAD || '',
    dirtyCount: Number(env.DOCTOR_DIRTY_COUNT || 0),
  },
  secrets: {
    GITHUB_TOKEN: env.DOCTOR_SECRET_GITHUB_TOKEN || 'unknown',
    GITHUB_BOOTSTRAP_TOKEN: env.DOCTOR_SECRET_GITHUB_BOOTSTRAP_TOKEN || 'unknown',
    GITHUB_APP_ID: env.DOCTOR_SECRET_GITHUB_APP_ID || 'unknown',
    GITHUB_APP_INSTALLATION_ID: env.DOCTOR_SECRET_GITHUB_APP_INSTALLATION_ID || 'unknown',
    GITHUB_APP_PRIVATE_KEY: env.DOCTOR_SECRET_GITHUB_APP_PRIVATE_KEY || 'unknown',
    GOOGLE_OAUTH_CLIENT_ID: env.DOCTOR_SECRET_GOOGLE_OAUTH_CLIENT_ID || 'unknown',
    GOOGLE_OAUTH_CLIENT_SECRET: env.DOCTOR_SECRET_GOOGLE_OAUTH_CLIENT_SECRET || 'unknown',
    CARTESIA_API_KEY: env.DOCTOR_SECRET_CARTESIA_API_KEY || 'unknown',
  },
  endpoints: {
    homeCenterMcpAuthChallengeHttpStatus: env.DOCTOR_MCP_STATUS || 'unknown',
  },
};
data.readiness = {
  githubAdminFullAuthority: [data.secrets.GITHUB_APP_ID, data.secrets.GITHUB_APP_INSTALLATION_ID, data.secrets.GITHUB_APP_PRIVATE_KEY].every((x) => x === 'present'),
  githubBootstrapOnly: data.secrets.GITHUB_BOOTSTRAP_TOKEN === 'present',
};
let status = 'ready';
const blockers = [];
if (!data.commands.gh) blockers.push('gh_missing');
if (!data.commands.gcloud) blockers.push('gcloud_missing');
if (data.secrets.GOOGLE_OAUTH_CLIENT_ID !== 'present') blockers.push('google_oauth_client_id_missing');
if (!data.readiness.githubAdminFullAuthority) status = 'degraded';
if (blockers.length) status = 'blocked';
data.status = status;
data.blockers = blockers;
const markdown = [
  '# Home Center Doctor',
  '',
  `status: ${status}`,
  `project: ${data.project}`,
  `gh_logged_in: ${data.auth.ghLoggedIn}`,
  `gcloud_account: ${data.auth.gcloudAccount}`,
  `git_branch: ${data.git.branch}`,
  `dirty_count: ${data.git.dirtyCount}`,
  `mcp_auth_challenge_http_status: ${data.endpoints.homeCenterMcpAuthChallengeHttpStatus}`,
  `github_admin_full_authority: ${data.readiness.githubAdminFullAuthority}`,
  `github_bootstrap_only: ${data.readiness.githubBootstrapOnly}`,
  `blockers: ${blockers.join(', ')}`,
  '',
].join('\n');
fs.writeFileSync(env.DOCTOR_OUT_JSON, JSON.stringify(data, null, 2));
fs.writeFileSync(env.DOCTOR_OUT_MD, markdown);
console.log(markdown);
NODE
case "$(node -e "process.stdout.write(require('./$OUT_JSON').status)")" in
  ready) exit 0 ;;
  degraded) exit 1 ;;
  *) exit 2 ;;
esac
