#!/usr/bin/env python3
"""Stable Termux ASMR command. Audio transport is Taildrop only."""
import argparse,json,os,re,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
STATE=Path.home()/'.local/state/asmr'
CATALOG=ROOT/'tools/campaigns/asmr_episodes.json'
def run(script,*args):
 return subprocess.call([sys.executable,str(HERE/script),*args])
def catalog():
 return json.loads(CATALOG.read_text(encoding='utf-8'))
def current():
 try:return json.loads((STATE/'current.json').read_text())
 except FileNotFoundError:return {}
def select(row):
 STATE.mkdir(parents=True,exist_ok=True)
 t=STATE/'current.tmp';t.write_text(json.dumps(row),encoding='utf-8');os.replace(t,STATE/'current.json')
def install():
 # Symlink into Termux PATH, never overwrite another command.
 dest=Path(os.environ.get('PREFIX','/data/data/com.termux/files/usr'))/'bin'/'asmr'
 if dest.exists() or dest.is_symlink():
  if dest.is_symlink() and dest.resolve()==Path(__file__).resolve():return 0
  raise RuntimeError('asmr command already exists; refusing replacement')
 os.chmod(__file__,0o755);dest.symlink_to(Path(__file__).resolve())
 print('ASMR_COMMAND='+str(dest));return 0
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('verb',choices=['install','update','list','clone','clone-status','render','status','resume','stop','drop','drop-status','verify','receipt','doctor'])
 p.add_argument('name',nargs='?')
 p.add_argument('--received',type=Path)
 p.add_argument('--resend',action='store_true')
 a=p.parse_args()
 if a.resend and a.verb!='drop':p.error('--resend requires drop')
 if a.received and a.verb!='verify':p.error('--received requires verify')
 if a.verb=='install':return install()
 if a.verb=='update':
  env=dict(os.environ,GIT_LFS_SKIP_SMUDGE='1')
  if subprocess.check_output(['git','-C',str(ROOT),'status','--porcelain','--untracked-files=no'],text=True).strip():raise RuntimeError('Tracked working tree changes; update blocked')
  return subprocess.call(['git','-C',str(ROOT),'pull','--ff-only'],env=env)
 if a.verb=='list':
  for k,v in catalog().items():print(k+'  '+v['episode'])
  print('clone quiet-drew  (send deep-clean WAV using Taildrop first)')
  return 0
 if a.verb in ('clone','clone-status'):
  if a.name not in (None,'quiet-drew'):p.error('Known clone: quiet-drew')
  select({'kind':'clone','name':'quiet-drew'})
  return run('asmr_quiet_drew_phone.py','start' if a.verb=='clone' else 'status')
 if a.verb=='doctor':return run('ritsu_asmr_phone.py','doctor')
 if a.verb=='receipt':
  row=current()
  path=Path.home()/'.local/state'/('asmr-quiet-drew' if row.get('kind')=='clone' else 'ritsu-asmr')/'latest.txt'
  print(path.read_text(encoding='utf-8'));return 0
 row=current()
 if a.name:
  if a.name not in catalog():p.error('Unknown episode; use asmr list')
  row={'kind':'episode','name':a.name,**catalog()[a.name]}
 if a.verb=='status' and row.get('kind')=='clone' and not a.name:return run('asmr_quiet_drew_phone.py','status')
 if a.verb=='render' and not a.name:p.error('Use asmr render NAME; asmr list shows names')
 if row.get('kind')!='episode':p.error('Select an episode with asmr render NAME or specify NAME')
 ep=row['episode']
 if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',ep):raise RuntimeError('Invalid catalog episode')
 select(row)
 args=['--episode',ep]
 if a.verb=='render':return run('ritsu_asmr_phone.py','start',*args,'--repo-transcript',row['commit'],row['path'])
 if a.resend:args+=['--resend']
 if a.received:args+=['--received',str(a.received)]
 return run('ritsu_asmr_phone.py',a.verb,*args)
if __name__=='__main__':
 try:sys.exit(main())
 except (OSError,ValueError,RuntimeError) as e:print('ASMR_BLOCKED='+str(e),file=sys.stderr);sys.exit(2)
