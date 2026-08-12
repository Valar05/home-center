#!/usr/bin/env python3
import argparse, json, shlex
import hands_router as hr

ALIASES={'phone':'primary-phone','pc':'THECAULDRON','computer':'THECAULDRON','laptop':'THECAULDRON'}

def compile_command(text):
 argv=shlex.split(text)
 if argv and argv[0].lower()=='hands': argv=argv[1:]
 if not argv: raise ValueError('usage: hands <phone|pc|target> <operation> [args]')
 raw_target=argv.pop(0)
 target=ALIASES.get(raw_target.lower(),raw_target)
 if not argv: raise ValueError('operation required')
 op=argv.pop(0).lower()
 phone={'observe':'phone.observe','home':'phone.home','back':'phone.back','recents':'phone.recents'}
 if target=='primary-phone' and op in phone and argv: raise ValueError(f'{op} takes no arguments')
 if target=='primary-phone' and op in phone: return target,[{'op':phone[op],'args':{}}]
 if target=='primary-phone' and op=='launch':
  if len(argv)!=1: raise ValueError('usage: hands phone launch PACKAGE')
  return target,[{'op':'phone.launch','args':{'package':argv[0]}}]
 if target=='primary-phone' and op in {'uri','open','open_uri'}:
  if not argv: raise ValueError('usage: hands phone uri URI [PACKAGE]')
  args={'uri':argv[0]}
  if len(argv)>1: args['package']=argv[1]
  if len(argv)>2: raise ValueError('usage: hands phone uri URI [PACKAGE]')
  return target,[{'op':'phone.open_uri','args':args}]
 if target=='primary-phone' and op=='text':
  if not argv: raise ValueError('usage: hands phone text TEXT')
  return target,[{'op':'phone.text','args':{'text':' '.join(argv)}}]
 if target=='THECAULDRON' and op=='status' and not argv: return target,[{'op':'system.status','args':{}}]
 if op=='exec':
  if not argv: raise ValueError('usage: hands <target> exec COMMAND')
  return target,[{'op':'shell.exec','args':{'command':' '.join(argv)}}]
 if op in hr.OPS:
  args={}
  if argv:
   try: args=json.loads(' '.join(argv))
   except json.JSONDecodeError as e: raise ValueError('explicit operations accept one JSON args object') from e
  return target,[{'op':op,'args':args}]
 raise ValueError(f'unknown bounded Hands operation: {op}')

def submit(text):
 target,steps=compile_command(text)
 return hr.enqueue('drew',target,steps)

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('text',nargs='+'); a=ap.parse_args()
 job=submit(' '.join(a.text)); print(json.dumps({'response':f"Hands queued {job['id']} -> {job['target']} ({len(job['steps'])} step(s))",'job':job},indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
