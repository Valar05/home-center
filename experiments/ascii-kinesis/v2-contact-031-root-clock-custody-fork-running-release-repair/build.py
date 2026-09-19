#!/usr/bin/env python3
from pathlib import Path
import base64,gzip,hashlib,html,json,subprocess,tempfile
from PIL import Image,ImageDraw

R=Path(__file__).resolve().parent
E="v2-contact-031-root-clock-custody-fork-running-release-repair"
SLUG="root-clock-custody-fork-running-release-repair"
W,H,G=64,24,19
FPS=24
SRC={"site":"The Spriters Resource","asset_id":52578,"name":"Mario & Luigi","game":"Super Mario Bros. 2: The Lost Levels (JPN)","platform":"NES","raw_dimensions":[584,468],"raw_bytes":52370,"raw_sha256":"7aa238a5d3cb74646aa93659241a3f933caea45d7908a27e59fa56a477d33bf6","source_timing":"UNKNOWN","region":[12,300,250,103],"whole_sheet_inspected":True,"rights":"evidence-only; no source pixels, palette, costume, exact silhouette, choreography, tracing, or redistribution"}
PRE="experiments/ascii-kinesis/v2-contact-002-root-clock-custody-fork/"
CMD="phc_contact002_create031_assemble_20260919_1403_v1"
def K(i,n,root,pts,obj,cust,support,role,note,timing,hold):
    return {"key_id":f"C031-K{i}","name":n,"root":root,"A":pts,"object":{"glyph":"o","position":obj,"state":"ANCHORED" if cust=="A_HAND" else ("FREE" if cust=="FREE" else "OUTSIDE")},"custody":cust,"contact_state":"HAND_OBJECT" if cust=="A_HAND" else "NONE","root_owner":"A_LOCAL","support_A":support,"causal_role":role,"motion_arc_root_note":note,"timing_class":timing,"timing_provenance":"DERIVED_UAT_OPINION","hold_frames":hold}
def P(root,head,sl,sr,el,er,hl,hr,kl,kr,fl,fr):
    return {"root":root,"head":head,"shoulder_l":sl,"shoulder_r":sr,"elbow_l":el,"elbow_r":er,"hand_l":hl,"hand_r":hr,"knee_l":kl,"knee_r":kr,"foot_l":fl,"foot_r":fr}
keys=[
 K(0,"RUNNING_GATHER",[10,11],P([10,11],[10,4],[8,7],[12,6],[12,8],[8,8],[15,9],[5,10],[13,15],[7,15],[16,19],[5,18]),[5,10],"A_HAND","RIGHT_DRIVE","Carrier already travels; rear hand owns the object while the stride remains primary.","Root advances before throw preparation; object relation is local.","FOURS",3),
 K(1,"COUNTERROTATE_LOAD",[14,11],P([14,11],[15,4],[12,7],[17,6],[16,9],[10,6],[20,10],[8,5],[12,15],[17,15],[9,19],[20,19]),[8,5],"A_HAND","LEFT_CATCH","Chest winds against travel while the catching leg accepts weight.","Root continues right; rear-side object load does not freeze locomotion.","TWOS",2),
 K(2,"CROSSSTEP_CARRY",[18,11],P([18,11],[19,4],[16,7],[21,6],[20,10],[15,5],[23,11],[13,4],[21,15],[16,15],[25,18],[14,19]),[13,4],"A_HAND","RIGHT_DRIVE","Cross-step carries the object past the torso without donating root authority to the hand.","Pelvis overtakes the loaded hand; custody stays local.","TWOS",2),
 K(3,"WHIP_WINDOW",[22,11],P([22,11],[23,4],[20,7],[25,6],[18,9],[29,6],[17,10],[32,5],[20,15],[25,15],[17,19],[29,18]),[32,5],"A_HAND","LEFT_CATCH","Throw side whips forward after pelvis lead; opposite arm opens negative space.","Hand-object anchor reaches release window while root velocity remains forward.","ONES",1),
 K(4,"RELEASE_FORK",[26,11],P([26,11],[27,4],[24,7],[29,6],[22,8],[33,7],[20,9],[36,7],[29,15],[24,15],[32,19],[22,18]),[38,6],"FREE","RIGHT_DRIVE","Custody breaks at full directional commitment, not at a stop pose.","A_HAND -> FREE is a hard causal fork; root clock remains continuous.","ONES",1),
 K(5,"RUN_THROUGH_RECOIL",[31,11],P([31,11],[32,4],[29,6],[34,8],[27,6],[36,10],[25,7],[38,12],[28,15],[35,15],[26,19],[39,18]),[46,5],"FREE","LEFT_CATCH","Throw arm overshoots low while the next step catches the still-moving center of mass.","Free object gains lead; shoulder recoil lags pelvis instead of reversing release.","TWOS",3),
 K(6,"OBJECT_OUTRUNS_BODY",[36,11],P([36,11],[36,4],[33,7],[39,6],[38,9],[34,9],[42,10],[31,10],[39,15],[34,15],[43,19],[31,18]),[54,6],"FREE","RIGHT_DRIVE","Arm swing re-enters the run cycle while projectile separation keeps increasing.","Carrier recovers on its own locomotor phase; object keeps independent clock.","TWOS",3),
 K(7,"RECOVERY_CROSSING",[41,11],P([41,11],[41,4],[38,6],[44,7],[36,8],[46,9],[34,9],[49,10],[39,15],[45,15],[36,19],[49,19]),[61,8],"FREE","LEFT_CATCH","Recovery is another committed stride, not return-to-idle.","Root exits right with asymmetry preserved; free object approaches frame exit.","FOURS",4),
 K(8,"RUNNING_EXIT",[46,11],P([46,11],[47,4],[44,7],[49,6],[48,9],[45,8],[52,10],[42,9],[50,15],[44,15],[53,18],[41,19]),None,"OUTSIDE","RIGHT_DRIVE","Object has left the frame; carrier continues with unresolved locomotor debt.","Release is proven orthogonal to root motion because carrier never stops to complete it.","FOURS",5),
]
TRANS=[3,3,3,1,4,4,4,4]
def line(g,a,b,ch=None):
 x0,y0=map(round,a);x1,y1=map(round,b);dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;e=dx+dy
 if ch is None: ch='-' if abs(x1-x0)>abs(y1-y0)*1.6 else ('|' if abs(y1-y0)>abs(x1-x0)*1.6 else ('\\' if (x1-x0)*(y1-y0)>0 else '/'))
 while True:
  if 0<=x0<W and 0<=y0<H and g[y0][x0]==' ':g[y0][x0]=ch
  if x0==x1 and y0==y1:break
  q=2*e
  if q>=dy:e+=dy;x0+=sx
  if q<=dx:e+=dx;y0+=sy
def put(g,p,c):
 if p is None:return
 x,y=map(round,p)
 if 0<=x<W and 0<=y<H:g[y][x]=c
def frame(k):
 g=[[' ']*W for _ in range(H)]
 for x in range(W):g[G][x]='_'
 p=k["A"]
 for a,b in [("shoulder_l","shoulder_r"),("shoulder_l","root"),("shoulder_r","root"),("shoulder_l","elbow_l"),("elbow_l","hand_l"),("shoulder_r","elbow_r"),("elbow_r","hand_r"),("root","knee_l"),("knee_l","foot_l"),("root","knee_r"),("knee_r","foot_r")]: line(g,p[a],p[b])
 mid=[(p["shoulder_l"][0]+p["shoulder_r"][0])/2,(p["shoulder_l"][1]+p["shoulder_r"][1])/2];line(g,mid,p["head"],"|")
 put(g,p["head"],"@");put(g,p["root"],"+");put(g,p["hand_l"],"o");put(g,p["hand_r"],"o");put(g,p["foot_l"],"L");put(g,p["foot_r"],"R")
 op=k["object"]["position"]
 if op is not None: put(g,op,"*" if k["custody"]=="A_HAND" else "O")
 if k["custody"]=="A_HAND" and op is not None: line(g,p["hand_r"],op,":")
 if k["custody"]=="FREE" and op is not None:
  for d in (3,6): put(g,[op[0]-d,op[1]+1],".")
 return "\n".join("".join(r).rstrip() for r in g)
def lerp(a,b,t):return [a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t]
def tween(a,b,t):
 q=json.loads(json.dumps(a));q["root"]=lerp(a["root"],b["root"],t)
 for j in q["A"]:q["A"][j]=lerp(a["A"][j],b["A"][j],t)
 if a["custody"]==b["custody"] and a["object"]["position"] is not None and b["object"]["position"] is not None:q["object"]["position"]=lerp(a["object"]["position"],b["object"]["position"],t)
 else:q["object"]=a["object"];q["custody"]=a["custody"];q["contact_state"]=a["contact_state"]
 return q
def timeline():
 out=[]
 for i,k in enumerate(keys):
  out += [k]*k["hold_frames"]
  if i<len(keys)-1:
   n=TRANS[i]
   if k["custody"]!=keys[i+1]["custody"]:continue
   out += [tween(k,keys[i+1],j/(n+1)) for j in range(1,n+1)]
 return out
def glyph(d,c,x,y,cw,ch):
 q=(244,244,244);w=2;P=lambda u,v:(x+1+u*(cw-2),y+1+v*(ch-2))
 if c==' ':return
 if c=='_':d.line((*P(0,1),*P(1,1)),fill=q,width=w)
 elif c=='-':d.line((*P(0,.5),*P(1,.5)),fill=q,width=w)
 elif c=='|':d.line((*P(.5,0),*P(.5,1)),fill=q,width=w)
 elif c=='/':d.line((*P(0,1),*P(1,0)),fill=q,width=w)
 elif c=='\\':d.line((*P(0,0),*P(1,1)),fill=q,width=w)
 elif c=='.':d.ellipse((x+cw//2-1,y+ch//2-1,x+cw//2+1,y+ch//2+1),fill=q)
 elif c in '*O':d.ellipse((x+1,y+1,x+cw-2,y+ch-2),outline=q,width=w)
 elif c=='@':d.ellipse((x+1,y+1,x+cw-2,y+ch-2),outline=q,width=w);d.line((*P(.25,.55),*P(.75,.55)),fill=q,width=1)
 elif c=='+':d.line((*P(0,.5),*P(1,.5)),fill=q,width=w);d.line((*P(.5,0),*P(.5,1)),fill=q,width=w)
 elif c in 'oLR':d.rectangle((x+1,y+2,x+cw-2,y+ch-2),outline=q,width=1)
 elif c==':':d.ellipse((x+cw//2-1,y+2,x+cw//2+1,y+4),fill=q);d.ellipse((x+cw//2-1,y+ch-4,x+cw//2+1,y+ch-2),fill=q)
def raster(txt):
 im=Image.new("RGB",(320,192),(6,6,6));d=ImageDraw.Draw(im);cw,ch=5,8
 for y,row in enumerate(txt.splitlines()[:H]):
  for x,c in enumerate(row[:W]):glyph(d,c,x*cw,y*ch,cw,ch)
 return im
def sha(b):return hashlib.sha256(b).hexdigest()
def contact_sheet():
 out=[E,"PRINCIPLE=OBJECT RELEASE IS ORTHOGONAL TO ROOT MOTION",f"REVISES={PRE}",f"NEGATIVE_FIXTURE={PRE}","SOURCE_CHANGE=false",f"SOURCE=TSR asset 52578 | 584x468 RGBA | 52370 bytes | sha256={SRC['raw_sha256']}","SOURCE_TIMING=UNKNOWN | roles=POSE_REFERENCE + CONTACT_TOPOLOGY_REFERENCE","RIGHTS="+SRC["rights"],""]
 for k in keys:out += ["="*64,f"{k['key_id']} {k['name']} | {k['timing_class']} | hold={k['hold_frames']} | {k['timing_provenance']}",f"CUSTODY={k['custody']} | CONTACT={k['contact_state']} | ROOT={k['root_owner']} | SUPPORT={k['support_A']}",f"ROLE={k['causal_role']}",f"ARC={k['motion_arc_root_note']}",frame(k),""]
 return "\n".join(out).rstrip()+"\n"
def spa(a,j,v):
 z=lambda s:base64.b64encode(gzip.compress(s.encode(),9,mtime=0)).decode()
 return '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+E+'</title><style>body{background:#080808;color:#eee;font-family:system-ui;margin:0}nav{position:sticky;top:0;background:#111;padding:10px}button{margin-right:8px}section{display:none;padding:12px}section.on{display:block}pre{white-space:pre;overflow:auto;font-family:ui-monospace,Consolas,monospace;font-variant-ligatures:none}video{width:min(100%,800px);image-rendering:pixelated}</style><nav><button data-view="ascii" data-v="a">ASCII</button><button data-view="json" data-v="j">JSON</button><button data-view="video" data-v="v">VIDEO</button></nav><section id="a" class="on"><pre></pre></section><section id="j"><pre></pre></section><section id="v"><video controls autoplay muted loop playsinline src="data:video/mp4;base64,'+base64.b64encode(v).decode()+'"></video></section><script>const A="'+z(a)+'",J="'+z(j)+'";async function d(s){let u=Uint8Array.from(atob(s),c=>c.charCodeAt(0));return new TextDecoder().decode(await new Response(new Blob([u]).stream().pipeThrough(new DecompressionStream("gzip"))).arrayBuffer())}(async()=>{a.querySelector("pre").textContent=await d(A);j.querySelector("pre").textContent=await d(J)})();document.querySelectorAll("button").forEach(b=>b.onclick=()=>document.querySelectorAll("section").forEach(s=>s.classList.toggle("on",s.id===b.dataset.v)))</script>'
def main():
 tl=timeline();assert len(tl)>=40;a=contact_sheet()
 with tempfile.TemporaryDirectory() as td:
  td=Path(td);fd=td/"f";fd.mkdir()
  for i,k in enumerate(tl):raster(frame(k)).save(fd/f"{i:04d}.png")
  mp=td/"m.mp4";subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate",str(FPS),"-i",str(fd/"%04d.png"),"-c:v","libx264","-preset","veryslow","-crf","28","-pix_fmt","yuv420p","-movflags","+faststart",str(mp)],check=True)
  v=mp.read_bytes();probe=json.loads(subprocess.check_output(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=codec_name,pix_fmt,width,height,avg_frame_rate,nb_frames","-of","json",str(mp)]))
  subprocess.run(["ffmpeg","-v","error","-i",str(mp),"-f","null","-"],check=True)
 media={"bytes":len(v),"sha256":sha(v),"probe":probe["streams"][0],"decoded_frames":len(tl),"strict_decode":"PASS"}
 revision={"revises":PRE,"negative_fixture":PRE,"source_change":False,"reset_issue_comment":5634613836,"successor_identity_issue_comment":5744486433}
 motion={"schema":"ascii-kinesis.motion.v2","format_version":2,"experiment_id":E,"lane":"contact","revision":revision,"source":SRC,"source_roles":["POSE_REFERENCE","CONTACT_TOPOLOGY_REFERENCE"],"principle":"OBJECT RELEASE IS ORTHOGONAL TO ROOT MOTION","timing":{"authority":"worker-authored","provenance":"DERIVED_UAT_OPINION","fps":FPS},"direction":{"sentence":"Run through the throw: pelvis and support keep traveling while the hand-object constraint loads, releases, recoils, and the free object outruns the body."},"keys":keys,"compile":{"method":"AUTHORED ASCII KEYS + DIRECTION PROFILE -> DETERMINISTIC CONNECTIVE MOTION -> ASCII-ONLY FRAME RENDER -> MP4 -> SPA","fps":FPS,"frames_total":len(tl),"connector_rule":"Interpolate coordinates only while custody/contact topology is unchanged; custody fork hard-cuts.","source_sprite_pixels_used":False,"media":media},"correction_hooks":["KEEP","REJECT","EXAGGERATE","COMPRESS","RETIME","CHANGE SOURCE","FIX BLOCKER","RERUN"]}
 j=json.dumps(motion,indent=2,sort_keys=True)+"\n";s=spa(a,j,v)
 files=["build.py","contact-sheet.txt","manifest.json","motion.json","receipt.json",SLUG+".motion.html"]
 manifest={"backward_compatible":True,"schema":"ascii-kinesis.swarm-manifest.v2","format_version":2,"experiment_id":E,"lane":"contact","files":files,"primary_tabs":["ASCII","JSON","VIDEO"],"ascii_literal_text":True,"whitespace_preserved":True,"ligatures_disabled":True,"source_art_embedded":False,"video_required":True,"video_source":"abstract_ascii_rig_only","video_packaging":"embedded MP4 data URI in "+SLUG+".motion.html","reconstruction":"python3 build.py","revision":revision,"source":SRC,"media":media,"state":"PERSISTED_NOT_DELIVERED"}
 receipt={"schema":"ascii-kinesis.repair-receipt.v2","experiment_id":E,"state":"PERSISTED_NOT_DELIVERED","authorized_creation_command":CMD,"repo_readback":False,"issue_pre_delivery":False,"home_center_pre_delivery":False,"chat":{"PART1":False,"PART2":False,"PART3":False},"tango":"PENDING_ACTUAL_VISIBLE_FINAL_MEDIA","noodle_queen":"PENDING_AFTER_TANGO","official_validator":"PENDING_AFTER_TANGO_QUEEN","drew_accepted":False,"revision":revision,"source":SRC,"media":media}
 (R/"contact-sheet.txt").write_text(a);(R/"motion.json").write_text(j);(R/"manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n");(R/"receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n");(R/(SLUG+".motion.html")).write_text(s)
 print(json.dumps({"experiment":E,"files":files,"frames":len(tl),"media":media,"ascii_sha256":sha(a.encode()),"motion_sha256":sha(j.encode()),"spa_sha256":sha(s.encode())},sort_keys=True))
if __name__=="__main__":main()
