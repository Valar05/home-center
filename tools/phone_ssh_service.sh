#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

STATE_ROOT="${HC_STATE_DIR:-$HOME/.local/state/home-center}/phone-ssh"
RECEIPTS="$STATE_ROOT/receipts.jsonl"
LATEST="$STATE_ROOT/latest.json"
DIAG="$STATE_ROOT/diagnostic.txt"
PORT="${FORTRESS_PHONE_SSH_PORT:-8022}"
mkdir -p "$STATE_ROOT"

emit(){
  local action="$1" ok="$2" state="$3" detail="$4"
  python3 - "$RECEIPTS" "$LATEST" "$action" "$ok" "$state" "$detail" "$PORT" <<'PY'
import json,os,sys,time
receipts,latest,action,ok,state,detail,port=sys.argv[1:]
obj={'schema':'fortress-phone-ssh-v1','atEpoch':int(time.time()),'action':action,'ok':ok=='1','state':state,'detail':detail,'port':int(port)}
os.makedirs(os.path.dirname(latest),exist_ok=True)
with open(receipts,'a',encoding='utf-8') as f:f.write(json.dumps(obj,sort_keys=True)+'\n')
if os.path.getsize(receipts)>512*1024:
 lines=open(receipts,encoding='utf-8').read().splitlines()[-1000:]
 tmp=receipts+'.tmp';open(tmp,'w',encoding='utf-8').write('\n'.join(lines)+'\n');os.replace(tmp,receipts)
tmp=latest+'.tmp';open(tmp,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n');os.replace(tmp,latest)
print(json.dumps(obj,sort_keys=True))
PY
}

# A running sshd or an occupied TCP port is not SSH proof. The service already
# requires python3 for receipts, so use an active localhost protocol probe and
# require the SSH identification banner before reporting healthy.
listener_ok(){
  command -v python3 >/dev/null 2>&1 || return 1
  python3 - "$PORT" <<'PY' >/dev/null 2>&1
import socket,sys
port=int(sys.argv[1])
with socket.create_connection(('localhost',port),timeout=0.8) as sock:
    sock.settimeout(0.8)
    banner=sock.recv(128)
if not banner.startswith(b'SSH-'):
    raise SystemExit(2)
PY
}

process_ok(){ pgrep -f '(^|/)sshd([[:space:]]|$)' >/dev/null 2>&1; }
healthy_local(){ process_ok && listener_ok; }

status(){
  if healthy_local; then emit status 1 listening "sshd process and SSH banner are independently proven on port ${PORT}"; return 0; fi
  if process_ok; then emit status 0 process_without_listener "sshd exists but SSH service on port ${PORT} is not proven callable locally"; return 2; fi
  emit status 0 stopped "sshd is not running"; return 2
}

install_deps(){
  command -v sshd >/dev/null 2>&1 && return 0
  command -v pkg >/dev/null 2>&1 || { emit ensure 0 openssh_missing "sshd missing and pkg unavailable"; return 3; }
  pkg install -y openssh >"$DIAG" 2>&1 || { emit ensure 0 openssh_install_failed "$(tail -c 1200 "$DIAG" 2>/dev/null || true)"; return 3; }
}

config_check(){
  : >"$DIAG"
  sshd -t >"$DIAG" 2>&1 || { emit diagnose 0 config_invalid "$(tail -c 1600 "$DIAG" 2>/dev/null || true)"; return 1; }
}

start_sshd(){
  mkdir -p "$HOME/.ssh"; chmod 700 "$HOME/.ssh"
  ssh-keygen -A >>"$DIAG" 2>&1 || true
  config_check || return 1
  if command -v sv >/dev/null 2>&1 && [ -d "${PREFIX:-}/var/service/sshd" ]; then
    sv up sshd >>"$DIAG" 2>&1 || true
  fi
  if ! process_ok; then
    sshd >>"$DIAG" 2>&1 || true
  fi
  for _ in 1 2 3 4 5; do healthy_local && return 0; sleep 1; done
  return 1
}

failure_detail(){
  local proc='absent' listener='unproven'
  process_ok && proc='present' || true
  listener_ok && listener='ssh_banner_present' || true
  printf 'process=%s listener=%s port=%s; %s' "$proc" "$listener" "$PORT" "$(tail -c 1600 "$DIAG" 2>/dev/null || true)"
}

ensure(){
  if healthy_local; then emit ensure 1 listening "sshd remains healthy on port ${PORT}"; return 0; fi
  install_deps || return $?
  if start_sshd; then emit ensure 1 listening "sshd started and SSH banner is proven on port ${PORT}"; return 0; fi
  emit ensure 0 start_failed "$(failure_detail)"; return 4
}

repair(){
  if healthy_local; then emit repair 1 healthy "SSH already healthy; no restart required"; return 0; fi
  install_deps || return $?
  if start_sshd; then emit repair 1 recovered "SSH recovered and SSH banner is proven"; return 0; fi
  pkill -TERM -f '(^|/)sshd([[:space:]]|$)' >/dev/null 2>&1 || true
  sleep 1
  if start_sshd; then emit repair 1 recovered "sshd restarted and SSH banner is proven"; return 0; fi
  emit repair 0 failed "$(failure_detail)"; return 5
}

case "${1:-status}" in
  status) status ;;
  ensure) ensure ;;
  repair) repair ;;
  receipts) [ -f "$LATEST" ] && cat "$LATEST" || status ;;
  *) echo 'usage: phone_ssh_service.sh [status|ensure|repair|receipts]' >&2; exit 64 ;;
esac
