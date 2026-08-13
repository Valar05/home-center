#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

STATE_ROOT="${HC_STATE_DIR:-$HOME/.local/state/home-center}/phone-ssh"
RECEIPTS="$STATE_ROOT/receipts.jsonl"
LATEST="$STATE_ROOT/latest.json"
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
tmp=latest+'.tmp';open(tmp,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n');os.replace(tmp,latest)
print(json.dumps(obj,sort_keys=True))
PY
}

listener_ok(){
  if command -v ss >/dev/null 2>&1; then
    ss -ltn 2>/dev/null | grep -Eq "[:.]${PORT}[[:space:]]"
  else
    pgrep -x sshd >/dev/null 2>&1
  fi
}

status(){
  local proc=0 listen=0
  pgrep -x sshd >/dev/null 2>&1 && proc=1 || true
  listener_ok && listen=1 || true
  if [ "$proc" -eq 1 ] && [ "$listen" -eq 1 ]; then emit status 1 listening "sshd process and local listener present"; return 0; fi
  if [ "$proc" -eq 1 ]; then emit status 0 process_without_listener "sshd exists but port ${PORT} is not listening"; return 2; fi
  emit status 0 stopped "sshd is not running"; return 2
}

install_deps(){
  command -v sshd >/dev/null 2>&1 && return 0
  command -v pkg >/dev/null 2>&1 || { emit ensure 0 openssh_missing "sshd missing and pkg unavailable"; return 3; }
  pkg install -y openssh >/dev/null
}

start_sshd(){
  mkdir -p "$HOME/.ssh"
  chmod 700 "$HOME/.ssh"
  ssh-keygen -A >/dev/null 2>&1 || true
  if command -v sv >/dev/null 2>&1 && [ -d "${PREFIX:-}/var/service/sshd" ]; then
    sv up sshd >/dev/null 2>&1 || true
  else
    sshd >/dev/null 2>&1 || true
  fi
  for _ in 1 2 3 4 5; do listener_ok && return 0; sleep 1; done
  return 1
}

ensure(){
  if status >/dev/null 2>&1; then status; return 0; fi
  install_deps || return $?
  if start_sshd; then emit ensure 1 listening "sshd started and port ${PORT} is listening"; return 0; fi
  emit ensure 0 start_failed "sshd could not establish listener on port ${PORT}"; return 4
}

repair(){
  if ensure >/dev/null 2>&1; then emit repair 1 healthy "SSH already healthy or recovered without destructive restart"; return 0; fi
  pkill -TERM -x sshd >/dev/null 2>&1 || true
  sleep 1
  if start_sshd; then emit repair 1 recovered "sshd restarted and listener restored"; return 0; fi
  emit repair 0 failed "restart did not restore listener on port ${PORT}"; return 5
}

case "${1:-status}" in
  status) status ;;
  ensure) ensure ;;
  repair) repair ;;
  receipts) [ -f "$LATEST" ] && cat "$LATEST" || status ;;
  *) echo 'usage: phone_ssh_service.sh [status|ensure|repair|receipts]' >&2; exit 64 ;;
esac
