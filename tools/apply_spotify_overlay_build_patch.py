#!/usr/bin/env python3
"""Patch the Termux overlay forge to derive and receipt its Gradle version."""
from __future__ import annotations

import argparse
from pathlib import Path


def read_lf(path: Path) -> str:
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")


def write_lf(path: Path, text: str) -> None:
    path.write_bytes(text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8"))


def replace_once(path: Path, old: str, new: str) -> None:
    text = read_lf(path)
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one anchor, found {count}: {old[:120]!r}")
    write_lf(path, text.replace(old, new, 1))


def apply(root: Path) -> None:
    script = root / "tools/build_operator_overlay_termux.sh"
    version_block = """GRADLE_CONFIG="$APP/build.gradle"
BUILD_RECEIPT="$OUTDIR/operator-overlay-build-receipt.json"
mapfile -t OVERLAY_VERSION < <(python - "$GRADLE_CONFIG" <<'PY'
import re,sys
text=open(sys.argv[1],encoding='utf-8').read()
code=re.search(r'\\bversionCode\\s+(\\d+)',text)
name=re.search(r"\\bversionName\\s+'([^']+)'",text)
if not code or not name:
    raise SystemExit('operator overlay Gradle version is missing')
print(code.group(1))
print(name.group(1))
PY
)
VERSION_CODE="${HC_OVERLAY_VERSION_CODE:-${OVERLAY_VERSION[0]}}"
VERSION_NAME="${HC_OVERLAY_VERSION_NAME:-${OVERLAY_VERSION[1]}}"
[[ "$VERSION_CODE" =~ ^[0-9]+$ ]] || { echo "BLOCKED: invalid overlay versionCode: $VERSION_CODE" >&2; exit 38; }
[ -n "$VERSION_NAME" ] || { echo 'BLOCKED: empty overlay versionName.' >&2; exit 39; }

"""
    replace_once(
        script,
        '[ -n "$RISH_BIN" ] || RISH_BIN="$HOME/bin/rish"\n\n',
        '[ -n "$RISH_BIN" ] || RISH_BIN="$HOME/bin/rish"\n\n' + version_block,
    )
    replace_once(
        script,
        'aapt2 link -o "$WORK/base-unsigned.apk" -I "$FRAMEWORK_RES" --manifest "$BUILD_MANIFEST" --min-sdk-version 26 --target-sdk-version 35 --version-code 3 --version-name 1.2.0\n',
        'aapt2 link -o "$WORK/base-unsigned.apk" -I "$FRAMEWORK_RES" --manifest "$BUILD_MANIFEST" --min-sdk-version 26 --target-sdk-version 35 --version-code "$VERSION_CODE" --version-name "$VERSION_NAME"\n',
    )
    receipt_block = """apksigner verify --verbose "$APK" >/dev/null
SIGNER_INFO="$(apksigner verify --print-certs "$APK")"
CERT_SHA="$(printf '%s\\n' "$SIGNER_INFO" | sed -nE 's/^.*certificate SHA-256 digest:[[:space:]]*//p' | head -1)"
[ -n "$CERT_SHA" ] || { echo 'BLOCKED: APK signer certificate digest missing.' >&2; exit 40; }
APK_SHA="$(sha256sum "$APK" | awk '{print $1}')"
APK_BYTES="$(stat -c '%s' "$APK")"
SOURCE_COMMIT="$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || true)"
python - "$BUILD_RECEIPT" "$APK" "$APK_SHA" "$APK_BYTES" "$CERT_SHA" "$VERSION_CODE" "$VERSION_NAME" "$SOURCE_COMMIT" <<'PY'
import json,os,sys,time
path,apk,sha,byte_count,cert,version_code,version_name,source=sys.argv[1:]
obj={
  'schema':'home-center.operator-overlay-termux-build.v1',
  'ok':True,
  'artifact':apk,
  'apkSha256':sha,
  'byteCount':int(byte_count),
  'signingCertificateSha256':cert,
  'versionCode':int(version_code),
  'versionName':version_name,
  'sourceCommit':source,
  'builtAtEpoch':int(time.time()),
}
os.makedirs(os.path.dirname(path),exist_ok=True)
open(path,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\\n')
print(json.dumps(obj,sort_keys=True))
PY

sha256sum "$APK"
echo "TERMUX OVERLAY APK BUILT apk=$APK versionCode=$VERSION_CODE versionName=$VERSION_NAME signer=$CERT_SHA androidJar=$ANDROID_JAR frameworkRes=$FRAMEWORK_RES receipt=$BUILD_RECEIPT"
"""
    replace_once(
        script,
        'apksigner verify --verbose "$APK" >/dev/null\n\nsha256sum "$APK"\necho "TERMUX OVERLAY APK BUILT apk=$APK androidJar=$ANDROID_JAR frameworkRes=$FRAMEWORK_RES"\n',
        receipt_block,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    apply(Path(args.root).resolve())
    print("apply_spotify_overlay_build_patch: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
