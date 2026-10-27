#!/usr/bin/env python3
from __future__ import annotations
import argparse,base64,hashlib,io,json,math,pathlib,tempfile,wave
from pocket_tts_cauldron_backend import CauldronRenderError,render_on_cauldron
from pocket_tts_render_v2 import CONTRACT_VERSION,GeneratedUnit,PocketTtsEngine,SAMPLE_RATE,normalized_text,sha256_bytes

def wav_bytes(seconds=.6):
    pcm=bytearray()
    for i in range(int(seconds*SAMPLE_RATE)):
        value=int(4000*math.sin(2*math.pi*180*i/SAMPLE_RATE));pcm.extend(value.to_bytes(2,'little',signed=True))
    target=io.BytesIO()
    with wave.open(target,'wb') as audio:audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(SAMPLE_RATE);audio.writeframes(pcm)
    return target.getvalue()
text='Headless remote render contract.'; audio=wav_bytes(); digest=sha256_bytes(audio)
receipt={'status':'complete','accepted':True,'contractVersion':CONTRACT_VERSION,'requestId':'section-001','textSha256':sha256_bytes(normalized_text(text).encode()),'artifactSha256':digest,'output':r'C:\\Users\\Public\\HomeCenterPocketTts\\section.wav','sampleRate':SAMPLE_RATE,'channels':1,'sampleWidth':2,'frames':(len(audio)-44)//2,'durationSeconds':(len(audio)-44)/2/SAMPLE_RATE,'corruptTail':False}
class FakeClient:
    def __init__(self):self.tickets={};self.counter=0
    def drive_operation(self,operation,args):
        if operation=='computer_hands.worker.status':return {'online':True,'capabilities':['shell.exec'],'workerId':'windows-hands-01'}
        if operation=='computer_hands.request.create':
            self.counter+=1; ticket=f'ticket-{self.counter}'; action=args['action']; arguments=args['arguments']
            if action=='process.start': stdout='STARTED'
            else:
                command=arguments['command']
                if 'Test-Path' in command: stdout=json.dumps(receipt)
                else:
                    import re
                    offset=int(re.search(r'Seek\((\d+)',command).group(1));length=int(re.search(r'byte\[\] (\d+)',command).group(1));stdout=base64.b64encode(audio[offset:offset+length]).decode()
            self.tickets[ticket]={'stdout':stdout};return {'ticketId':ticket}
        if operation=='computer_hands.request.status':return {'status':'completed','result':{'ok':True,**self.tickets[args['ticketId']]}}
        raise AssertionError(operation)
with tempfile.TemporaryDirectory(prefix='cauldron-v2-') as temp:
    output=pathlib.Path(temp)/'section.wav'; result=render_on_cauldron('section-001',text,output,client=FakeClient(),timeout=2)
    assert output.read_bytes()==audio and result['backend']=='cauldron-computer-hands' and result['artifactSha256']==digest
class Offline:
    def drive_operation(self,operation,args):return {'online':False,'capabilities':['shell.exec']}
try:render_on_cauldron('section-002',text,pathlib.Path('/tmp/no.wav'),client=Offline(),timeout=1);raise AssertionError('offline accepted')
except CauldronRenderError:pass
print('Pocket TTS Cauldron Computer Hands transport: OK')
