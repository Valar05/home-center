#!/usr/bin/env python3
from __future__ import annotations
import ipaddress,json,os,socket,subprocess,sys,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path

USER=os.environ.get('FORTRESS_CAULDRON_USER','dclar')
EXPECTED=os.environ.get('FORTRESS_CAULDRON_HOSTNAME','THECAULDRON').lower()
STATE=Path.home()/'.local/state/fortress-online/cauldron-ssh-endpoint.json'


def run(cmd,timeout=8):
    return subprocess.run(cmd,text=True,capture_output=True,timeout=timeout)


def wifi_reconnect():
    rish=os.environ.get('RISH') or shutil_which('rish') or str(Path.home()/'bin/rish')
    if not Path(rish).exists() and not shutil_which(rish):
        return {'attempted':False,'ok':False,'detail':'rish missing'}
    p=run([rish,'-c','svc wifi enable; cmd wifi reconnect >/dev/null 2>&1 || true; ip route'],10)
    return {'attempted':True,'ok':p.returncode==0,'detail':(p.stdout+p.stderr)[-1200:]}


def shutil_which(name):
    import shutil
    return shutil.which(name)


def local_networks():
    p=run(['ip','-4','route'],4)
    nets=[]
    for line in p.stdout.splitlines():
        parts=line.split()
        if not parts: continue
        try:
            if '/' in parts[0]:
                net=ipaddress.ip_network(parts[0],strict=False)
                if net.version==4 and net.is_private:
                    nets.append(net)
        except ValueError: pass
    # Keep discovery bounded. Collapse larger LANs to the phone's /24 when src is known.
    bounded=[]
    for net in nets:
        if net.prefixlen>=24:
            bounded.append(net)
        else:
            bounded.extend(list(net.subnets(new_prefix=24))[:16])
    # Prefer directly-connected, unique networks.
    out=[]
    seen=set()
    for n in bounded:
        s=str(n)
        if s not in seen:
            seen.add(s); out.append(n)
    return out[:16]


def port22(ip):
    try:
        with socket.create_connection((str(ip),22),timeout=.28): return str(ip)
    except OSError: return None


def verify(ip):
    destination=f'{USER}@{ip}'
    cmd=['ssh','-o','BatchMode=yes','-o','PasswordAuthentication=no','-o','KbdInteractiveAuthentication=no',
         '-o','StrictHostKeyChecking=accept-new','-o','ConnectTimeout=2',destination,
         'powershell -NoProfile -Command "$env:COMPUTERNAME" 2>$null || hostname']
    try: p=run(cmd,5)
    except Exception as exc: return None,repr(exc)
    observed=(p.stdout.strip() or p.stderr.strip())[-500:]
    if p.returncode==0 and p.stdout.strip().lower()==EXPECTED:
        return f'{USER}@{ip}',observed
    return None,observed


def main():
    wifi=wifi_reconnect()
    # Let Android finish reassociation without turning this into an unbounded wait.
    time.sleep(1.5)
    nets=local_networks()
    if not nets:
        print(json.dumps({'ok':False,'state':'no_private_lan','wifi':wifi},indent=2)); return 2
    hosts=[]
    for net in nets:
        hosts.extend(list(net.hosts()))
    # Hard safety bound even if routing is weird.
    hosts=hosts[:4096]
    open_ips=[]
    with ThreadPoolExecutor(max_workers=96) as ex:
        futures=[ex.submit(port22,ip) for ip in hosts]
        for fut in as_completed(futures):
            v=fut.result()
            if v: open_ips.append(v)
    attempts=[]
    for ip in open_ips:
        endpoint,obs=verify(ip); attempts.append({'ip':ip,'observed':obs})
        if endpoint:
            STATE.parent.mkdir(parents=True,exist_ok=True)
            obj={'ok':True,'endpoint':endpoint,'hostname':EXPECTED.upper(),'wifi':wifi,'networks':[str(n) for n in nets],'verifiedAtEpoch':int(time.time())}
            STATE.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
            print(endpoint)
            return 0
    print(json.dumps({'ok':False,'state':'cauldron_not_found','wifi':wifi,'networks':[str(n) for n in nets],'openSshCandidates':attempts},indent=2))
    return 3

if __name__=='__main__': raise SystemExit(main())
