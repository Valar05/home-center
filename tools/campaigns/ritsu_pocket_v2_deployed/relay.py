"""Minimal tailnet-only audio relay. Python standard library, except existing tts_adapter."""
import argparse, json, os, secrets, threading, urllib.parse, ipaddress
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tts_adapter import resolve

import sys
if sys.stdout is None:sys.stdout=open(str(Path(__file__).with_name('relay-headless.stdout.log')),'a',buffering=1,encoding='utf-8')
if sys.stderr is None:sys.stderr=open(str(Path(__file__).with_name('relay-headless.stderr.log')),'a',buffering=1,encoding='utf-8')
PENDING=deque(); FILES={}; LOCK=threading.RLock()

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--host',required=True,help='THECAULDRON Tailscale IPv4 only')
    p.add_argument('--port',type=int,default=19643)
    p.add_argument('--token-file',default=str(Path(__file__).with_name('relay-token.txt')))
    a=p.parse_args()
    if not ipaddress.ip_address(a.host) in ipaddress.ip_network('100.64.0.0/10'):
        p.error('Bind to a Tailscale IPv4 address, not public or wildcard')
    tokenpath=Path(a.token_file)
    if not tokenpath.exists():
        tokenpath.write_text(secrets.token_urlsafe(32),encoding='utf-8')
        try: os.chmod(tokenpath,0o600)
        except OSError: pass
    token=tokenpath.read_text(encoding='utf-8').strip()
    class Handler(BaseHTTPRequestHandler):
        def respond(self,code,body=b'',ctype='application/json'):
            self.send_response(code); self.send_header('Content-Type',ctype)
            self.send_header('Content-Length',str(len(body))); self.send_header('Cache-Control','no-store'); self.end_headers()
            if body:self.wfile.write(body)
        def auth(self):
            if not secrets.compare_digest(self.headers.get('Authorization',''), 'Bearer '+token):
                self.respond(401,b'{"error":"unauthorized"}');return False
            return True
        def do_GET(self):
            if not self.auth():return
            path=urllib.parse.urlparse(self.path).path
            if path=='/health':return self.respond(200,b'{"ok":true}')
            if path=='/next':
                with LOCK: item=PENDING[0] if PENDING else None
                return self.respond(200,json.dumps(item).encode()) if item else self.respond(204)
            if path.startswith('/audio/'):
                key=path.split('/')[-1]
                with LOCK: f=FILES.get(key)
                if not f or not Path(f).is_file():return self.respond(404)
                return self.respond(200,Path(f).read_bytes(),'audio/wav')
            self.respond(404)
        def do_POST(self):
            if not self.auth():return
            path=urllib.parse.urlparse(self.path).path
            try:
                n=int(self.headers.get('Content-Length','0'))
                if n<=0 or n>16384: return self.respond(413)
                obj=json.loads(self.rfile.read(n))
                if path=='/ack':
                    key=obj.get('id')
                    with LOCK:
                        if PENDING and PENDING[0]['id']==key:PENDING.popleft()
                    return self.respond(200,b'{"ok":true}')
                if path=='/enqueue':
                    # Explicitly require same-machine origin for speech submissions.
                    if self.client_address[0] not in ('127.0.0.1',a.host):return self.respond(403)
                    text=obj.get('text','')
                    if not isinstance(text,str) or not (1<=len(text)<=1000):return self.respond(400)
                    character=obj.get('character','ritsu')
                    profile=obj.get('profile','normal')
                    if not isinstance(profile,str) or profile not in ('normal','warm','delighted','happy','amused','somber','upset','whisper'):
                        return self.respond(400,b'{"error":"unsupported_pocket_profile"}')
                    print('ENQUEUE_DEBUG',repr(text),flush=True)
                    if text.startswith('__TURBO_WAV__:'):
                        basename=text[len('__TURBO_WAV__:'):]
                        candidate=(Path(r'C:\Users\dclar\workspace\ritsu-chatterbox-turbo')/'generated'/basename).resolve()
                        directory=(Path(r'C:\Users\dclar\workspace\ritsu-chatterbox-turbo')/'generated').resolve()
                        if (not basename or '/' in basename or '\\' in basename
                            or candidate.parent != directory or candidate.suffix.lower() != '.wav'
                            or not candidate.is_file() or candidate.stat().st_size <= 44):
                            return self.respond(400,b'{"error":"invalid_generated_wav"}')
                        filename=str(candidate)
                    else:
                        filename,_=resolve(text,character,profile)
                    key=secrets.token_hex(12)
                    with LOCK:
                        FILES[key]=filename
                        PENDING.append({'id':key,'character':character,'profile':profile,'text':text[:120], 'audio':'/audio/'+key})
                    return self.respond(200,json.dumps({'ok':True,'id':key}).encode())
                self.respond(404)
            except Exception as e:
                self.respond(500,json.dumps({'error':str(e)}).encode())
    print('Relay listening on '+a.host+':'+str(a.port),flush=True)
    loopback=ThreadingHTTPServer(('127.0.0.1',a.port),Handler)
    threading.Thread(target=loopback.serve_forever,daemon=True,name='ritsu-local-relay').start()
    print('Local relay listening on 127.0.0.1:'+str(a.port),flush=True)
    ThreadingHTTPServer((a.host,a.port),Handler).serve_forever()
if __name__=='__main__':main()

