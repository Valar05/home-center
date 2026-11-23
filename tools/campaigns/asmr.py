#!/usr/bin/env python3
"""Stable Termux ASMR command. Audio transport is Taildrop only."""
import argparse,json,os,re,shlex,shutil,subprocess,sys,tempfile
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
 # Shared Android storage is noexec. Execute a private Termux shell stub instead.
 prefix=Path(os.environ.get('PREFIX','/data/data/com.termux/files/usr'))
 dest=prefix/'bin'/'asmr'
 source=Path(__file__).resolve()
 marker='# HomeCenter ASMR launcher v1\n'
 body='#!'+str(prefix/'bin'/'sh')+'\n'+marker+'exec '+shlex.quote(str(prefix/'bin'/'python3'))+' '+shlex.quote(str(source))+' "$@"\n'
 if dest.is_symlink():
  if dest.resolve()!=source:raise RuntimeError('Unrelated asmr symlink; refusing replacement')
 elif dest.exists():
  if not dest.is_file() or marker not in dest.read_text(encoding='utf-8'):raise RuntimeError('Unrelated asmr command; refusing replacement')
 with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=dest.parent,prefix='.asmr-',delete=False) as f:
  tmp=Path(f.name);f.write(body)
 try:
  tmp.chmod(0o755);os.replace(tmp,dest)
 finally:tmp.unlink(missing_ok=True)
 if dest.is_symlink() or not os.access(dest,os.X_OK) or dest.read_text()!=body:raise RuntimeError('Launcher verification failed')
 print('ASMR_COMMAND='+str(dest));return 0
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('verb',choices=['install','update','list','clone','clone-status','render','status','resume','stop','drop','drop-status','verify','receipt','doctor','chatterbox','chatterbox-status','chatterbox-dry','chatterbox-deep'])
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
  print('clone quiet-drew  (existing Quiet Drew V3)')
  print('clone growl-ab    (two denoising variants; Taildrop both refs first)')
  print('chatterbox        (separate engine; pinned supplied reference; generates dry and minus-two)')
  print('chatterbox-dry / chatterbox-deep  (select a Chatterbox output for drop/verify)')
  return 0
 if a.verb in ('clone','clone-status'):
  if a.name not in (None,'quiet-drew','growl-ab'):p.error('Known clones: quiet-drew, growl-ab')
  key=a.name or 'quiet-drew'
  select({'kind':'clone','name':key})
  script='asmr_growl_ab_phone.py' if key=='growl-ab' else 'asmr_quiet_drew_phone.py'
  return run(script,'start' if a.verb=='clone' else 'status')
 if a.verb=='doctor':return run('ritsu_asmr_phone.py','doctor')
 if a.verb in ('chatterbox','chatterbox-status','chatterbox-dry','chatterbox-deep'):
  previous=current()
  chosen=(previous.get('episode') if a.verb=='chatterbox-status' and previous.get('kind')=='chatterbox'
          else 'CHATTERBOX_GROWL_DRY_V1' if a.verb=='chatterbox-dry'
          else 'CHATTERBOX_GROWL_DEEP_V1')
  select({'kind':'chatterbox','episode':chosen,'name':'chatterbox'})
  if a.verb in ('chatterbox','chatterbox-status'):
   return run('chatterbox_growl_phone.py','start' if a.verb=='chatterbox' else 'status')
  print('ASMR_SELECTED='+chosen+'; use asmr drop or asmr verify once rendered')
  return 0
 if a.verb=='receipt':
  row=current()
  path=Path.home()/'.local/state'/('chatterbox-growl' if row.get('kind')=='chatterbox' else 'asmr-growl-ab' if row.get('name')=='growl-ab' and row.get('kind')=='clone' else 'asmr-quiet-drew' if row.get('kind')=='clone' else 'ritsu-asmr')/'latest.txt'
  print(path.read_text(encoding='utf-8'));return 0
 row=current()
 if a.name:
  if a.name not in catalog():p.error('Unknown episode; use asmr list')
  row={'kind':'episode','name':a.name,**catalog()[a.name]}
 if a.verb=='status' and row.get('kind')=='chatterbox' and not a.name:return run('chatterbox_growl_phone.py','status')
 if a.verb=='resume' and row.get('kind')=='chatterbox' and not a.name:return run('chatterbox_growl_phone.py','resume')
 if a.verb=='stop' and row.get('kind')=='chatterbox' and not a.name:raise RuntimeError('Chatterbox stop is not implemented; no unrelated task touched')
 if a.verb=='status' and row.get('kind')=='clone' and not a.name:
  return run('asmr_growl_ab_phone.py' if row.get('name')=='growl-ab' else 'asmr_quiet_drew_phone.py','status')
 if a.verb=='render' and not a.name:p.error('Use asmr render NAME; asmr list shows names')
 if row.get('kind') not in ('episode','chatterbox'):p.error('Select an episode with asmr render NAME or use asmr chatterbox')
 if row.get('kind')=='chatterbox' and a.verb=='render':p.error('Chatterbox render starts with asmr chatterbox, not asmr render')
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
