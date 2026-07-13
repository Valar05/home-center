#!/data/data/com.termux/files/usr/bin/sh
set -eu

ROOT="/storage/emulated/0/Documents/GodotProjects/home-center"
HOST_DISPLAY="${DISPLAY:-}"

exec proot-distro login debian -- sh -lc '
set -eu
cd /storage/emulated/0/Documents/GodotProjects/home-center/browser-worker
export PATH=/usr/bin:/bin:/usr/sbin:/sbin
export HOME_CENTER_CHROMIUM_EXECUTABLE=/usr/bin/chromium
export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
if [ "${1:-}" != "" ]; then
  export DISPLAY="$1"
fi
shift || true
if [ ! -d node_modules/playwright ]; then
  npm install --ignore-scripts --no-bin-links >/dev/null
fi
node src/chatgpt_plugin_debug.mjs "$@"
' sh "$HOST_DISPLAY" "$@"
