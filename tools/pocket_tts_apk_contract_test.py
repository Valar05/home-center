#!/data/data/com.termux/files/usr/bin/python3
from pathlib import Path
import sys
import zipfile

apk = Path(sys.argv[1] if len(sys.argv) > 1 else 'app/build/outputs/apk/debug/app-debug.apk')
if not apk.is_file():
    raise SystemExit(f'APK not found: {apk}')
required = {
    'lib/arm64-v8a/liblitert_jni.so',
    'lib/arm64-v8a/libLiteRt.so',
    'lib/arm64-v8a/libLiteRtClGlAccelerator.so',
}
with zipfile.ZipFile(apk) as archive:
    names = set(archive.namelist())
missing = sorted(required - names)
if missing:
    raise SystemExit('Pocket TTS APK native contract failed; missing: ' + ', '.join(missing))
print(f'Pocket TTS APK native contract: OK apk={apk} arm64_libraries={len(required)}')
