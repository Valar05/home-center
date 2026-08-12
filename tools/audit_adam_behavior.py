#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re
from pathlib import Path

TEXT_EXT={'.md','.txt','.json','.js','.mjs','.cjs','.ts','.tsx','.py','.sh','.ps1','.yml','.yaml','.toml','.ini','.html','.css'}
SKIP={'.git','node_modules','.venv','venv','__pycache__'}
SURFACE=re.compile(r'\b(adam|codex|worker|chatgpt|venice|judg(?:e)?ment jar|fortress|computer hands|phone hands|chromium throne|handoff)\b',re.I)
STOP=re.compile(r'(stop permission|consult.{0,40}venice|venice.{0,40}(stop|continue)|judg(?:e)?ment jar.{0,80}(stop|continue))',re.I|re.S)
CONTINUE=re.compile(r'(continue immediately|resume.{0,40}(mission|commission)|next action|retry|requeue|keep working)',re.I|re.S)
EVIDENCE=re.compile(r'(receipt|readback|post-state|native[- ]medium|evidence|accepted|delivered|deployed|callable)',re.I)
HUMAN=re.compile(r'(ask drew|ask the user|user must|manual|handoff|operator[- ]only)',re.I)
BODY=re.compile(r'(computer hands|phone hands|browser nerve|chromium throne|shell\.exec|worker)',re.I)
PROMPTISH=re.compile(r'(rule|skill|prompt|bootstrap|worker profile|contract|operator|campaign|starts_here|readme)',re.I)


def files(root:Path):
    for p in root.rglob('*'):
        if not p.is_file() or p.suffix.lower() not in TEXT_EXT: continue
        if any(part in SKIP for part in p.parts): continue
        yield p


def score(item):
    # Hunger: operator friction × recurrence × reliability gain × confidence × reversibility / (cost × risk)
    sev=item['severity']
    base={'critical':9,'high':6,'medium':3,'low':1}[sev]
    recurrence=2 if item['category'] in {'stop-gate','human-fallback','evidence-boundary'} else 1
    reliability=2 if item['category'] in {'stop-gate','human-fallback'} else 1.5
    confidence=1 if item['confidence']=='high' else .65
    reversibility=1.25
    cost=1
    risk=1.1 if item['category']=='stop-gate' else 1
    return round(base*recurrence*reliability*confidence*reversibility/(cost*risk),2)


def audit(root:Path):
    scanned=0; relevant=0; findings=[]; surfaces=[]
    for p in files(root):
        scanned+=1
        rel=str(p.relative_to(root)).replace('\\','/')
        try: text=p.read_text(encoding='utf-8',errors='ignore')
        except Exception: continue
        if not SURFACE.search(text): continue
        relevant+=1
        low=rel.lower(); promptish=bool(PROMPTISH.search(low)) or '/skills/' in low or low.startswith('skills/') or '.continue/' in low
        has_stop=bool(STOP.search(text)); has_continue=bool(CONTINUE.search(text)); has_evidence=bool(EVIDENCE.search(text)); has_human=bool(HUMAN.search(text)); has_body=bool(BODY.search(text))
        surfaces.append({'path':rel,'stopGate':has_stop,'continuation':has_continue,'evidence':has_evidence,'humanFallbackLanguage':has_human,'bodyAware':has_body,'promptish':promptish})
        if promptish and not has_stop:
            findings.append({'path':rel,'category':'stop-gate','severity':'high','confidence':'medium','reason':'Behavior/prompt surface references Adam/worker/Fortress behavior but contains no detectable Venice/Jar stop-or-continue gate.'})
        if has_human and has_body and not re.search(r'(exhaust|before asking|final fallback|operator-only|genuine human)',text,re.I):
            findings.append({'path':rel,'category':'human-fallback','severity':'high','confidence':'medium','reason':'Surface contains both worker/body behavior and manual/user handoff language without an obvious existing-body exhaustion guard.'})
        if promptish and re.search(r'\b(done|complete|finished|stop)\b',text,re.I) and not has_evidence:
            findings.append({'path':rel,'category':'evidence-boundary','severity':'medium','confidence':'medium','reason':'Behavior surface discusses terminal state but no detectable receipt/readback/native evidence vocabulary.'})
        if promptish and has_stop and not has_continue:
            findings.append({'path':rel,'category':'continuation','severity':'high','confidence':'medium','reason':'Stop/review semantics are present but no detectable immediate continuation/resume behavior follows denial or incomplete work.'})
    for f in findings: f['hungerScore']=score(f)
    findings.sort(key=lambda x:(-x['hungerScore'],x['path']))
    return {'schema':'fortress.adam-behavior-audit.v1','scannedTextFiles':scanned,'relevantBehaviorFiles':relevant,'findingCount':len(findings),'findings':findings,'surfaces':surfaces}


def md(report):
    out=['# Adam / Codex / Worker Behavior Audit','',f"Scanned text files: **{report['scannedTextFiles']}**",f"Behavior-relevant files: **{report['relevantBehaviorFiles']}**",f"Advisory findings: **{report['findingCount']}**",'', '## Hunger-ranked findings','']
    for i,f in enumerate(report['findings'][:200],1):
        out.append(f"{i}. **{f['hungerScore']} — {f['severity'].upper()} — {f['category']}** — `{f['path']}` — {f['reason']}")
    out += ['', '## Interpretation', '', 'This is an adversarial static audit, not acceptance. A finding means the file deserves human/Jar review; absence of a finding does not prove correct behavior. Hunger ordering favors recurring operator-friction and reliability defects first.']
    return '\n'.join(out)+'\n'


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',default='.'); ap.add_argument('--json'); ap.add_argument('--markdown'); args=ap.parse_args()
    report=audit(Path(args.root).resolve())
    if args.json: Path(args.json).write_text(json.dumps(report,indent=2),encoding='utf-8')
    if args.markdown: Path(args.markdown).write_text(md(report),encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('schema','scannedTextFiles','relevantBehaviorFiles','findingCount')},indent=2))
    for f in report['findings'][:20]: print(f"{f['hungerScore']:>6} {f['severity']:<8} {f['category']:<18} {f['path']}")

if __name__=='__main__': main()
