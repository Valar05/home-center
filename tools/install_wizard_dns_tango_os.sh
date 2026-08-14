#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
BIN="$HOME/.local/bin"
STATE="$HOME/.local/state/wizard-dns-tango"
mkdir -p "$BIN" "$STATE" "$STATE/receipts"

cat > "$BIN/wdt" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$ROOT"; STATE="$STATE"
start_one(){ name="\$1"; shift; tmux has-session -t "\$name" 2>/dev/null || tmux new-session -d -s "\$name" "cd '\$ROOT' && WDT_STATE='\$STATE' exec \$* >>'\$STATE/\$name.log' 2>&1"; }
case "\${1:-status}" in
 start)
   rm -f "\$STATE/RELEASED" "\$STATE/TREMORCLES_RELEASED" "\$STATE/FOLEY_RELEASED" "\$STATE/VISUAL_ORCHESTRATOR_RELEASED"
   start_one wdt-kernel python3 wizard_dns_tango/os.py
   start_one wdt-mockray python3 wizard_dns_tango/mockray_daemon.py
   start_one wdt-tremorcles python3 wizard_dns_tango/tetsuya_tremorcle_morse.py
   start_one wdt-foley python3 wizard_dns_tango/runtime_foley.py
   start_one wdt-dance python3 wizard_dns_tango/visual_orchestrator.py
   printf '{"kind":"dispatch","task_id":"wdt-boot","verified":true,"at":%s,"message":"Wizard DNS Tango sensory runtime booted"}\n' "\$(date +%s)" >> "\$STATE/events.jsonl"
   ;;
 stop)
   touch "\$STATE/RELEASED" "\$STATE/TREMORCLES_RELEASED" "\$STATE/FOLEY_RELEASED" "\$STATE/VISUAL_ORCHESTRATOR_RELEASED"
   for s in wdt-kernel wdt-mockray wdt-tremorcles wdt-foley wdt-dance; do tmux kill-session -t "\$s" 2>/dev/null || true; done
   ;;
 status)
   for s in wdt-kernel wdt-mockray wdt-tremorcles wdt-foley wdt-dance; do tmux has-session -t "\$s" 2>/dev/null && echo "● \$s" || echo "○ \$s"; done
   echo; cat "\$STATE/dance-card.txt" 2>/dev/null || true
   ;;
 watch)
   while :; do clear; "\$0" status; printf '\a'; sleep 2; done
   ;;
 logs) tail -n 100 "\$STATE"/*.log 2>/dev/null || true ;;
 *) echo 'wdt start|stop|status|watch|logs' >&2; exit 2 ;;
esac
EOF
chmod +x "$BIN/wdt"
"$BIN/wdt" start
printf '{"schema":"wizard-dns-tango-install-v2","installed":true,"services":["kernel","mockray","tremorcles","foley","dance"],"watch":"wdt watch","state":"%s"}\n' "$STATE" > "$STATE/install-receipt.json"
cat "$STATE/install-receipt.json"
