import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from google.api_core.exceptions import PreconditionFailed
from google.cloud import firestore, storage
from PIL import Image, ImageDraw

PROJECT = os.environ.get('GOOGLE_CLOUD_PROJECT') or os.environ.get('GCLOUD_PROJECT')
BUCKET = os.environ.get('HOME_CENTER_ARTIFACT_BUCKET', 'home-center-generated')
BLENDER = os.environ.get('BLENDER_BIN', '/usr/local/bin/blender')
TIMEOUT = min(int(os.environ.get('BLENDER_WORKSPACE_TIMEOUT_SECONDS', '1700')), 1750)
DB = firestore.Client(project=PROJECT)
GCS = storage.Client(project=PROJECT)
LOCK = threading.Lock()

def now(): return datetime.now(timezone.utc).isoformat()
def digest(path):
    h=hashlib.sha256(); size=0
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk); size += len(chunk)
    return h.hexdigest(), size

def download(identity, destination):
    GCS.bucket(identity['bucket']).blob(identity['objectName']).download_to_filename(destination)
    sha,size=digest(destination)
    if sha != identity['sha256'] or size != int(identity['byteLength']): raise RuntimeError('immutable input readback mismatch')

def upload(path, object_name, role):
    sha,size=digest(path); blob=GCS.bucket(BUCKET).blob(object_name)
    try: blob.upload_from_filename(path, if_generation_match=0, content_type=content_type(path.name))
    except PreconditionFailed:
        tmp=Path(path.parent)/('readback-'+path.name); blob.download_to_filename(tmp); rsha,rsize=digest(tmp); tmp.unlink()
        if (sha,size)!=(rsha,rsize): raise RuntimeError('immutable output collision')
    return {'role':role,'name':path.name,'mediaType':content_type(path.name),'byteLength':size,'sha256':sha,'bucket':BUCKET,'objectName':object_name,'storageRef':f'gs://{BUCKET}/{object_name}','immutable':True}

def content_type(name):
    return {'.blend':'application/x-blender','.glb':'model/gltf-binary','.json':'application/json','.png':'image/png','.mp4':'video/mp4','.log':'text/plain'}.get(Path(name).suffix.lower(),'application/octet-stream')

def classify(name):
    if name=='scene.blend': return 'blend'
    if name=='scene.glb': return 'glb'
    if name=='inspection.json': return 'inspection'
    if name=='validation.json': return 'validation'
    if name=='contact-sheet.png': return 'contactSheet'
    if name=='animation-preview.mp4': return 'animationPreview'
    if 'wire' in name: return 'wireframe'
    if 'raking' in name: return 'rakingLight'
    if name.endswith('.png'): return 'reviewImage'
    return 'artifact'

def contact_sheet(directory):
    images=sorted([p for p in Path(directory).glob('*.png') if p.name!='contact-sheet.png'])
    if not images: return
    thumbs=[]
    for p in images:
        im=Image.open(p).convert('RGB'); im.thumbnail((480,360)); thumbs.append((p.name,im.copy()))
    cols=3; cellw=500; cellh=400; rows=(len(thumbs)+cols-1)//cols
    sheet=Image.new('RGB',(cols*cellw,rows*cellh),(28,28,30)); draw=ImageDraw.Draw(sheet)
    for i,(name,im) in enumerate(thumbs):
        x=(i%cols)*cellw+(cellw-im.width)//2; y=(i//cols)*cellh+24
        sheet.paste(im,(x,y)); draw.text(((i%cols)*cellw+12,(i//cols)*cellh+374),name,fill=(230,230,230))
    sheet.save(Path(directory)/'contact-sheet.png')

def acquire(operation_id):
    ref=DB.collection('blenderWorkspaceOperations').document(operation_id); tx=DB.transaction()
    @firestore.transactional
    def inner(transaction):
        snap=ref.get(transaction=transaction)
        if not snap.exists: raise RuntimeError('operation not found')
        data=snap.to_dict()
        if data.get('state') in ('completed','running'): return None
        if data.get('state')!='queued': raise RuntimeError('operation is not queued')
        transaction.update(ref,{'state':'running','startedAt':data.get('startedAt') or now(),'updatedAt':now(),'executor':{'blender':'4.5.12','serviceRevision':os.environ.get('K_REVISION','')}})
        return data
    return ref,inner(tx)

def complete_mutation(record, revision, result):
    opref=DB.collection('blenderWorkspaceOperations').document(record['operationId']); wsref=DB.collection('blenderWorkspaces').document(record['workspaceId']); revref=DB.collection('blenderWorkspaceRevisions').document(record['targetRevisionId']); tx=DB.transaction()
    @firestore.transactional
    def inner(transaction):
        ws=wsref.get(transaction=transaction).to_dict()
        if ws.get('pendingOperationId')!=record['operationId']: raise RuntimeError('workspace mutation lease lost')
        ids=list(ws.get('revisionIds') or [])
        if record['targetRevisionId'] not in ids: ids.append(record['targetRevisionId'])
        transaction.update(wsref,{'currentRevisionId':record['targetRevisionId'],'pendingOperationId':None,'revisionIds':ids[-500:],'updatedAt':now()})
        transaction.set(revref,revision,merge=True)
        transaction.update(opref,{'state':'completed','result':result,'humanAcceptance':'unreviewed','completedAt':now(),'updatedAt':now()})
    inner(tx)

def fail_operation(record, error, stderr=''):
    opref=DB.collection('blenderWorkspaceOperations').document(record['operationId']); payload={'state':'failed','blockingError':{'code':'blender.workspace.execution_failed','message':str(error)[:1200],'stderr':stderr[-8000:]},'failedAt':now(),'updatedAt':now()}; opref.set(payload,merge=True)
    if record.get('targetRevisionId'): DB.collection('blenderWorkspaceRevisions').document(record['targetRevisionId']).set({'state':'failed','blockingError':payload['blockingError'],'updatedAt':now()},merge=True)
    if record.get('kind') in ('create','mutate','restore'):
        wsref=DB.collection('blenderWorkspaces').document(record['workspaceId']); tx=DB.transaction()
        @firestore.transactional
        def clear(transaction):
            snap=wsref.get(transaction=transaction); data=snap.to_dict() if snap.exists else {}
            if data.get('pendingOperationId')==record['operationId']: transaction.update(wsref,{'pendingOperationId':None,'updatedAt':now()})
        clear(tx)

def process(operation_id):
    opref,record=acquire(operation_id)
    if record is None: return
    record['operationId']=operation_id
    with tempfile.TemporaryDirectory(prefix='blender-workspace-') as td:
        td=Path(td); out=td/'output'; out.mkdir(); request={'operation':record['kind'],'recipe':record.get('recipe') or {},'request':record.get('request') or {},'workspaceId':record['workspaceId'],'revisionId':record.get('targetRevisionId') or record.get('revisionId'),'inputHash':record['inputHash']}
        try:
            source=None
            if record['kind']=='create' and record.get('source',{}).get('kind')=='home_center_artifact': source=record['source']
            elif record['kind'] in ('mutate','restore','render','export'):
                source_revision=record.get('sourceRevisionId') if record['kind']=='restore' else record.get('baseRevisionId') or record.get('revisionId')
                snap=DB.collection('blenderWorkspaceRevisions').document(source_revision).get()
                if not snap.exists or snap.to_dict().get('state')!='completed': raise RuntimeError('source revision is not completed')
                source=snap.to_dict()['scene']
            if source:
                ext='.blend' if source.get('format')=='blend' or source.get('name','').endswith('.blend') else '.glb'
                local=td/('source'+ext); download(source,local); request['sourcePath']=str(local); request['sourceFormat']=ext[1:]
            req=td/'request.json'; req.write_text(json.dumps(request,separators=(',',':')))
            cmd=[BLENDER,'--background','--factory-startup','--disable-autoexec','--python','/app/executor.py','--',str(req),str(out)]
            run=subprocess.run(cmd,capture_output=True,text=True,timeout=TIMEOUT,env={**os.environ,'PYTHONNOUSERSITE':'1'})
            (out/'stdout.log').write_text(run.stdout[-65536:]); (out/'stderr.log').write_text(run.stderr[-65536:])
            if run.returncode: raise RuntimeError(f'Blender exited {run.returncode}: {run.stderr[-2000:]}')
            if record['kind']=='render': contact_sheet(out)
            prefix=(f"blender/workspaces/v1/{record['ownerHash']}/{record['workspaceId']}/revisions/{record.get('targetRevisionId')}" if record.get('targetRevisionId') else f"blender/workspaces/v1/{record['ownerHash']}/{record['workspaceId']}/revisions/{record['revisionId']}/derived/{operation_id}")
            artifacts=[]
            for p in sorted(out.iterdir()):
                if p.is_file(): artifacts.append(upload(p,f'{prefix}/{p.name}',classify(p.name)))
            result={'workspaceId':record['workspaceId'],'revisionId':record.get('targetRevisionId') or record.get('revisionId'),'artifacts':artifacts,'blenderVersion':'4.5.12','containerRevision':os.environ.get('K_REVISION',''),'inputHash':record['inputHash'],'humanAcceptance':'unreviewed','immutable':True}
            if record.get('targetRevisionId'):
                byname={a['name']:a for a in artifacts}; inspection=json.loads((out/'inspection.json').read_text()); validation=json.loads((out/'validation.json').read_text()); scene=byname['scene.blend']; scene['format']='blend'
                revision={'state':'completed','scene':scene,'inspection':inspection,'validation':validation,'completedAt':now(),'updatedAt':now(),'recipeHash':hashlib.sha256(json.dumps(record.get('recipe') or {},sort_keys=True,separators=(',',':')).encode()).hexdigest(),'blenderVersion':'4.5.12'}
                complete_mutation(record,revision,result)
            else: opref.set({'state':'completed','result':result,'humanAcceptance':'unreviewed','completedAt':now(),'updatedAt':now()},merge=True)
        except Exception as e:
            stderr=''
            try: stderr=(out/'stderr.log').read_text()
            except Exception: pass
            fail_operation(record,e,stderr); raise

class Handler(BaseHTTPRequestHandler):
    def reply(self,status,payload):
        body=json.dumps(payload,separators=(',',':')).encode(); self.send_response(status); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        if self.path in ('/','/health','/ready'): self.reply(200,{'ok':True,'service':'home-center-blender','blenderVersion':'4.5.12','revision':os.environ.get('K_REVISION','')})
        else: self.reply(404,{'error':'not_found'})
    def do_POST(self):
        if self.path!='/task': return self.reply(404,{'error':'not_found'})
        if not self.headers.get('X-CloudTasks-TaskName') and os.environ.get('ALLOW_DIRECT_TASKS')!='true': return self.reply(403,{'error':'cloud_task_required'})
        try:
            length=min(int(self.headers.get('Content-Length','0')),16384); payload=json.loads(self.rfile.read(length)); operation_id=str(payload.get('operationId',''))[:80]
            if not operation_id: raise ValueError('operationId required')
            with LOCK: process(operation_id)
            self.reply(200,{'ok':True,'operationId':operation_id})
        except Exception as e: self.reply(500,{'ok':False,'error':str(e)[:1000]})
    def log_message(self,fmt,*args): print(fmt%args,flush=True)

if __name__=='__main__': ThreadingHTTPServer(('0.0.0.0',int(os.environ.get('PORT','8080'))),Handler).serve_forever()
