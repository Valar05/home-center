#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = Path(os.path.expanduser(os.getenv('HC_FORTRESS_STATE', '~/.local/state/home-center/fortress-resume')))
STATE.mkdir(parents=True, exist_ok=True)
MAX_EVIDENCE_BYTES = 64 * 1024


def run(cmd, *, cwd=ROOT, timeout=240):
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=timeout)


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


def evidence_text(path: str) -> str:
    if not path:
        return ''
    p=Path(path)
    raw=p.read_bytes()
    if len(raw)>MAX_EVIDENCE_BYTES:
        raise ValueError(f'evidence file exceeds {MAX_EVIDENCE_BYTES} bytes: {p}')
    obj=json.loads(raw.decode('utf-8'))
    if obj.get('schema')!='fortress.phone-evidence.v1' or obj.get('ok') is not True:
        raise ValueError('runtime evidence is missing, invalid, or not successful')
    return json.dumps(obj, indent=2, sort_keys=True)


def status_porcelain() -> str:
    return run(['git','status','--porcelain']).stdout.strip()


def emit(obj, rc):
    print(json.dumps(obj, indent=2, sort_keys=True))
    return rc


def push_repair(row):
    push=run(['git','push','origin','HEAD:main'],timeout=180)
    row['repairPush']={'rc':push.returncode,'stdout':push.stdout[-3000:],'stderr':push.stderr[-3000:]}
    return push.returncode==0


def main():
    ap = argparse.ArgumentParser(description='Fortress Venice -> repair -> Venice completion loop')
    ap.add_argument('--base', required=True)
    ap.add_argument('--head', default='HEAD')
    ap.add_argument('--acceptance', required=True)
    ap.add_argument('--evidence-file', required=True)
    ap.add_argument('--max-rounds', type=int, default=4)
    args = ap.parse_args()

    if args.max_rounds < 1 or args.max_rounds > 8:
        raise SystemExit('max-rounds must be 1..8')
    try:
        evidence=evidence_text(args.evidence_file)
    except Exception as exc:
        return emit({'schema':'fortress-venice-loop-v2','ok':False,'boundary':'runtime_evidence_invalid','error':str(exc)},11)
    dirty_before = status_porcelain()
    if dirty_before:
        return emit({
            'schema':'fortress-venice-loop-v2','ok':False,
            'boundary':'preexisting_dirty_tree_requires_preservation',
            'dirty':dirty_before.splitlines()[:100],
        }, 10)

    review_acceptance = args.acceptance + '\n\nRUNTIME EVIDENCE (phone-produced, bounded):\n' + evidence
    session = str(int(time.time()))
    history = []
    for round_no in range(1, args.max_rounds + 1):
        receipt = STATE / f'{session}.venice.{round_no}.json'
        review = run([
            'bash', 'tools/venice_review_selfheal.sh',
            '--repo', str(ROOT), '--base', args.base, '--head', args.head,
            '--acceptance', review_acceptance, '--receipt', str(receipt),
        ], timeout=300)
        data = read_json(receipt)
        row = {'round': round_no, 'reviewRc': review.returncode, 'receipt': str(receipt), 'venice': data}
        history.append(row)
        if data.get('externalReviewGateSatisfied') is True:
            return emit({'schema':'fortress-venice-loop-v2','ok':True,'base':args.base,'head':args.head,'evidenceFile':args.evidence_file,'rounds':history}, 0)

        findings = data.get('findings') or ['Venice review failed without parsed findings. Inspect reviewText and deterministicChecks.']
        prompt = (
            'FORTRESS ONLINE repair round. Apply Venice blocking critique to the current repository without changing the commission boundary. '
            'Do not redesign or substitute tools. Run relevant local tests. Do not stop merely to report the critique; edit the code. '
            'Runtime evidence is supplied for diagnosis; do not fabricate or edit runtime receipts to make a failure pass.\n\n'
            f'Acceptance:\n{args.acceptance}\n\nRuntime evidence:\n{evidence}\n\nVenice findings:\n- ' + '\n- '.join(map(str, findings))
        )
        head_before = run(['git','rev-parse','HEAD']).stdout.strip()
        repair = run([sys.executable, 'tools/adam.py', 'continue', prompt, '--cwd', str(ROOT), '--timeout', '300'], timeout=330)
        dirty_after = status_porcelain()
        head_after_repair = run(['git','rev-parse','HEAD']).stdout.strip()
        row['repair'] = {
            'rc':repair.returncode,'stdout':repair.stdout[-4000:],'stderr':repair.stderr[-4000:],
            'headBefore':head_before,'headAfterRepair':head_after_repair,
            'dirtyAfterRepair':dirty_after.splitlines()[:100],
        }
        if repair.returncode != 0:
            return emit({
                'schema':'fortress-venice-loop-v2','ok':False,'boundary':'repair_lane_unavailable_or_failed',
                'base':args.base,'head':args.head,'rounds':history,
            }, 2)
        if head_before == head_after_repair and not dirty_after:
            return emit({
                'schema':'fortress-venice-loop-v2','ok':False,'boundary':'repair_lane_made_no_change',
                'base':args.base,'head':args.head,'rounds':history,
            }, 3)

        if dirty_after:
            tests = run(['bash','tools/run_fortress_local_contracts.sh'], timeout=300)
            row['localContracts'] = {'rc':tests.returncode,'stdout':tests.stdout[-4000:],'stderr':tests.stderr[-4000:]}
            if tests.returncode != 0:
                return emit({
                    'schema':'fortress-venice-loop-v2','ok':False,'boundary':'repair_failed_local_contracts',
                    'base':args.base,'head':args.head,'rounds':history,
                }, 5)
            add = run(['git','add','-A'])
            if add.returncode != 0:
                row['gitAdd']={'rc':add.returncode,'stderr':add.stderr[-2000:]}
                return emit({'schema':'fortress-venice-loop-v2','ok':False,'boundary':'repair_commit_stage_failed','rounds':history}, 6)
            commit = run(['git','commit','-m',f'Fortress: apply Venice critique round {round_no}'])
            row['repairCommit']={'rc':commit.returncode,'stdout':commit.stdout[-3000:],'stderr':commit.stderr[-3000:]}
            if commit.returncode != 0:
                return emit({'schema':'fortress-venice-loop-v2','ok':False,'boundary':'repair_commit_failed','rounds':history}, 7)
            if not push_repair(row):
                return emit({'schema':'fortress-venice-loop-v2','ok':False,'boundary':'repair_push_rejected','rounds':history},8)
        elif head_before != head_after_repair:
            if not push_repair(row):
                return emit({'schema':'fortress-venice-loop-v2','ok':False,'boundary':'repair_push_rejected','rounds':history},8)

        row['reviewHeadNext'] = run(['git','rev-parse','HEAD']).stdout.strip()

    return emit({
        'schema':'fortress-venice-loop-v2','ok':False,'boundary':'venice_still_failing_after_bounded_repairs',
        'base':args.base,'head':args.head,'rounds':history,
    }, 4)


if __name__ == '__main__':
    raise SystemExit(main())
