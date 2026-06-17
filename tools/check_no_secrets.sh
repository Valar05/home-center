#!/data/data/com.termux/files/usr/bin/sh
set -eu

fail=0

tracked_secret_files="$(git ls-files 2>/dev/null | rg '(^|/)(google-services\.json|.*service-account.*\.json|.*secret.*\.json|.*secrets.*\.properties|.*\.(jks|keystore))$' || true)"
if [ -n "$tracked_secret_files" ]; then
  echo "$tracked_secret_files" >&2
  echo "Secret/config file is tracked. Remove it from git before committing." >&2
  fail=1
fi

if rg -n --hidden --glob '!app/build/**' --glob '!build/**' --glob '!.gradle/**' --glob '!.git/**' --glob '!app/google-services.json' --glob '!README.md' --glob '!docs/**' --glob '!tools/check_no_secrets.sh' \
  'Authorization: Bearer [A-Za-z0-9._~+/=-]{10,}|-----BEGIN (RSA |EC |OPENSSH |)PRIVATE KEY-----|AIza[0-9A-Za-z_-]{20,}' .; then
  echo "Potential secret found. Remove it before committing." >&2
  fail=1
fi

exit "$fail"
