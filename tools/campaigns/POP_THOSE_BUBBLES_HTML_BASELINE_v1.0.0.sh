#!/data/data/com.termux/files/usr/bin/bash
# POP_THOSE_BUBBLES_HTML_BASELINE_v1.0.0: phone-owned GitHub repo creation
set -Eeuo pipefail
umask 077
NAME=POP_THOSE_BUBBLES_HTML_BASELINE_v1.0.0
OWNER=Valar05
REPO=pop-those-bubbles
DEST="$HOME/projects/$REPO"
ARCHIVE="$HOME/storage/downloads/POP_THOSE_BUBBLES_ASSETS_v1.zip"
EXPECTED=61cd3b3c08ae74f3a8de69be2c7b3b01375a553d4b348906d7fbd1f70b0ff2cf
STATE="$HOME/.local/state/$NAME"
mkdir -p "$STATE"
RUN="$(date -u +%Y%m%dT%H%M%SZ)-$$"
LOG="$STATE/$RUN.log"
PHASE=boot
MODE="${1:---dry-run}"
receipt(){ echo "CAMPAIGN=$NAME RESULT=$1 PHASE=$PHASE DETAIL=$2 LOG=$LOG" | tee "$STATE/latest.txt"; echo "$(date -u +%FT%TZ) $1 $PHASE $2" >> "$STATE/history.txt"; if command -v termux-clipboard-set >/dev/null; then termux-clipboard-set < "$STATE/latest.txt" || true; else echo CLIPBOARD_UNAVAILABLE; fi; }
failed(){ local rc="$1"; trap - ERR; receipt BLOCKED "exit=$rc"; exit "$rc"; }
trap 'failed "$?"' ERR
case "$MODE" in
 --status) cat "$STATE/latest.txt" 2>/dev/null || echo NO_RECEIPT; exit 0;;
 --stop) if test -f "$STATE/serve.pid"; then pid="$(cat "$STATE/serve.pid")"; kill -TERM -- "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null || true; rm -f "$STATE/serve.pid"; fi; receipt STOPPED preview; exit 0;;
 --serve) command -v python >/dev/null || { echo PYTHON_REQUIRED; exit 2; }; test -f "$DEST/index.html" || { echo NOT_INSTALLED; exit 3; }; (cd "$DEST"; setsid python -m http.server 8765 --bind 127.0.0.1 </dev/null > "$STATE/serve.log" 2>&1 & echo $! > "$STATE/serve.pid"); sleep 1; curl -fsS http://127.0.0.1:8765/ >/dev/null; receipt PREVIEW_STARTED http://127.0.0.1:8765/; exit 0;;
 --dry-run|--apply|--resume) ;;
 *) echo 'Use --dry-run, --apply, --resume, --serve, --status or --stop'; exit 2;;
esac
exec > >(tee -a "$LOG") 2>&1
echo "CAMPAIGN=$NAME MODE=$MODE"
echo "ARCHIVE=$ARCHIVE TARGET=$OWNER/$REPO DEST=$DEST"
echo 'EXCLUDES=hose swipe wind lightning fireball poison upgrades'
PHASE=preflight
for bin in git gh unzip sha256sum curl; do command -v "$bin" >/dev/null && echo "FOUND=$bin" || echo "MISSING=$bin"; done
if gh auth status >/dev/null 2>&1; then echo GH_AUTH_OK; else echo GH_AUTH_MISSING; fi
test -f "$ARCHIVE" && echo ARCHIVE_PRESENT || echo ARCHIVE_MISSING
if test "$MODE" = --dry-run; then receipt DRY_RUN checks_only; exit 0; fi
for bin in git gh unzip sha256sum; do command -v "$bin" >/dev/null || { echo "REQUIRES=$bin"; exit 4; }; done
gh auth status >/dev/null 2>&1 || { echo TERMUX_GITHUB_AUTH_NOT_READY; exit 5; }
test -f "$ARCHIVE" || { echo ASSET_ARCHIVE_REQUIRED; exit 6; }
echo "$EXPECTED  $ARCHIVE" | sha256sum -c -
unzip -tq "$ARCHIVE"
files="$(unzip -Z1 "$ARCHIVE" | LC_ALL=C sort)"
required="$(printf 'README.md\nbackground.png\nbubble.png\ngame.js\nindex.html\nstyle.css')"
test "$files" = "$required" || { echo INVALID_ARCHIVE_MEMBERS; exit 7; }
PHASE=guard
remote="https://github.com/$OWNER/$REPO.git"
exists=0
gh repo view "$OWNER/$REPO" --json name >/dev/null 2>&1 && exists=1
if test -e "$DEST"; then
 test -d "$DEST/.git" || { echo UNRELATED_DESTINATION; exit 8; }
 test -z "$(git -C "$DEST" status --porcelain)" || { echo DIRTY_REPO_REFUSED; exit 9; }
 origin="$(git -C "$DEST" remote get-url origin)"
 case "$origin" in "$remote"|"git@github.com:$OWNER/$REPO.git") :;; *) echo ORIGIN_MISMATCH; exit 10;; esac
 test "$exists" -eq 1 || { echo REMOTE_ABSENT; exit 11; }
 git -C "$DEST" fetch origin main
 test "$(git -C "$DEST" rev-parse HEAD)" = "$(git -C "$DEST" rev-parse origin/main)" || { echo DIVERGENT_REPOSITORY; exit 12; }
else
 test "$exists" -eq 0 || { echo REMOTE_EXISTS_BUT_LOCAL_MISSING; exit 13; }
fi
PHASE=stage
STAGE="$(mktemp -d "$STATE/stage.XXXXXXXX")"
trap 'rm -rf "$STAGE"' EXIT
unzip -jq "$ARCHIVE" -d "$STAGE"
test -s "$STAGE/game.js" || { echo MISSING_GAME_SCRIPT; exit 14; }
for token in pointerup spawner split tap draw; do grep -Fq "$token" "$STAGE/game.js" || { echo "SOURCE_FEATURE_MISSING=$token"; exit 15; }; done
for token in chainLightning fireball toxicPool SwipeHose; do if grep -Fq "$token" "$STAGE/game.js"; then echo "EXCLUDED_FEATURE_FOUND=$token"; exit 16; fi; done
echo BASELINE_STATIC_CHECK_PASS
PHASE=publish
if test "$exists" -eq 0; then
 gh repo create "$OWNER/$REPO" --private --description 'Tap-only HTML Canvas revival of Pop Those Bubbles'
 mkdir -p "$DEST"
 git -C "$DEST" init -b main
 git -C "$DEST" remote add origin "$remote"
fi
for file in index.html style.css game.js bubble.png background.png README.md; do cp "$STAGE/$file" "$DEST/$file"; done
printf '.DS_Store\n*.log\nnode_modules/\n' > "$DEST/.gitignore"
git -C "$DEST" add index.html style.css game.js bubble.png background.png README.md .gitignore
if ! git -C "$DEST" diff --cached --quiet; then
 git -C "$DEST" -c user.name='Drew Clarke' -c user.email='drew@users.noreply.github.com' commit -m 'Revive tap-only bubble game in HTML Canvas'
 git -C "$DEST" push -u origin main
fi
PHASE=verify
sha="$(git -C "$DEST" rev-parse HEAD)"
git -C "$DEST" fetch origin main
test "$sha" = "$(git -C "$DEST" rev-parse origin/main)"
test -z "$(git -C "$DEST" status --porcelain)"
git -C "$DEST" status --short
receipt SOURCE_PUBLISHED "https://github.com/$OWNER/$REPO @ $sha; browser review pending"
