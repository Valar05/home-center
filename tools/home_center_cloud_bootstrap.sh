#!/data/data/com.termux/files/usr/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"
PROJECT="${FIREBASE_PROJECT:-home-center-dclar}"
REPO="${HOME_CENTER_GITHUB_REPO:-Valar05/home-center}"
MODE="${1:-run}"
REPORT_DIR="generated/bootstrap"
REPORT="$REPORT_DIR/home_center_cloud_bootstrap_latest.md"
mkdir -p "$REPORT_DIR"

log() { printf '%s\n' "$*"; }
section() { printf '\n== %s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }
secret_present() {
  name="$1"
  if ! have gcloud; then return 2; fi
  gcloud secrets describe "$name" --project "$PROJECT" >/dev/null 2>&1
}

github_secret_present() {
  name="$1"
  if ! have gh; then return 2; fi
  gh secret list --repo "$REPO" 2>/dev/null | awk '{print $1}' | grep -Fx "$name" >/dev/null 2>&1
}

run_optional() {
  label="$1"
  shift
  section "$label"
  set +e
  "$@"
  code=$?
  set -e
  if [ "$code" -eq 0 ]; then
    log "ok: $label"
    return 0
  fi
  log "blocked: $label exited $code"
  return "$code"
}

write_summary() {
  status="$1"
  missing_file="$REPORT_DIR/missing_steps.tmp"
  : > "$missing_file"
  for name in GITHUB_APP_ID GITHUB_APP_INSTALLATION_ID GITHUB_APP_PRIVATE_KEY GCP_WORKLOAD_IDENTITY_PROVIDER GCP_DEPLOY_SERVICE_ACCOUNT; do
    case "$name" in
      GCP_*)
        if ! github_secret_present "$name"; then printf '%s\n' "- GitHub Actions secret: $name" >> "$missing_file"; fi
        ;;
      *)
        if ! secret_present "$name"; then printf '%s\n' "- Secret Manager: $name" >> "$missing_file"; fi
        ;;
    esac
  done
  {
    printf '%s\n\n' '# Home Center Cloud Bootstrap'
    printf 'status: %s\n' "$status"
    printf 'project: %s\n' "$PROJECT"
    printf 'generated_at: %s\n\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf '%s\n' '## Remaining external steps'
    if [ -s "$missing_file" ]; then cat "$missing_file"; else printf '%s\n' '- none'; fi
    printf '\n%s\n\n' '## Useful commands'
    printf '%s\n' '- sh tools/home_center_cloud_bootstrap.sh manifest'
    printf '%s\n' '- sh tools/github_admin_gh_bootstrap.sh convert CODE_FROM_GITHUB_REDIRECT'
    printf '%s\n' '- sh tools/github_admin_gh_bootstrap.sh installation generated/github_admin/github-app.private-key.pem'
    printf '%s\n' '- sh tools/home_center_cloud_bootstrap.sh run'
  } > "$REPORT"
  rm -f "$missing_file"
  log "summary: $REPORT"
}
usage() {
  cat <<'EOF'
Usage: sh tools/home_center_cloud_bootstrap.sh [run|manifest|save-bootstrap|secrets-from-env|doctor|validate|status|summary]

run              Do every safe local step: status, optional bootstrap save, manifest, env-secret install, doctor, validation.
manifest         Write the GitHub App manifest HTML form.
save-bootstrap  Store the current gh login token as GITHUB_BOOTSTRAP_TOKEN.
secrets-from-env Store GITHUB_APP_ID, GITHUB_APP_INSTALLATION_ID, and GITHUB_APP_PRIVATE_KEY from environment variables.
doctor           Run the redacted Home Center doctor.
validate         Run the compact validation wrapper.
status           Print current command/auth/secret readiness without mutation.
summary          Write the latest bootstrap summary without changing secrets.
EOF
}

status_report() {
  section "Local tool status"
  for cmd in gh gcloud firebase node npm git; do
    if have "$cmd"; then log "$cmd: $(command -v "$cmd")"; else log "$cmd: missing"; fi
  done
  if have gh; then gh auth status || true; fi
  if have gcloud; then gcloud auth list --filter=status:ACTIVE --format='value(account)' 2>/dev/null | sed 's/^/gcloud_account: /' || true; fi

  section "Secret Manager status"
  for name in GITHUB_TOKEN GITHUB_BOOTSTRAP_TOKEN GITHUB_APP_ID GITHUB_APP_INSTALLATION_ID GITHUB_APP_PRIVATE_KEY GOOGLE_OAUTH_CLIENT_ID GOOGLE_OAUTH_CLIENT_SECRET CARTESIA_API_KEY; do
    if secret_present "$name"; then log "$name: present"; else log "$name: missing_or_unknown"; fi
  done
  section "GitHub Actions secret status"
  for name in GCP_WORKLOAD_IDENTITY_PROVIDER GCP_DEPLOY_SERVICE_ACCOUNT; do
    if github_secret_present "$name"; then log "$name: present"; else log "$name: missing_or_unknown"; fi
  done
}

save_bootstrap_if_possible() {
  if ! have gh; then log "skip: gh missing"; return 1; fi
  if ! gh auth status >/dev/null 2>&1; then log "skip: gh is not logged in"; return 1; fi
  sh tools/github_admin_gh_bootstrap.sh save-bootstrap
}

install_env_secrets_if_possible() {
  if [ -n "${GITHUB_APP_ID:-}" ] && [ -n "${GITHUB_APP_INSTALLATION_ID:-}" ] && [ -n "${GITHUB_APP_PRIVATE_KEY:-}" ]; then
    sh tools/setup_github_admin_secrets.sh "$PROJECT"
    return 0
  fi
  log "skip: set GITHUB_APP_ID, GITHUB_APP_INSTALLATION_ID, and GITHUB_APP_PRIVATE_KEY to install full GitHub App authority"
  return 1
}

case "$MODE" in
  run)
    status_report
    run_optional "save bootstrap GitHub token" save_bootstrap_if_possible || true
    run_optional "write GitHub App manifest form" sh tools/github_admin_gh_bootstrap.sh manifest || true
    run_optional "install GitHub App secrets from environment" install_env_secrets_if_possible || true
    run_optional "doctor" sh tools/home_center_doctor.sh || true
    run_optional "validation" sh tools/home_center_ci_validate.sh || true
    if secret_present GITHUB_APP_ID && secret_present GITHUB_APP_INSTALLATION_ID && secret_present GITHUB_APP_PRIVATE_KEY; then
      write_summary ready
      exit 0
    fi
    write_summary blocked_external_github_app_secrets
    exit 1
    ;;
  manifest)
    sh tools/github_admin_gh_bootstrap.sh manifest
    ;;
  save-bootstrap)
    save_bootstrap_if_possible
    ;;
  secrets-from-env)
    install_env_secrets_if_possible
    ;;
  doctor)
    sh tools/home_center_doctor.sh
    ;;
  validate)
    sh tools/home_center_ci_validate.sh
    ;;
  status)
    status_report
    ;;
  summary)
    if secret_present GITHUB_APP_ID && secret_present GITHUB_APP_INSTALLATION_ID && secret_present GITHUB_APP_PRIVATE_KEY; then
      write_summary ready
    else
      write_summary blocked_external_github_app_secrets
      exit 1
    fi
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
