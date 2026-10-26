#!/usr/bin/env bash
# Termux-only installer for a stable 'cauldron' command. No SSH server changes.
set -euo pipefail
if [[ -z "${PREFIX:-}" || "${PREFIX}" != *com.termux* ]]; then
  echo "ERROR: Run this in Termux, not Windows or a generic Linux host." >&2; exit 2
fi
command -v ssh >/dev/null || { echo "ERROR: OpenSSH client missing. Install the Termux openssh package." >&2; exit 2; }
command -v python3 >/dev/null || { echo "ERROR: Python missing. Install the Termux python package." >&2; exit 2; }
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
RESOLVER="$ROOT/tools/resolve_cauldron_ssh.py"
[[ -r "$RESOLVER" ]] || { echo "ERROR: Missing existing Home Center resolver: $RESOLVER" >&2; exit 2; }
INSTALL_DIR="$HOME/.local/share/cauldron-ssh"
mkdir -p "$INSTALL_DIR" "$PREFIX/bin"
cp "$RESOLVER" "$INSTALL_DIR/resolve_cauldron_ssh.py.tmp"
python3 -m py_compile "$INSTALL_DIR/resolve_cauldron_ssh.py.tmp"
mv -f "$INSTALL_DIR/resolve_cauldron_ssh.py.tmp" "$INSTALL_DIR/resolve_cauldron_ssh.py"
# Atomic installer; no alteration of ~/.ssh, guardians, Tailscale, or relay watchdogs.
cat > "$PREFIX/bin/cauldron.tmp" <<'WRAPPER'
#!/usr/bin/env bash
set -u
RESOLVER="$HOME/.local/share/cauldron-ssh/resolve_cauldron_ssh.py"
STATE="$HOME/.local/state/fortress-online/cauldron-ssh-endpoint.json"
usage() { echo 'Usage: cauldron [--doctor|--retry|--] [remote shell args...]'; }
if [[ ${1:-} == --help || ${1:-} == -h ]]; then usage; exit 0; fi
if [[ ! -r "$RESOLVER" ]]; then echo "CAULDRON_ERROR=resolver_missing" >&2; exit 3; fi
doctor=false
retry=false
if [[ ${1:-} == --doctor ]]; then doctor=true; shift; fi
if [[ ${1:-} == --retry ]]; then retry=true; shift; fi
# Resolver first requires authenticated SSH to THECAULDRON and writes verified endpoint.
resolve() {
  local output rc
  output="$(python3 "$RESOLVER" 2>"${TMPDIR:-/tmp}/cauldron-resolve-$$.err")"; rc=$?
  if ((rc!=0)); then
    echo "CAULDRON_ERROR=resolution_failed; ssh authentication, Tailscale connectivity, or Windows sshd unavailable" >&2
    cat "${TMPDIR:-/tmp}/cauldron-resolve-$$.err" >&2
    rm -f "${TMPDIR:-/tmp}/cauldron-resolve-$$.err"
    return "$rc"
  fi
  rm -f "${TMPDIR:-/tmp}/cauldron-resolve-$$.err"
  printf '%s' "$output"
}
endpoint="$(resolve)" || exit $?
if $doctor; then
  echo "CAULDRON_PROBE=PASS endpoint=$endpoint"
  echo "NOTE: this proves an authenticated hostname probe, not an interactive session or remote shell persistence."
  exit 0
fi
if [[ "$endpoint" =~ ^([^@]+)@([^:]+)(:([0-9]+))?$ ]]; then
  user="${BASH_REMATCH[1]}"; host="${BASH_REMATCH[2]}"; port="${BASH_REMATCH[4]:-22}"
else echo "CAULDRON_ERROR=bad_endpoint" >&2; exit 3; fi
command=(ssh -tt -p "$port" -o ConnectTimeout=8 -o ServerAliveInterval=15 -o ServerAliveCountMax=3 -o TCPKeepAlive=yes -o StrictHostKeyChecking=yes -o ExitOnForwardFailure=yes -- "$user@$host")
if (($#)); then command+=("$@"); fi
attempt=0
while :; do
  "${command[@]}"
  code=$?
  if ! $retry || ((code!=255)); then exit "$code"; fi
  attempt=$((attempt+1))
  if ((attempt>12)); then echo "CAULDRON_ERROR=retry_limit_reached" >&2; exit 255; fi
  delay=$((attempt*2)); ((delay>20)) && delay=20
  echo "Cauldron SSH transport interrupted (exit 255); reconnecting in ${delay}s (attempt ${attempt}/12)." >&2
  sleep "$delay"
  endpoint="$(resolve)" || continue
  if [[ "$endpoint" =~ ^([^@]+)@([^:]+)(:([0-9]+))?$ ]]; then
    user="${BASH_REMATCH[1]}"; host="${BASH_REMATCH[2]}"; port="${BASH_REMATCH[4]:-22}"
    command=(ssh -tt -p "$port" -o ConnectTimeout=8 -o ServerAliveInterval=15 -o ServerAliveCountMax=3 -o TCPKeepAlive=yes -o StrictHostKeyChecking=yes -o ExitOnForwardFailure=yes -- "$user@$host")
    if (($#)); then command+=("$@"); fi
  fi
done
WRAPPER
chmod 700 "$PREFIX/bin/cauldron.tmp"
mv -f "$PREFIX/bin/cauldron.tmp" "$PREFIX/bin/cauldron"
command -v cauldron || { echo "ERROR: command not on PATH" >&2; exit 4; }
echo "CAULDRON_INSTALL=OK"
echo "Run 'cauldron --doctor' for a live authenticated probe; run 'cauldron' to connect."
echo "Optional 'cauldron --retry' reconnects transport on SSH failure, but does NOT resume a terminated remote shell."
