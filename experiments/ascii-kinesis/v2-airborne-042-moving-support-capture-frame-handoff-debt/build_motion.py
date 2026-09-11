#!/usr/bin/env python3
from __future__ import annotations
import json, math, subprocess, hashlib, shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parent
MOTION=ROOT/'motion.json'; FRAME_DIR=ROOT/'.frames'; OUT=ROOT/'airborne042-authoritative.mp4'
W,H,FPS=800,448,24
holds={'ONES':1,'TWOS':2,'FOURS':4}; hard_after={1,6,7,9}
def lerp(a,b,t): return a+(b-a)*t
def bridge(a,b,t):
 s=t*t*(3-2*t); o={}
 for q in ('x','y','lean','arm'): o[q]=lerp(a[q],b[q],s)
 for q in ('platform_x','platform_v'): o[q]=lerp(a[q],b[q],t)
 for q in ('legL','legR'): o[q]=(lerp(a[q][0],b[q][0],s),lerp(a[q][1],b[q][1],s))
 o['contact']=a['contact']; o['support']=a['support']; o['label']=a['label']+'→'+b['label']; return o
def font(size):
 p='/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
 try:return ImageFont.truetype(p,size)
 except:return ImageFont.load_default()
FONT=font(14); SMALL=font(12)
def render(k,idx,total):
 im=Image.new('RGB',(W,H),(10,12,14)); d=ImageDraw.Draw(im)
 d.line((62,390,192,390),fill=(155,155,155),width=3); d.text((62,398),'FIXED LAUNCH',fill=(130,130,130),font=SMALL)
 px=k['platform_x']; py=350
 d.line((px-86,py,px+86,py),fill=(220,220,220),width=4); d.line((px-70,py+8,px+70,py+8),fill=(130,130,130),width=2)
 d.line((px+50,py+20,px+75,py+20),fill=(160,160,160),width=2); d.polygon([(px+75,py+20),(px+66,py+15),(px+66,py+25)],fill=(160,160,160)); d.text((px-78,py+15),'MOVING FRAME',fill=(150,150,150),font=SMALL)
 x,y=k['x'],k['y']; lean=k['lean']; pelvis=(x,y); shoulder=(x+lean*.7,y-34); head=(shoulder[0]+lean*.25,shoulder[1]-24)
 d.line((*pelvis,*shoulder),fill='white',width=4); d.ellipse((head[0]-9,head[1]-9,head[0]+9,head[1]+9),outline='white',width=3)
 aa=math.radians(-30+k['arm']); ab=math.radians(210-k['arm']*.6); Ls=(shoulder[0]-4,shoulder[1]+4); Rs=(shoulder[0]+4,shoulder[1]+4)
 Lh=(Ls[0]+33*math.cos(ab),Ls[1]+33*math.sin(ab)); Rh=(Rs[0]+33*math.cos(aa),Rs[1]+33*math.sin(aa)); d.line((*Ls,*Lh),fill=(240,240,240),width=3); d.line((*Rs,*Rh),fill=(240,240,240),width=3)
 for side,off,col in [('L',k['legL'],(255,255,255)),('R',k['legR'],(210,210,210))]:
  foot=(x+off[0],y+off[1]); knee=(x+off[0]*.45,y+off[1]*.5); d.line((x,y,*knee),fill=col,width=4); d.line((*knee,*foot),fill=col,width=4)
  if side in k['support']: d.line((foot[0]-9,foot[1],foot[0]+9,foot[1]),fill=(255,215,140),width=3)
 d.ellipse((x-3,y-3,x+3,y+3),fill=(255,190,120))
 if k['contact'].startswith('MOVING_PLATFORM'): d.line((px,py-8,x,y),fill=(100,150,190),width=1)
 d.text((18,18),f'AIRBORNE042 · {idx+1:02d}/{total:02d}',fill='white',font=FONT); d.text((18,40),k['label'],fill=(220,220,220),font=FONT); d.text((18,62),f"contact={k['contact']}",fill=(175,175,175),font=SMALL); d.text((18,80),'PARENT WORLD MOTION ≠ CHILD LOCAL KEY',fill=(150,190,220),font=SMALL)
 return im
def main():
 m=json.loads(MOTION.read_text()); keys=m['keys']; frames=[]
 for i,k in enumerate(keys):
  frames += [k]*holds[k['timing_class']]
  if i+1<len(keys):
   n=0 if i in hard_after or k['contact']!=keys[i+1]['contact'] else (2 if k['timing_class']!='ONES' else 1)
   for j in range(1,n+1): frames.append(bridge(k,keys[i+1],j/(n+1)))
 if FRAME_DIR.exists(): shutil.rmtree(FRAME_DIR)
 FRAME_DIR.mkdir()
 for i,k in enumerate(frames): render(k,i,len(frames)).save(FRAME_DIR/f'f{i:04d}.png')
 subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-framerate',str(FPS),'-i',str(FRAME_DIR/'f%04d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','25','-movflags','+faststart',str(OUT)],check=True)
 b=OUT.read_bytes(); print(json.dumps({'path':str(OUT),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'frames':len(frames),'fps':FPS},sort_keys=True))
if __name__=='__main__': main()
