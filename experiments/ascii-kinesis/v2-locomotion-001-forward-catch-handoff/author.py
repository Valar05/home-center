from pathlib import Path
import json
ENTRY=Path(__file__).resolve().parent
W,H=54,20
bones=[('pelvis','chest'),('chest','head'),('chest','l_shoulder'),('l_shoulder','l_elbow'),('l_elbow','l_hand'),('chest','r_shoulder'),('r_shoulder','r_elbow'),('r_elbow','r_hand'),('pelvis','l_knee'),('l_knee','l_foot'),('pelvis','r_knee'),('r_knee','r_foot')]

def line(a,b):
    x0,y0=a;x1,y1=b; dx=abs(x1-x0); sx=1 if x0<x1 else -1; dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy
    out=[]
    while True:
        out.append((x0,y0))
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy
    return out

def render(j, support_symbols):
    g=[[' ']*W for _ in range(H)]
    for x in range(W): g[18][x]='-'
    for a,b in bones:
        pts=line(j[a],j[b])
        for x,y in pts[1:-1]:
            if 0<=x<W and 0<=y<H and g[y][x]==' ':
                ax,ay=j[a]; bx,by=j[b]
                if bx==ax: ch='|'
                elif (bx-ax)*(by-ay)>0: ch='\\'
                else: ch='/'
                g[y][x]=ch
    marks={'head':'O','pelvis':'+','chest':'o','l_shoulder':'o','r_shoulder':'o','l_elbow':'o','r_elbow':'o','l_hand':'*','r_hand':'*','l_knee':'o','r_knee':'o','l_foot':'*','r_foot':'*'}
    for name,ch in marks.items():
        x,y=j[name]
        g[y][x]=support_symbols.get(name,ch)
    return '\n'.join(''.join(row).rstrip() for row in g).rstrip()

keys=[]
def add(kid,name,timing,role,support,rootnote,j,sym):
    keys.append({'key_id':kid,'name':name,'timing_class':timing,'timing_provenance':'INFERRED','causal_role':role,'support_contact':support,'motion_arc_root_note':rootnote,'joints':j,'ascii_pose':render(j,sym)})

# generic independently-authored biped; positions are not traced from source.
add('K0','LOAD','FOURS','rear support stores travel impulse','REAR_FOOT_OWNS_ROOT','root x=12; low velocity; pelvis compresses over rear support',
{'pelvis':[12,11],'chest':[13,7],'head':[14,4],'l_shoulder':[11,7],'l_elbow':[9,9],'l_hand':[10,11],'r_shoulder':[15,7],'r_elbow':[17,9],'r_hand':[16,11],'l_knee':[10,14],'l_foot':[8,17],'r_knee':[15,14],'r_foot':[18,17]}, {'l_foot':'!','r_foot':'*'})
add('K1','PUSH','ONES','rear support spends impulse and opens stride','REAR_TOE_LAST_SUPPORT','root x=14; acceleration begins; rear contact narrows before release',
{'pelvis':[14,10],'chest':[15,6],'head':[16,3],'l_shoulder':[13,6],'l_elbow':[11,8],'l_hand':[10,10],'r_shoulder':[17,6],'r_elbow':[19,8],'r_hand':[20,10],'l_knee':[11,14],'l_foot':[8,17],'r_knee':[18,12],'r_foot':[21,14]}, {'l_foot':'!','r_foot':'*'})
add('K2','CROSS','TWOS','root travels while neither foot owns it','NO_FOOT_SUPPORT','root x=19; largest forward spacing; shallow airborne arc',
{'pelvis':[19,9],'chest':[20,5],'head':[21,2],'l_shoulder':[18,5],'l_elbow':[16,7],'l_hand':[15,9],'r_shoulder':[22,5],'r_elbow':[24,7],'r_hand':[25,9],'l_knee':[17,12],'l_foot':[15,14],'r_knee':[22,12],'r_foot':[25,15]}, {})
add('K3','PROBE','ONES','lead foot touches without yet owning root','LEAD_FOOT_PROBE_CONTACT','root x=24; forward travel continues; probe lands ahead of pelvis',
{'pelvis':[24,9],'chest':[25,5],'head':[26,2],'l_shoulder':[23,5],'l_elbow':[21,7],'l_hand':[20,9],'r_shoulder':[27,5],'r_elbow':[29,7],'r_hand':[30,9],'l_knee':[21,12],'l_foot':[19,15],'r_knee':[27,13],'r_foot':[31,17]}, {'r_foot':'?'})
add('K4','CATCH','TWOS','lead contact earns support and absorbs vertical load','LEAD_FOOT_OWNS_ROOT','root x=27; pelvis drops while x still advances; catch is not a stop',
{'pelvis':[27,11],'chest':[28,7],'head':[29,4],'l_shoulder':[26,7],'l_elbow':[24,9],'l_hand':[23,11],'r_shoulder':[30,7],'r_elbow':[32,9],'r_hand':[33,11],'l_knee':[24,14],'l_foot':[22,16],'r_knee':[29,14],'r_foot':[31,17]}, {'r_foot':'!'})
add('K5','PASS','ONES','body passes over trusted support while momentum survives','LEAD_FOOT_OWNS_ROOT','root x=31; pelvis rises and passes support; no velocity reset',
{'pelvis':[31,9],'chest':[32,5],'head':[33,2],'l_shoulder':[30,5],'l_elbow':[28,7],'l_hand':[27,9],'r_shoulder':[34,5],'r_elbow':[36,7],'r_hand':[37,9],'l_knee':[28,12],'l_foot':[26,15],'r_knee':[31,13],'r_foot':[31,17]}, {'r_foot':'!'})
add('K6','TRANSFER','TWOS','new lead contact arrives before old support fully releases','DUAL_CONTACT_TRANSFER','root x=35; support overlap stabilizes ownership handoff',
{'pelvis':[35,10],'chest':[36,6],'head':[37,3],'l_shoulder':[34,6],'l_elbow':[32,8],'l_hand':[31,10],'r_shoulder':[38,6],'r_elbow':[40,8],'r_hand':[41,10],'l_knee':[37,13],'l_foot':[41,17],'r_knee':[33,14],'r_foot':[31,17]}, {'l_foot':'?','r_foot':'!'})
add('K7','NEXT_LOAD','FOURS','new support owns root and prepares next impulse','NEW_REAR_FOOT_OWNS_ROOT','root x=39; ownership has transferred; compression readies next cycle',
{'pelvis':[39,11],'chest':[40,7],'head':[41,4],'l_shoulder':[38,7],'l_elbow':[36,9],'l_hand':[35,11],'r_shoulder':[42,7],'r_elbow':[44,9],'r_hand':[45,11],'l_knee':[41,14],'l_foot':[43,17],'r_knee':[36,14],'r_foot':[34,17]}, {'l_foot':'!','r_foot':'*'})

motion={
'schema':'ascii-kinesis.motion.v2','format_version':2,'id':'v2-locomotion-001-forward-catch-handoff','title':'ASCII Kinesis V2 Locomotion 001 — Forward Catch Handoff','lane':'locomotion',
'source':{
 'provider':'The Spriters Resource','asset_id':32,'name':'Aladdin','game':'Aladdin','platform':'SNES','section':'Playable Characters','submitter':'Silverbolt','url':'https://www.spriters-resource.com/snes/aladdin/asset/32/',
 'evidence_identity':{'dimensions':'418x736','format':'GIF','bytes':30726,'sha256':'e9928f049a519d676521ec0849930752d71efac59006b046e597c7cb0fc6ec74','gif_frames_observed':1},
 'rights_note':'Copyright-restricted source used only as whole-sheet evidence. No source pixels, palette, exact contours, frame layout, traced pose, costume, or character-specific drawing is embedded, redistributed, or closely imitated. The delivered rig is independently authored generic ASCII.',
 'whole_sheet_boundary':'The entire available 418x736 TSR sheet was inspected as one evidence corpus, including upright travel cycles, broad stride changes, low/airborne body states, vertical/hanging travel states, action families, and return/settle poses. The source page has a community comment suggesting a crouched throw may be absent; this pass treats the published sheet as the complete available evidence and does not invent omitted material.',
 'timing_evidence':'Exact source custody observed one static GIF frame containing the sheet. Sheet layout therefore establishes pose/state evidence but not exposure duration or source-authentic chronology.'
},
'evidence_split':{
 'OBSERVED':['entire available TSR asset is a single 418x736 static GIF sheet','sheet contains repeated upright travel families with changing stride extension/compression','sheet also contains low/airborne and vertical/hanging travel states, demonstrating support-state changes beyond level walking','published sheet alone does not encode playback timing'],
 'INFERRED':['generic eight-key forward support-exchange cycle','probe contact is separated from trusted support ownership','root x remains monotonic through catch compression','all ONES/TWOS/FOURS exposure classes and sequence chronology'],
 'UNKNOWN':['source-authentic frame chronology','source-authentic exposure durations','exact source ground plane','which source foot owns root in every published drawing','whether additional game poses omitted from the published sheet would alter this principle']
},
'principle':{'name':'THE CATCH ABSORBS HEIGHT, NOT FORWARD TRAVEL','summary':'In fast locomotion, first contact should not teleport the root to rest. The lead foot may probe, then earn support while the pelvis compresses vertically; forward root travel survives the catch and support ownership transfers afterward.','state_sequence':['LOAD','PUSH','CROSS','PROBE','CATCH','PASS','TRANSFER','NEXT_LOAD'],'minimal_maximal_unit':'one complete forward support-ownership handoff expressed as eight decisive ASCII rig keys, compiled without semantic tween states'},
'timing_policy':{'nominal_fps':24,'vocabulary':{'ONES':'new key/drawing every display frame','TWOS':'one key/drawing held two display frames','FOURS':'one key/drawing held four display frames','STREET_FIGHTER_CAPCOM':'nonuniform inferred gameplay timing with readable holds and fast causal joins'},'all_decisive_key_timing_provenance':'INFERRED','source_authentic_timing_claimed':False,'compile_cycle_repeats':4},
'rig':{'grid':{'width':W,'height':H,'origin':'top-left'},'facing':'RIGHT','joint_symbols':{'head':'O','pelvis':'+','joint':'o','extremity':'*','trusted_support':'!','probe_contact':'?'},'bones':bones,'source_specific_design':False,'ascii_semantic_authority':True},
'keys':keys,
'motion_dungeon':{'semantic_authority':'authored ascii_pose strings in decisive keys','hold_frames_by_class':{'ONES':1,'TWOS':2,'FOURS':4},'connective_motion':'NONE_BETWEEN_CAUSAL_KEYS','connective_rationale':'Every adjacent key changes a causal support/contact phase. The compiler fails closed instead of inventing intermediate support semantics. Motion comes from ordered authored keys plus explicit holds.','ascii_only_frame_rendering':True,'video_source':'abstract_ascii_rig_only','source_art_embedded':False,'unsupported_states_fail_closed':True,'cycle_repeats':4},
'compile_facts':{'status':'PENDING_BUILD','media_path':'motion.mp4','media_sha256':None,'media_bytes':None,'frames_per_cycle':None,'total_frames':None,'duration_seconds':None,'codec':'h264','pixel_format':'yuv420p'},
'compatibility':{'backward_compatible':True,'v1_artifacts_untouched':True,'primary_tabs':['ASCII','JSON','VIDEO'],'reader_contract':'ASCII Kinesis swarm v2; additive to existing anthology'},
'correction_hooks':['KEEP','REJECT','EXAGGERATE','COMPRESS','RETIME','CHANGE SOURCE','PROMOTE','SPAWN VARIANT','FIX BLOCKER','RERUN']
}
ENTRY.mkdir(parents=True,exist_ok=True)
(ENTRY/'motion.json').write_text(json.dumps(motion,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
