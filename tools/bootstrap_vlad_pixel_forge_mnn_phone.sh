#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
STATE="${HC_PIXEL_FORGE_STATE:-$HOME/.local/state/home-center/pixel-forge}"
MNN_ROOT="${HC_MNN_ROOT:-$HOME/workspace/MNN}"
MNN_REF="${HC_MNN_REF:-3.4.1}"
RECEIPT="$STATE/mnn-bootstrap.json"
mkdir -p "$STATE" "$(dirname "$MNN_ROOT")"
python3 "$ROOT/tools/vlad_pixel_forge_probe.py" > "$STATE/probe.stdout.json"
record(){ local ok="$1" state="$2" detail="$3" demo="${4:-}"; python3 - "$RECEIPT" "$ok" "$state" "$detail" "$MNN_ROOT" "$demo" "$MNN_REF" <<'PY'
import json,sys,time
path,ok,state,detail,mnn,demo,ref=sys.argv[1:]
obj={'schema':'vlad.pixel-forge.mnn-bootstrap.v4','ok':ok=='1','state':state,'detail':detail,'mnnRoot':mnn,'mnnRef':ref,'diffusionDemo':demo or None,'device':'primary-phone','ciUsed':False,'godotPolicy':'forge-only-not-delivery-runtime','recordedAtEpoch':int(time.time())}
open(path,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n'); print(json.dumps(obj,indent=2,sort_keys=True))
PY
}
for tool in git cmake ninja clang python3; do command -v "$tool" >/dev/null 2>&1 || { record 0 BLOCKED "missing phone tool: $tool"; exit 10; }; done
python3 - <<'PY' >/dev/null 2>&1 || { record 0 BLOCKED 'Python Pillow is required for canonical VPX packing; install it on the phone before Pixel Forge.'; exit 16; }
from PIL import Image
PY
FREE_KB="$(df -Pk "$HOME" | awk 'NR==2 {print $4}')"; MIN_FREE_KB="${HC_PIXEL_FORGE_MIN_FREE_KB:-8388608}"
[ "$FREE_KB" -ge "$MIN_FREE_KB" ] || { record 0 BLOCKED "insufficient free storage: ${FREE_KB}KiB; require ${MIN_FREE_KB}KiB"; exit 11; }
NDK="${ANDROID_NDK:-${ANDROID_NDK_HOME:-}}"
if [ -z "$NDK" ]; then for p in "$HOME/android-sdk/ndk"/* "$PREFIX/share/android-ndk" "$HOME/Android/Sdk/ndk"/*; do [ -d "$p" ] && NDK="$p"; done; fi
[ -n "$NDK" ] && [ -d "$NDK" ] || { record 0 BLOCKED 'Android NDK not found on phone; refusing blind multi-GB SDK install.'; exit 12; }
export ANDROID_NDK="$NDK"
if [ ! -d "$MNN_ROOT/.git" ]; then
  git clone --filter=blob:none --no-checkout https://github.com/alibaba/MNN.git "$MNN_ROOT"
else
  DIRTY="$(git -C "$MNN_ROOT" status --porcelain)"
  [ -z "$DIRTY" ] || { record 0 BLOCKED 'Existing MNN checkout is dirty; refusing to overwrite unrelated local work.'; exit 17; }
fi
git -C "$MNN_ROOT" fetch --depth 1 origin "refs/tags/$MNN_REF:refs/tags/$MNN_REF"
git -C "$MNN_ROOT" checkout --detach "$MNN_REF"
ACTUAL_REF="$(git -C "$MNN_ROOT" describe --tags --exact-match 2>/dev/null || true)"
[ "$ACTUAL_REF" = "$MNN_REF" ] || { record 0 BLOCKED "MNN ref mismatch expected=$MNN_REF actual=$ACTUAL_REF"; exit 13; }
BUILD="$MNN_ROOT/project/android/build_vlad_pixel_forge"; rm -rf "$BUILD"; mkdir -p "$BUILD"; cd "$BUILD"
cmake ../../.. -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE="$ANDROID_NDK/build/cmake/android.toolchain.cmake" \
  -DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=android-26 \
  -DMNN_LOW_MEMORY=ON -DMNN_ARM82=ON -DMNN_OPENCL=ON \
  -DMNN_BUILD_DIFFUSION=ON -DMNN_BUILD_FOR_ANDROID_COMMAND=ON \
  -DMNN_BUILD_OPENCV=ON -DMNN_IMGCODECS=ON -DMNN_SUPPORT_TRANSFORMER_FUSE=ON \
  -DMNN_BUILD_TOOLS=ON -DMNN_BUILD_CONVERTER=OFF -DMNN_BUILD_TEST=OFF \
  -DMNN_SEP_BUILD=OFF -DCMAKE_BUILD_TYPE=Release
ninja -j"${HC_PIXEL_FORGE_BUILD_JOBS:-2}" diffusion_demo
DEMO="$(find "$BUILD" -type f -name diffusion_demo -perm -u+x -print | head -1)"
[ -n "$DEMO" ] && [ -x "$DEMO" ] || { record 0 BLOCKED 'MNN build did not produce executable diffusion_demo.'; exit 14; }
LIBS="$(find "$BUILD" -type f \( -name '*.so' -o -name '*.a' \) -print | head -200)"
[ -n "$LIBS" ] || { record 0 BLOCKED 'MNN build finished without native libraries.'; exit 15; }
printf '%s\n' "$LIBS" > "$STATE/mnn-libraries.txt"
printf '%s\n' "$DEMO" > "$STATE/diffusion-demo.path"
record 1 BUILT "MNN $MNN_REF diffusion_demo built locally on phone with TokForge-compatible tokenizer layout; NDK=$NDK" "$DEMO"
