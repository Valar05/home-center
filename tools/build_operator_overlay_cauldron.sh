#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
OUT="${HC_CAULDRON_OVERLAY_APK:-$ROOT/android/operator-overlay/app/build/outputs/apk/debug/app-debug.apk}"
ENDPOINT="${FORTRESS_CAULDRON_SSH:-dclar@192.168.40.213}"
STATE="$HOME/.local/state/home-center"
mkdir -p "$STATE" "$(dirname "$OUT")"

cd "$ROOT"
python tools/ssh_axis.py check --target cauldron --json > "$STATE/cauldron-ssh-axis.json" || {
  cat "$STATE/cauldron-ssh-axis.json" >&2
  echo 'BLOCKED: THECAULDRON SSH Axis is not callable; refusing to pretend the desktop forge exists.' >&2
  exit 41
}

HOSTPORT="$ENDPOINT"
PORT=22
if [[ "$HOSTPORT" =~ ^(.+):([0-9]+)$ ]]; then
  HOSTPORT="${BASH_REMATCH[1]}"
  PORT="${BASH_REMATCH[2]}"
fi

SOURCE_SHA="$(git rev-parse HEAD)"
REMOTE_APK='C:\\Users\\Public\\home-center-adam-overlay.apk'
REMOTE_PS="$STATE/build-adam-overlay-cauldron.ps1"
cat > "$REMOTE_PS" <<'PS'
$ErrorActionPreference = 'Stop'
$repoCandidates = @(
  (Join-Path $env:USERPROFILE 'Documents\GodotProjects\home-center'),
  (Join-Path $env:USERPROFILE 'Documents\GitHub\home-center'),
  (Join-Path $env:USERPROFILE 'source\repos\home-center'),
  (Join-Path $env:USERPROFILE 'home-center')
)
$repo = $null
foreach ($candidate in $repoCandidates) {
  if (Test-Path (Join-Path $candidate '.git')) { $repo = $candidate; break }
}
if (-not $repo) {
  $repo = Join-Path $env:TEMP 'home-center-adam-forge'
  if (Test-Path $repo) { Remove-Item -Recurse -Force $repo }
  git clone --depth 1 --branch main https://github.com/Valar05/home-center.git $repo
}
Set-Location $repo
git fetch origin main
git checkout main
git reset --hard origin/main

$sdkCandidates = @($env:ANDROID_SDK_ROOT, $env:ANDROID_HOME, (Join-Path $env:LOCALAPPDATA 'Android\Sdk')) | Where-Object { $_ }
$sdk = $sdkCandidates | Where-Object { Test-Path (Join-Path $_ 'platforms\android-35\android.jar') } | Select-Object -First 1
if (-not $sdk) {
  $sdkBase = $sdkCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
  if ($sdkBase) {
    $sdkmanager = Get-ChildItem -Path (Join-Path $sdkBase 'cmdline-tools') -Recurse -Filter sdkmanager.bat -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($sdkmanager) {
      & $sdkmanager.FullName 'platforms;android-35' 'build-tools;35.0.0'
      if ($LASTEXITCODE -ne 0) { throw 'sdkmanager failed to install API 35 platform/build-tools' }
      $sdk = $sdkBase
    }
  }
}
if (-not $sdk -or -not (Test-Path (Join-Path $sdk 'platforms\android-35\android.jar'))) {
  throw 'Android SDK API 35 is unavailable on THECAULDRON'
}
$env:ANDROID_SDK_ROOT = $sdk
$env:ANDROID_HOME = $sdk

if (-not (Get-Command java -ErrorAction SilentlyContinue)) { throw 'Java is unavailable on THECAULDRON' }

$gradle = Get-Command gradle -ErrorAction SilentlyContinue
if ($gradle) {
  $gradleExe = $gradle.Source
} else {
  $gradleHome = Join-Path $env:TEMP 'gradle-8.9'
  $gradleExe = Join-Path $gradleHome 'bin\gradle.bat'
  if (-not (Test-Path $gradleExe)) {
    $zip = Join-Path $env:TEMP 'gradle-8.9-bin.zip'
    Invoke-WebRequest -UseBasicParsing 'https://services.gradle.org/distributions/gradle-8.9-bin.zip' -OutFile $zip
    Expand-Archive -Path $zip -DestinationPath $env:TEMP -Force
  }
}

Set-Location (Join-Path $repo 'android\operator-overlay')
& $gradleExe ':app:assembleDebug' '--no-daemon'
if ($LASTEXITCODE -ne 0) { throw "Gradle overlay build failed with exit code $LASTEXITCODE" }
$apk = Join-Path $PWD 'app\build\outputs\apk\debug\app-debug.apk'
if (-not (Test-Path $apk)) { throw "Expected APK missing: $apk" }
Copy-Item -Force $apk 'C:\Users\Public\home-center-adam-overlay.apk'
$sha = (Get-FileHash -Algorithm SHA256 'C:\Users\Public\home-center-adam-overlay.apk').Hash.ToLowerInvariant()
Write-Output "CAULDRON_OVERLAY_APK_OK sha256=$sha path=C:\Users\Public\home-center-adam-overlay.apk"
PS

echo '[forge] Sending bounded build script to THECAULDRON'
scp -P "$PORT" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$REMOTE_PS" "$HOSTPORT:C:/Users/Public/build-adam-overlay-cauldron.ps1"

echo '[forge] Building current main on THECAULDRON'
ssh -p "$PORT" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$HOSTPORT" \
  "powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\\Users\\Public\\build-adam-overlay-cauldron.ps1" \
  | tee "$STATE/cauldron-overlay-build.txt"
grep -q 'CAULDRON_OVERLAY_APK_OK' "$STATE/cauldron-overlay-build.txt" || {
  echo 'BLOCKED: THECAULDRON build did not emit a successful APK receipt.' >&2
  exit 42
}

echo '[forge] Returning APK from THECAULDRON to phone'
scp -P "$PORT" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$HOSTPORT:C:/Users/Public/home-center-adam-overlay.apk" "$OUT.part"
mv "$OUT.part" "$OUT"
[ -s "$OUT" ] || { echo 'BLOCKED: returned THECAULDRON APK is empty.' >&2; exit 43; }
sha256sum "$OUT" | tee "$STATE/cauldron-overlay-apk.sha256"
echo "CAULDRON OVERLAY APK RECEIVED source=$SOURCE_SHA apk=$OUT"
