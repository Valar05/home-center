#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
BIN="$HOME/.local/bin"
STATE="$HOME/.local/state/home-center/wizard-dns-tango"
mkdir -p "$BIN" "$STATE" "$STATE/receipts"
cat > "$BIN/wdt" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$ROOT"
STATE="$STATE"
case "\${1:-status}" in
  start)
    rm -f "\$STATE/RELEASED"
    if ! tmux has-session -t wizard-dns-tango 2>/dev/null; then
      tmux new-session -d -s wizard-dns-tango "cd '\$ROOT' && exec python3 wizard_dns_tango/os.py >>'\$STATE/os.log' 2>&1"
    fi
    ;;
  stop)
    touch "\$STATE/RELEASED"
    tmux kill-session -t wizard-dns-tango 2>/dev/null || true
    ;;
  status)
    if tmux has-session -t wizard-dns-tango 2>/dev/null; then echo 'WIZARD DNS TANGO • ON'; else echo 'WIZARD DNS TANGO • OFF'; fi
    [ -f "\$STATE/queue.json" ] && cat "\$STATE/queue.json" || true
    ;;
  logs) tail -n 80 "\$STATE/os.log" 2>/dev/null || true ;;
  *) echo 'wdt start|stop|status|logs' >&2; exit 2 ;;
esac
EOF
chmod +x "$BIN/wdt"
"$BIN/wdt" start
printf '{"schema":"wizard-dns-tango-install-v1","installed":true,"tmux_session":"wizard-dns-tango","launcher":"%s/wdt"}\n' "$BIN" > "$STATE/install-receipt.json"
cat "$STATE/install-receipt.json"
