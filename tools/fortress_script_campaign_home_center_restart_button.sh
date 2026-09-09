#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="${HC_REPO_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"
STATE="${HC_STATE_DIR:-$HOME/.local/state/home-center}/script-campaigns/home-center-restart-button"
SESSION="hc-restart-button"
MISSION="$STATE/mission.txt"
LOG="$STATE/campaign.log"
RECEIPT="$STATE/receipt.txt"
mkdir -p "$STATE"
command -v tmux >/dev/null 2>&1 || { echo 'BLOCKED: tmux missing' >&2; exit 2; }

cat >"$MISSION" <<'MISSION'
FORTRESS BLOCKING CAMPAIGN — HOME CENTER RESTART BUTTON

COMMISSION
Drew already commissioned one obvious phone control: when the Home Center overlay says HC • OFFLINE / HOME CENTER • OFFLINE, a visible button on that SAME overlay must let him turn Home Center back on. This is not the existing control-enable toggle. It must recover the actual primary-phone Home Center relay and only report ON after fresh relay heartbeat proof.

DO NOT REINTERPRET
- Not a terminal command for Drew.
- Not a notification-only substitute.
- Not a new dashboard.
- Not a generic Repair All menu several taps away.
- Not "Enable control"; control-enabled + relay-offline is the exact failure shown in the screenshot.
- Existing notification recovery may remain as fallback, but it does not satisfy this commission.

KNOWN RECEIPTS / EXISTING PRIMITIVES
- `OperatorOverlayService.refreshUi()` distinguishes enabled-but-offline from CONTROL OFF.
- `home_center_phone_relay_recover.sh` is the canonical relay recovery primitive and requires fresh primary-phone heartbeat before success.
- `CartEventBridge.wakeTermux()` already proves this repository uses `com.termux.RUN_COMMAND` to execute a bounded Termux command from Android. Reuse that pattern rather than inventing a new bridge.
- receipt `receipts/venice/2026-08-14-phone-ingress-health-truth-plan.json` forbids PID theater, stale online logs, desktop proof, or asking Drew to type recovery commands while a machine lane exists.
- candidate helper `tools/home_center_recovery_button.sh` may be reused for recovery semantics but is NOT acceptance because it is notification-surface only.

IMPLEMENTATION TARGET
1. Add a dedicated visible overlay button with an unambiguous label such as `TURN HC ON` or `RESTART HC` whenever control is enabled but heartbeat is stale/offline.
2. Button invokes one bounded recovery command via the existing Termux RUN_COMMAND integration pattern, targeting the canonical relay recovery primitive.
3. While recovery is in progress, show a deterministic working state and prevent button-spam races.
4. Do not claim ON until the existing OperatorState heartbeat becomes fresh.
5. If recovery fails, leave the button visible and surface the failure without disabling ordinary overlay interaction.
6. Keep control enable/disable semantics separate. STOP remains STOP.
7. Add regression tests that distinguish CONTROL OFF from HC OFFLINE and assert restart button visibility/label/action only for the latter.
8. Build with existing phone build tooling; use existing signer-safe deployment/recovery tooling. Never uninstall a working overlay to bypass signer mismatch.
9. Physical acceptance requires screenshot/UI-state evidence from the primary phone showing: OFFLINE + restart button; button press; later ON or truthful still-offline result. Source/PR/APK alone is not delivery.

TIME NOW
This is a previously commissioned tiny-obvious UI control that survived multiple turns. Treat it as P0. Do not polish adjacent systems until this is delivered or a genuine external authority boundary is proven.

SAINT ANDREW
CONTINUE after source mutation, tests, build, and worker exit. Stop only after physical phone evidence or an exact external boundary. Persist receipts.
MISSION

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "ALIVE $SESSION"
  exit 0
fi

RUN="cd '$ROOT'; echo \"START \$(date -Iseconds)\" >>'$LOG'; if command -v adam >/dev/null 2>&1; then adam \"\$(cat '$MISSION')\"; elif [ -f tools/adam_planned_venice.py ]; then python3 tools/adam_planned_venice.py \"\$(cat '$MISSION')\"; else echo BLOCKED:no-worker; exit 127; fi >>'$LOG' 2>&1; rc=\$?; printf 'exit=%s time=%s\\n' \"\$rc\" \"\$(date -Iseconds)\" >'$RECEIPT'; exit \$rc"
tmux new-session -d -s "$SESSION" "$RUN"
echo "LAUNCHED $SESSION"
echo "mission=$MISSION"
echo "log=$LOG"
echo "receipt=$RECEIPT"
