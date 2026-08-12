#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = Path(os.path.expanduser(os.getenv('HC_FORTRESS_STATE', '~/.local/state/home-center/fortress-resume')))
STATE.mkdir(parents=True, exist_ok=True)


def run(cmd, *, cwd=ROOT, timeout=240):
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=timeout)


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


def main():
    ap = argparse.ArgumentParser(description='Fortress Venice -> repair -> Venice completion loop')
    ap.add_argument('--base', required=True)
    ap.add_argument('--head', default='HEAD')
    ap.add_argument('--acceptance', required=True)
    ap.add_argument('--max-rounds', type=int, default=4)
    args = ap.parse_args()

    if args.max_rounds < 1 or args.max_rounds > 8:
        raise SystemExit('max-rounds must be 1..8')

    session = str(int(time.time()))
    history = []
    for round_no in range(1, args.max_rounds + 1):
        receipt = STATE / f'{session}.venice.{round_no}.json'
        review = run([
            'bash', 'tools/run_venice_review_selfheal.sh',
            '--repo', str(ROOT), '--base', args.base, '--head', args.head,
            '--acceptance', args.acceptance, '--receipt', str(receipt),
        ], timeout=300)
        data = read_json(receipt)
        history.append({'round': round_no, 'reviewRc': review.returncode, 'receipt': str(receipt), 'venice': data})
        if data.get('externalReviewGateSatisfied') is True:
            out = {'schema':'fortress-venice-loop-v1','ok':True,'base':args.base,'head':args.head,'rounds':history}
            print(json.dumps(out, indent=2, sort_keys=True))
            return 0

        findings = data.get('findings') or ['Venice review failed without parsed findings. Inspect reviewText and deterministicChecks.']
        prompt = (
            'FORTRESS ONLINE repair round. Apply Venice blocking critique to the current repository without changing the commission boundary. '
            'Do not redesign or substitute tools. After editing, run the relevant local tests and leave the working tree ready for another Venice review.\n\n'
            f'Acceptance:\n{args.acceptance}\n\nVenice findings:\n- ' + '\n- '.join(map(str, findings))
        )
        before = run(['git','rev-parse','HEAD']).stdout.strip()
        repair = run([sys.executable, 'tools/adam.py', 'continue', prompt, '--cwd', str(ROOT), '--timeout', '300'], timeout=330)
        after = run(['git','rev-parse','HEAD']).stdout.strip()
        dirty = bool(run(['git','status','--porcelain']).stdout.strip())
        history[-1]['repair'] = {'rc':repair.returncode,'stdout':repair.stdout[-4000:],'stderr':repair.stderr[-4000:],'headBefore':before,'headAfter':after,'dirtyAfter':dirty}
        if repair.returncode != 0:
            out = {
                'schema':'fortress-venice-loop-v1','ok':False,'boundary':'repair_lane_unavailable_or_failed',
                'base':args.base,'head':args.head,'rounds':history,
            }
            print(json.dumps(out, indent=2, sort_keys=True))
            return 2
        if before == after and not dirty:
            out = {
                'schema':'fortress-venice-loop-v1','ok':False,'boundary':'repair_lane_made_no_change',
                'base':args.base,'head':args.head,'rounds':history,
            }
            print(json.dumps(out, indent=2, sort_keys=True))
            return 3

    out = {'schema':'fortress-venice-loop-v1','ok':False,'boundary':'venice_still_failing_after_bounded_repairs','base':args.base,'head':args.head,'rounds':history}
    print(json.dumps(out, indent=2, sort_keys=True))
    return 4


if __name__ == '__main__':
    raise SystemExit(main())
