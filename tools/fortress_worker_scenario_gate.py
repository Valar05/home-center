#!/usr/bin/env python3
"""Deterministic acceptance gate for fresh Fortress worker scenario traces.

A candidate trace is JSONL with records:
  {"id":"scenario-id","actions":["..."],"claims":["..."]}

This gate intentionally does not grade prose quality. It checks that required semantic
contracts are explicitly represented and forbidden regressions are absent. Real worker
runs should emit compact machine-readable action/claim tags alongside normal receipts.
"""
from __future__ import annotations
import argparse, json, pathlib, sys


def load_jsonl(path: pathlib.Path):
    rows=[]
    for n,line in enumerate(path.read_text(encoding='utf-8').splitlines(),1):
        if not line.strip():
            continue
        try: rows.append(json.loads(line))
        except Exception as e: raise SystemExit(f"{path}:{n}: invalid json: {e}")
    return rows


def norm(s: str) -> str:
    return ' '.join(str(s).lower().split())


def contains(haystack: str, needle: str) -> bool:
    # Deliberately simple/stable. Training traces should state contracts explicitly.
    return norm(needle) in norm(haystack)


def evaluate(scenario, trace):
    text='\n'.join([*(trace.get('actions') or []), *(trace.get('claims') or [])])
    missing=[x for x in scenario.get('must',[]) if not contains(text,x)]
    forbidden=[x for x in scenario.get('must_not',[]) if contains(text,x)]
    return {
        'id': scenario['id'],
        'mode': scenario.get('mode'),
        'pass': not missing and not forbidden,
        'missing': missing,
        'forbidden_present': forbidden,
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--scenarios', default='os/training/fortress-fresh-worker-scenarios.jsonl')
    ap.add_argument('--traces', required=True)
    ap.add_argument('--report')
    args=ap.parse_args()
    scenarios={r['id']:r for r in load_jsonl(pathlib.Path(args.scenarios))}
    traces={r['id']:r for r in load_jsonl(pathlib.Path(args.traces))}
    results=[]
    for sid,scenario in scenarios.items():
        if sid not in traces:
            results.append({'id':sid,'mode':scenario.get('mode'),'pass':False,'missing_trace':True})
        else:
            results.append(evaluate(scenario,traces[sid]))
    unknown=sorted(set(traces)-set(scenarios))
    report={
        'schema':'fortress.worker-scenario-report.v1',
        'scenario_count':len(scenarios),
        'passed':sum(1 for r in results if r.get('pass')),
        'failed':sum(1 for r in results if not r.get('pass')),
        'unknown_trace_ids':unknown,
        'results':results,
    }
    out=json.dumps(report,indent=2,sort_keys=True)+'\n'
    if args.report: pathlib.Path(args.report).write_text(out,encoding='utf-8')
    print(out,end='')
    return 0 if report['failed']==0 and not unknown else 2

if __name__=='__main__':
    raise SystemExit(main())
