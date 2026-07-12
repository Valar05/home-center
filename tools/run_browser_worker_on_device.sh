#!/data/data/com.termux/files/usr/bin/sh
set -eu

ROOT="/storage/emulated/0/Documents/GodotProjects/home-center"
QUERY="${1:-scrambled eggs recipe}"

exec proot-distro login debian -- sh -lc '
set -eu
cd /storage/emulated/0/Documents/GodotProjects/home-center/browser-worker
export PATH=/usr/bin:/bin:/usr/sbin:/sbin
export HOME_CENTER_CHROMIUM_EXECUTABLE=/usr/bin/chromium
export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
npm run smoke:google -- --query "$1"
' sh "$QUERY"
