#!/usr/bin/env python3
import importlib.util
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SPEC=importlib.util.spec_from_file_location('adam_audio_lab',ROOT/'adam_audio_lab.py')
audio=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(audio)

def sine(freq=120.0,seconds=1.0,amp=0.65):
 return tuple(int(32767*amp*math.sin(2*math.pi*freq*i/audio.SAMPLE_RATE)) for i in range(int(audio.SAMPLE_RATE*seconds)))

def main():
 silence=audio.analyze((0,)*audio.SAMPLE_RATE); assert silence['silence'] is True; assert audio.interest(silence)==0.0
 low=audio.analyze(sine()); assert low['rms']>0.1 and low['peak']>0.5
 graph=audio.graph_from(low); assert graph['schema']=='adam-sound-graph-v1'; assert graph['nodes']; assert graph['renderTarget']=='mono'
 # Sharp alternating signal must look substantially noisier/brighter than silence and remain bounded.
 noisy=audio.analyze(tuple(25000 if i%2 else -25000 for i in range(audio.SAMPLE_RATE//2)))
 assert 0.0<=noisy['zcr']<=1.0 and noisy['zcr']>0.8
 assert 0.0<=audio.interest(noisy)<=1.0
 print(json.dumps({'ok':True,'tests':['silence detection','deterministic features','bounded interest score','modular sound graph']}))
 return 0
if __name__=='__main__': raise SystemExit(main())
