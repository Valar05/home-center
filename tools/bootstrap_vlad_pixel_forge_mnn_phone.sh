#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
STATE="${HC_PIXEL_FORGE_STATE:-$HOME/.local/state/home-center/pixel-forge}"
MNN_ROOT="${HC_MNN_ROOT:-$HOME/workspace/MNN}"
RECEIPT="$STATE/mnn-bootstrap.json"
mkdir -p "$STATE" "$(dirname "$MNN_ROOT")"

python3 "$ROOT/tools/vlad_pixel_forge_probe.py" > "$STATE/probe.stdout.json"

record() {
  local ok="$1" state="$2" detail="$3"
  python3 - "$RECEIPT" "$ok" "$state" "$detail" "$MNN_ROOT" <<'PY'
import json,sys,time
path,ok,state,detail,mnn=sys.argv[1:]
obj={
  'schema':'vlad.pixel-forge.mnn-bootstrap.v1',
  'ok':ok=='1',
  'state':state,
  'detail':detail,
  'mnnRoot':mnn,
  'device':'primary-phone',
  'ciUsed':False,
  'godotPolicy':'forge-only-not-delivery-runtime',
  'recordedAtEpoch':int(time.time()),
}
open(path,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n')
print(json.dumps(obj,indent=2,sort_keys=True))
PY
}

for tool in git cmake ninja clang python3; do
  command -v "$tool" >/dev/null 2>&1 || { record 0 BLOCKED "missing phone tool: $tool"; exit 10; }
done

FREE_KB="$(df -Pk "$HOME" | awk 'NR==2 {print $4}')"
MIN_FREE_KB="${HC_PIXEL_FORGE_MIN_FREE_KB:-8388608}"
if [ "$FREE_KB" -lt "$MIN_FREE_KB" ]; then
  record 0 BLOCKED "insufficient free storage: ${FREE_KB}KiB; require ${MIN_FREE_KB}KiB before MNN source/build"
  exit 11
fi

NDK="${ANDROID_NDK:-${ANDROID_NDK_HOME:-}}"
if [ -z "$NDK" ]; then
  for p in "$HOME/android-sdk/ndk"/* "$PREFIX/share/android-ndk" "$HOME/Android/Sdk/ndk"/*; do
    [ -d "$p" ] || continue
    NDK="$p"
  done
fi
if [ -z "$NDK" ] || [ ! -d "$NDK" ]; then
  record 0 BLOCKED 'Android NDK not found on phone; bootstrap intentionally refuses a blind multi-GB SDK install.'
  exit 12
fi
export ANDROID_NDK="$NDK"

if [ ! -d "$MNN_ROOT/.git" ]; then
  git clone --depth 1 https://github.com/alibaba/MNN.git "$MNN_ROOT"
else
  git -C "$MNN_ROOT" fetch --depth 1 origin master
  git -C "$MNN_ROOT" reset --hard origin/master
fi

BUILD="$MNN_ROOT/project/android/build_vlad_pixel_forge"
mkdir -p "$BUILD"
cd "$BUILD"

cmake ../../.. \
  -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE="$ANDROID_NDK/build/cmake/android.toolchain.cmake" \
  -DANDROID_ABI=arm64-v8a \
  -DANDROID_PLATFORM=android-26 \
  -DMNN_LOW_MEMORY=ON \
  -DMNN_ARM82=ON \
  -DMNN_OPENCL=ON \
  -DMNN_BUILD_DIFFUSION=ON \
  -DMNN_BUILD_CONVERTER=OFF \
  -DMNN_BUILD_TOOLS=OFF \
  -DMNN_BUILD_TEST=OFF \
  -DMNN_SEP_BUILD=OFF \
  -DCMAKE_BUILD_TYPE=Release

ninja -j"${HC_PIXEL_FORGE_BUILD_JOBS:-2}"

LIBS="$(find "$BUILD" -type f \( -name '*.so' -o -name '*.a' \) -print | head -100)"
[ -n "$LIBS" ] || { record 0 BLOCKED 'MNN build finished without native libraries.'; exit 13; }
printf '%s\n' "$LIBS" > "$STATE/mnn-libraries.txt"
record 1 BUILT "MNN diffusion runtime built locally on phone with NDK=$NDK"
