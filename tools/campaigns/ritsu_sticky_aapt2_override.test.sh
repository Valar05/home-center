#!/usr/bin/env bash
# Reproduce AGP's AAPT2 override path validation without an Android phone.
set -Eeuo pipefail
src="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
repo="$(cd "$src/../.." && pwd -P)"
phone="$src/ritsu_sticky_phone_native.sh"
bash -n "$phone"
grep -Fq 'aapt2Wrapper="$repair/aapt2"' "$phone" || {
  echo "AAPT2_OVERRIDE_FAIL=missing_exact_named_wrapper"; exit 2;
}
grep -Fq 'case "$native" in' "$phone" || {
  echo "AAPT2_OVERRIDE_FAIL=missing_early_validation"; exit 2;
}
grep -Fq 'aapt2-scoped' "$phone" || {
  echo "AAPT2_OVERRIDE_FAIL=missing_prior_run_resume"; exit 2;
}
echo 'AAPT2_PHONE_SOURCE_GUARDS=PASS'
if ! command -v gradle >/dev/null 2>&1; then
  echo 'AAPT2_AGP_PLUGIN_CHECK=SKIP_gradle_not_present'
  exit 0
fi
if [ -z "${ANDROID_HOME:-}" ] || [ ! -f "$ANDROID_HOME/platforms/android-35/android.jar" ]; then
  echo 'AAPT2_AGP_PLUGIN_CHECK=SKIP_SDK35_not_present'
  exit 0
fi
temp="$(mktemp -d)"
trap 'rm -rf "$temp"' EXIT
cat > "$temp/aapt2" <<'AAPT2_WRAPPER'
#!/usr/bin/env bash
set -e
exec "$ANDROID_HOME/build-tools/35.0.0/aapt2" "$@"
AAPT2_WRAPPER
chmod 700 "$temp/aapt2"
"$temp/aapt2" version > "$temp/native-version.log" 2>&1

cp "$temp/aapt2" "$temp/aapt2-scoped"
if gradle -p "$repo/android/ritsu-control" :app:help \
    -PritsuStickyInstall=true \
    "-Pandroid.aapt2FromMavenOverride=$temp/aapt2-scoped" \
    --no-daemon > "$temp/negative.log" 2>&1; then
  echo 'AAPT2_AGP_NEGATIVE=unexpectedly_accepted_invalid_name'
  exit 2
fi
grep -Fq 'Custom AAPT2 location does not point to an AAPT2 executable' \
  "$temp/negative.log" || {
    tail -n 24 "$temp/negative.log"
    echo 'AAPT2_AGP_NEGATIVE=failed_for_unexpected_reason'
    exit 2
  }
echo 'AAPT2_AGP_WRONG_BASENAME_REJECTED=PASS'
gradle -p "$repo/android/ritsu-control" :app:help \
  -PritsuStickyInstall=true \
  "-Pandroid.aapt2FromMavenOverride=$temp/aapt2" \
  --no-daemon > "$temp/positive.log" 2>&1 || {
    tail -n 35 "$temp/positive.log"
    echo 'AAPT2_AGP_POSITIVE=failed'
    exit 2
  }
echo 'AAPT2_AGP_CORRECT_BASENAME_ACCEPTED=PASS'
