#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations
import json, os, platform, shutil, time
from pathlib import Path

SCHEMA = "vlad.pixel-forge.probe.v1"
STATE = Path(os.environ.get("HC_PIXEL_FORGE_STATE", "~/.local/state/home-center/pixel-forge")).expanduser()

def read_text(path: str, default: str = "") -> str:
    try: return Path(path).read_text(encoding="utf-8", errors="replace").strip()
    except OSError: return default

def parse_meminfo() -> dict:
    out = {}
    for line in read_text("/proc/meminfo").splitlines():
        if ":" not in line: continue
        key, rest = line.split(":", 1); parts = rest.strip().split()
        if not parts: continue
        try: value = int(parts[0])
        except ValueError: continue
        if len(parts) > 1 and parts[1].lower() == "kb": value *= 1024
        out[key] = value
    return out

def thermal() -> list[dict]:
    rows=[]; base=Path("/sys/class/thermal")
    if not base.exists(): return rows
    for zone in sorted(base.glob("thermal_zone*")):
        kind=read_text(str(zone/"type")); raw=read_text(str(zone/"temp"))
        try:
            value=float(raw); c=value/1000.0 if abs(value)>250 else value
        except ValueError: continue
        rows.append({"zone":zone.name,"type":kind,"celsius":round(c,2)})
    return rows

def tool(name:str)->dict:
    path=shutil.which(name); return {"name":name,"present":bool(path),"path":path or ""}

def main()->int:
    STATE.mkdir(parents=True, exist_ok=True)
    mem=parse_meminfo(); usage=shutil.disk_usage(Path.home())
    tools=[tool(n) for n in ("python3","java","gradle","aapt2","clang","cmake","ninja","git","rish","godot","godot4")]
    candidates=[shutil.which("MNNConvert") or "",shutil.which("MNNV2Basic.out") or "",str(Path.home()/"MNN"),str(Path.home()/"workspace"/"MNN")]
    result={
      "schema":SCHEMA,"device":"primary-phone","runtimeTarget":"custom-creative-engine",
      "godotPolicy":"forge-only-not-delivery-runtime","ciUsed":False,"timestampEpoch":int(time.time()),
      "platform":platform.platform(),"machine":platform.machine(),"python":platform.python_version(),"cpuCount":os.cpu_count(),
      "memory":{"MemTotalBytes":mem.get("MemTotal",0),"MemAvailableBytes":mem.get("MemAvailable",0),"SwapTotalBytes":mem.get("SwapTotal",0),"SwapFreeBytes":mem.get("SwapFree",0)},
      "storage":{"totalBytes":usage.total,"usedBytes":usage.used,"freeBytes":usage.free},"thermal":thermal(),"tools":tools,
      "mnn":{"present":any(p and Path(p).exists() for p in candidates),"candidates":candidates},
    }
    result["nextAction"]="benchmark_existing_mnn_pixel_model" if result["mnn"]["present"] else "bootstrap_mnn_android_runtime"
    out=STATE/"probe.json"; out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2,sort_keys=True)); return 0

if __name__=="__main__": raise SystemExit(main())
