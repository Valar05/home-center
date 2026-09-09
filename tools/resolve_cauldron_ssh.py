#!/usr/bin/env python3
from __future__ import annotations

import ipaddress
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

USER = os.environ.get('FORTRESS_CAULDRON_USER', 'dclar')
EXPECTED = os.environ.get('FORTRESS_CAULDRON_HOSTNAME', 'THECAULDRON').strip() or 'THECAULDRON'
EXPECTED_LOWER = EXPECTED.lower().rstrip('.')
DEFAULT_PORT = int(os.environ.get('FORTRESS_CAULDRON_SSH_PORT', '22'))
STATE = Path.home() / '.local/state/fortress-online/cauldron-ssh-endpoint.json'


def run(cmd, timeout=8):
    return subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, check=False)


def parse_endpoint(value: str) -> tuple[str, str, int]:
    raw = str(value or '').strip()
    if not raw:
        raise ValueError('empty endpoint')
    user_host, sep, port_text = raw.rpartition(':')
    if sep and port_text.isdigit() and ']' not in port_text:
        endpoint = user_host
        port = int(port_text)
    else:
        endpoint = raw
        port = DEFAULT_PORT
    if '@' in endpoint:
        user, host = endpoint.rsplit('@', 1)
    else:
        user, host = USER, endpoint
    return user or USER, host.strip('[]'), port


def format_endpoint(user: str, host: str, port: int) -> str:
    base = f'{user}@{host}' if user else host
    return base if port == 22 else f'{base}:{port}'


def hostname_matches(value: str) -> bool:
    text = str(value or '').strip().lower().rstrip('.')
    return text == EXPECTED_LOWER or text.startswith(EXPECTED_LOWER + '.')


def verify(endpoint: str, source: str) -> tuple[str | None, dict]:
    try:
        user, host, port = parse_endpoint(endpoint)
    except ValueError as exc:
        return None, {'endpoint': endpoint, 'source': source, 'error': str(exc)}
    destination = f'{user}@{host}' if user else host
    cmd = [
        'ssh', '-o', 'BatchMode=yes', '-o', 'PasswordAuthentication=no',
        '-o', 'KbdInteractiveAuthentication=no', '-o', 'StrictHostKeyChecking=accept-new',
        '-o', 'ConnectTimeout=3', '-p', str(port), destination,
        'powershell -NoProfile -Command "$env:COMPUTERNAME" 2>$null || hostname',
    ]
    started = time.monotonic()
    try:
        proc = run(cmd, 7)
    except Exception as exc:
        return None, {'endpoint': endpoint, 'source': source, 'error': repr(exc)}
    stdout = proc.stdout.strip()
    observed = {
        'endpoint': endpoint,
        'source': source,
        'returncode': proc.returncode,
        'stdout': stdout[-300:],
        'stderr': proc.stderr.strip()[-500:],
        'elapsedMs': int((time.monotonic() - started) * 1000),
    }
    if proc.returncode == 0 and hostname_matches(stdout):
        canonical = format_endpoint(user, host, port)
        return canonical, observed
    return None, observed


def cached_endpoint() -> str:
    try:
        data = json.loads(STATE.read_text(encoding='utf-8'))
        return str(data.get('endpoint') or '').strip()
    except Exception:
        return ''


def tailscale_candidates() -> list[tuple[str, str]]:
    exe = shutil.which('tailscale')
    if not exe:
        return []
    try:
        proc = run([exe, 'status', '--json'], 5)
        if proc.returncode != 0:
            return []
        data = json.loads(proc.stdout)
    except Exception:
        return []
    out: list[tuple[str, str]] = []
    peers = data.get('Peer') or {}
    values = peers.values() if isinstance(peers, dict) else peers if isinstance(peers, list) else []
    for peer in values:
        if not isinstance(peer, dict):
            continue
        names = [peer.get('HostName'), peer.get('DNSName')]
        if not any(hostname_matches(name) for name in names if name):
            continue
        dns = str(peer.get('DNSName') or '').strip().rstrip('.')
        if dns:
            out.append((format_endpoint(USER, dns, DEFAULT_PORT), 'tailscale-dns'))
        for ip in peer.get('TailscaleIPs') or []:
            try:
                ipaddress.ip_address(str(ip))
            except ValueError:
                continue
            out.append((format_endpoint(USER, str(ip), DEFAULT_PORT), 'tailscale-ip'))
    return out


def parse_networks(route_text: str) -> list[ipaddress.IPv4Network]:
    nets: list[ipaddress.IPv4Network] = []
    src_ips: list[ipaddress.IPv4Address] = []
    for line in route_text.splitlines():
        parts = line.split()
        if not parts:
            continue
        if 'src' in parts:
            try:
                src = ipaddress.ip_address(parts[parts.index('src') + 1])
                if isinstance(src, ipaddress.IPv4Address):
                    src_ips.append(src)
            except (ValueError, IndexError):
                pass
        token = parts[0]
        if '/' not in token:
            continue
        try:
            net = ipaddress.ip_network(token, strict=False)
        except ValueError:
            continue
        if isinstance(net, ipaddress.IPv4Network) and net.is_private:
            nets.append(net)
    if not nets:
        for src in src_ips:
            if src.is_private:
                nets.append(ipaddress.ip_network(f'{src}/24', strict=False))
    bounded: list[ipaddress.IPv4Network] = []
    for net in nets:
        if net.prefixlen >= 24:
            bounded.append(net)
            continue
        matching = [src for src in src_ips if src in net]
        if matching:
            bounded.append(ipaddress.ip_network(f'{matching[0]}/24', strict=False))
        else:
            bounded.extend(list(net.subnets(new_prefix=24))[:16])
    unique: list[ipaddress.IPv4Network] = []
    seen: set[str] = set()
    for net in bounded:
        key = str(net)
        if key not in seen:
            seen.add(key)
            unique.append(net)
    return unique[:16]


def local_networks() -> list[ipaddress.IPv4Network]:
    try:
        proc = run(['ip', '-4', 'route'], 4)
        return parse_networks(proc.stdout)
    except Exception:
        return []


def port_open(ip: ipaddress.IPv4Address) -> str | None:
    try:
        with socket.create_connection((str(ip), DEFAULT_PORT), timeout=0.28):
            return str(ip)
    except OSError:
        return None


def lan_candidates() -> tuple[list[tuple[str, str]], list[str]]:
    nets = local_networks()
    hosts: list[ipaddress.IPv4Address] = []
    for net in nets:
        hosts.extend(list(net.hosts()))
    hosts = hosts[:4096]
    open_ips: list[str] = []
    with ThreadPoolExecutor(max_workers=96) as executor:
        futures = [executor.submit(port_open, ip) for ip in hosts]
        for future in as_completed(futures):
            value = future.result()
            if value:
                open_ips.append(value)
    return [(format_endpoint(USER, ip, DEFAULT_PORT), 'lan-scan') for ip in open_ips], [str(n) for n in nets]


def unique_candidates(items: list[tuple[str, str]]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for endpoint, source in items:
        endpoint = str(endpoint or '').strip()
        if not endpoint or endpoint in seen:
            continue
        seen.add(endpoint)
        out.append((endpoint, source))
    return out


def main() -> int:
    candidates: list[tuple[str, str]] = []
    explicit = str(os.environ.get('FORTRESS_CAULDRON_SSH') or '').strip()
    if explicit:
        candidates.append((explicit, 'environment'))
    cached = cached_endpoint()
    if cached:
        candidates.append((cached, 'verified-cache'))
    extra = str(os.environ.get('FORTRESS_CAULDRON_CANDIDATES') or '')
    for item in extra.split(','):
        if item.strip():
            candidates.append((item.strip(), 'environment-candidate'))
    candidates.extend([
        (format_endpoint(USER, EXPECTED, DEFAULT_PORT), 'hostname'),
        (format_endpoint(USER, EXPECTED.lower(), DEFAULT_PORT), 'hostname-lower'),
        (format_endpoint(USER, EXPECTED.lower() + '.local', DEFAULT_PORT), 'mdns'),
    ])
    candidates.extend(tailscale_candidates())

    attempts: list[dict] = []
    for endpoint, source in unique_candidates(candidates):
        resolved, observed = verify(endpoint, source)
        attempts.append(observed)
        if resolved:
            STATE.parent.mkdir(parents=True, exist_ok=True)
            receipt = {
                'ok': True,
                'endpoint': resolved,
                'hostname': EXPECTED,
                'source': source,
                'shizukuRequired': False,
                'verifiedAtEpoch': int(time.time()),
                'attempts': attempts[-8:],
            }
            STATE.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8')
            print(resolved)
            return 0

    lan, networks = lan_candidates()
    for endpoint, source in unique_candidates(lan):
        resolved, observed = verify(endpoint, source)
        attempts.append(observed)
        if resolved:
            STATE.parent.mkdir(parents=True, exist_ok=True)
            receipt = {
                'ok': True,
                'endpoint': resolved,
                'hostname': EXPECTED,
                'source': source,
                'networks': networks,
                'shizukuRequired': False,
                'verifiedAtEpoch': int(time.time()),
                'attempts': attempts[-12:],
            }
            STATE.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8')
            print(resolved)
            return 0

    print(json.dumps({
        'ok': False,
        'state': 'cauldron_not_found',
        'hostname': EXPECTED,
        'networks': networks,
        'shizukuRequired': False,
        'attempts': attempts[-30:],
    }, indent=2), file=sys.stderr)
    return 3


if __name__ == '__main__':
    raise SystemExit(main())
