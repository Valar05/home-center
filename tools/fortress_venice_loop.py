#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = Path(os.path.expanduser(os.getenv('HC_FORTRESS_STATE', '~/.local/state/home-center/fortress-resume')))
VLAD_REVIEW_INBOX = Path(os.path.expanduser(os.getenv('HC_VLAD_REVIEW_INBOX', '~/.local/state/home-center/vlad-swarm/review-inbox')))
STATE.mkdir(parents=True, exist_ok=True)
MAX_EVIDENCE_BYTES = 64 * 1024


def run(cmd, *, cwd=ROOT, timeout=240):
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=timeout)

def read_json(path: Path):
    try:return json.loads(path.read_text(encoding='utf-8'))
    except Exception:return {}

def evidence_text(path: str) -> str:
    p=Path(path);raw=p.read_bytes()
    if len(raw)>MAX_EVIDENCE_BYTES:raise ValueError(f'evidence file exceeds {MAX_EVIDENCE_BYTES} bytes: {p}')
    obj=json.loads(raw.decode('utf-8'))
    if obj.get('schema')!='fortress.phone-evidence.v2' or obj.get('ok') is not True:raise ValueError('runtime evidence is missing, invalid, or not successful')
    return json.dumps(obj, indent=2, sort_keys=True)

def status_porcelain() -> str:return run(['git','status','--porcelain']).stdout.strip()
def emit(obj, rc):print(json.dumps(obj, indent=2, sort_keys=True));return rc

def push_repair(row):
    push=run(['git','push','origin','HEAD:main'],timeout=180);row['repairPush']={'rc':push.returncode,'stdout':push.stdout[-3000:],'stderr':push.stderr[-3000:]};return push.returncode==0

def refresh_evidence(path: str, row: dict) -> bool:
    p=Path(path);refresh=run(['bash','tools/fortress_refresh_phone_evidence.sh',str(p)],timeout=1800);row['runtimeReverify']={'rc':refresh.returncode,'stdout':refresh.stdout[-6000:],'stderr':refresh.stderr[-6000:]}
    if refresh.returncode != 0:return False
    try:evidence_text(path)
    except Exception as exc:row['runtimeReverify']['validationError']=str(exc);return False
    return True

def head_sha() -> str:return run(['git','rev-parse','HEAD']).stdout.strip()
def review_paths(head: str):
    VLAD_REVIEW_INBOX.mkdir(parents=True,exist_ok=True)
    stem=f'fortress-loop-{head}'
    return VLAD_REVIEW_INBOX/f'{stem}.json',VLAD_REVIEW_INBOX/f'{stem}.review.txt'
def ensure_review_request(base: str, head: str, acceptance: str, evidence: str):
    job,review=review_paths(head)
    payload={
        'schema':'venice-review-queue-v2','repo':str(ROOT),'base':base,'head':head,
        'acceptance':acceptance+'\n\nRUNTIME EVIDENCE (fresh phone-produced, bounded):\n'+evidence,
        'timeout':600,'reviewerMode':'judgment_jar_emulation','localVenice':False,
        'reviewTextPath':str(review),'reviewer':'chatgpt-venice-judgment-jar','state':'awaiting_chatgpt_judgment_jar',
    }
    if not job.exists():job.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    return job,review


def main():
    ap = argparse.ArgumentParser(description='Fortress Venice -> repair -> phone reverify -> Venice completion loop')
    ap.add_argument('--base', required=True)
    ap.add_argument('--head', default='HEAD')
    ap.add_argument('--acceptance', required=True)
    ap.add_argument('--evidence-file', required=True)
    ap.add_argument('--max-rounds', type=int, default=0, help='0 means continue until Venice PASS or a real execution boundary')
    args = ap.parse_args()
    if args.max_rounds < 0:raise SystemExit('max-rounds must be >= 0; 0 means unlimited')
    try:evidence=evidence_text(args.evidence_file)
    except Exception as exc:return emit({'schema':'fortress-venice-loop-v5','ok':False,'boundary':'runtime_evidence_invalid','error':str(exc)},11)
    dirty_before = status_porcelain()
    if dirty_before:return emit({'schema':'fortress-venice-loop-v5','ok':False,'boundary':'preexisting_dirty_tree_requires_preservation','dirty':dirty_before.splitlines()[:100]},10)

    session = str(int(time.time()));history=[];round_no=0
    while True:
        round_no += 1
        if args.max_rounds and round_no > args.max_rounds:return emit({'schema':'fortress-venice-loop-v5','ok':False,'boundary':'operator_configured_round_cap_reached','base':args.base,'head':args.head,'rounds':history},4)
        try:evidence=evidence_text(args.evidence_file)
        except Exception as exc:return emit({'schema':'fortress-venice-loop-v5','ok':False,'boundary':'runtime_evidence_invalid','error':str(exc),'rounds':history},11)
        current_head=head_sha();job,review_text=ensure_review_request(args.base,current_head,args.acceptance,evidence)
        if not review_text.is_file():
            return emit({'schema':'fortress-venice-loop-v5','ok':False,'boundary':'awaiting_chatgpt_judgment_jar','base':args.base,'head':current_head,'reviewJob':str(job),'reviewTextPath':str(review_text),'rounds':history},14)

        review_acceptance = args.acceptance + '\n\nRUNTIME EVIDENCE (fresh phone-produced, bounded):\n' + evidence
        receipt = STATE / f'{session}.venice.{round_no}.json'
        review = run(['bash','tools/venice_review_selfheal.sh','--repo',str(ROOT),'--base',args.base,'--head',current_head,'--acceptance',review_acceptance,'--review-text-file',str(review_text),'--reviewer','chatgpt-venice-judgment-jar','--receipt',str(receipt)], timeout=300)
        data = read_json(receipt);row = {'round': round_no, 'reviewRc': review.returncode, 'receipt': str(receipt), 'venice': data, 'reviewTextPath':str(review_text)};history.append(row)
        if data.get('externalReviewGateSatisfied') is True:return emit({'schema':'fortress-venice-loop-v5','ok':True,'base':args.base,'head':current_head,'evidenceFile':args.evidence_file,'rounds':history}, 0)
        if data.get('directive') == 'HALT_REQUIRED':return emit({'schema':'fortress-venice-loop-v5','ok':False,'boundary':'venice_halt_required','base':args.base,'head':current_head,'rounds':history},15)
        if data.get('directive') != 'CONTINUE_REQUIRED':return emit({'schema':'fortress-venice-loop-v5','ok':False,'boundary':'venice_directive_invalid_or_missing','base':args.base,'head':current_head,'rounds':history},16)

        findings = data.get('findings') or ['Venice CONTINUE_REQUIRED did not include parsed findings; inspect the review receipt.']
        prompt = ('FORTRESS ONLINE repair round. Apply Venice blocking critique to the current repository without changing the commission boundary. Do not redesign or substitute tools. Run relevant local tests. Do not stop merely to report the critique; edit the code. Runtime evidence is supplied for diagnosis; never fabricate or edit runtime receipts to make a failure pass.\n\n'+f'Acceptance:\n{args.acceptance}\n\nRuntime evidence:\n{evidence}\n\nVenice findings:\n- ' + '\n- '.join(map(str, findings)))
        head_before = head_sha();repair = run([sys.executable,'tools/adam.py','continue',prompt,'--cwd',str(ROOT),'--timeout','300'], timeout=330);dirty_after = status_porcelain();head_after_repair = head_sha()
        row['repair']={'rc':repair.returncode,'stdout':repair.stdout[-4000:],'stderr':repair.stderr[-4000:],'headBefore':head_before,'headAfterRepair':head_after_repair,'dirtyAfterRepair':dirty_after.splitlines()[:100]}
        if repair.returncode != 0:return emit({'schema':'fortress-venice-loop-v5','ok':False,'boundary':'repair_lane_unavailable_or_failed','base':args.base,'head':current_head,'rounds':history},2)
        if head_before == head_after_repair and not dirty_after:return emit({'schema':'fortress-venice-loop-v5','ok':False,'boundary':'repair_lane_made_no_change','base':args.base,'head':current_head,'rounds':history},3)
        if dirty_after:
            tests = run(['bash','tools/run_fortress_local_contracts.sh'], timeout=300);row['localContracts']={'rc':tests.returncode,'stdout':tests.stdout[-4000:],'stderr':tests.stderr[-4000:]}
            if tests.returncode != 0:return emit({'schema':'fortress-venice-loop-v5','ok':False,'boundary':'repair_failed_local_contracts','base':args.base,'head':current_head,'rounds':history},5)
            changed = [line[3:] for line in dirty_after.splitlines() if len(line) >= 4];forbidden = [p for p in changed if p.startswith('.github/workflows/') or Path(p).name.lower() in {'.env','credentials.json','id_rsa','id_ed25519'}]
            if forbidden:row['forbiddenRepairPaths']=forbidden;return emit({'schema':'fortress-venice-loop-v5','ok':False,'boundary':'repair_touched_forbidden_paths','rounds':history},13)
            add=run(['git','add','-A'])
            if add.returncode != 0:row['gitAdd']={'rc':add.returncode,'stderr':add.stderr[-2000:]};return emit({'schema':'fortress-venice-loop-v5','ok':False,'boundary':'repair_commit_stage_failed','rounds':history},6)
            commit=run(['git','commit','-m',f'Fortress: apply Venice critique round {round_no}']);row['repairCommit']={'rc':commit.returncode,'stdout':commit.stdout[-3000:],'stderr':commit.stderr[-3000:]}
            if commit.returncode != 0:return emit({'schema':'fortress-venice-loop-v5','ok':False,'boundary':'repair_commit_failed','rounds':history},7)
            if not push_repair(row):return emit({'schema':'fortress-venice-loop-v5','ok':False,'boundary':'repair_push_rejected','rounds':history},8)
        elif head_before != head_after_repair:
            if not push_repair(row):return emit({'schema':'fortress-venice-loop-v5','ok':False,'boundary':'repair_push_rejected','rounds':history},8)
        row['reviewHeadNext']=head_sha()
        if not refresh_evidence(args.evidence_file,row):return emit({'schema':'fortress-venice-loop-v5','ok':False,'boundary':'runtime_reverify_failed_after_repair','rounds':history},12)

if __name__ == '__main__': raise SystemExit(main())
