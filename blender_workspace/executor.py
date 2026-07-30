import bpy
import bmesh
import hashlib
import json
import math
import os
import sys
from mathutils import Vector
from pathlib import Path

args=sys.argv[sys.argv.index('--')+1:]
REQUEST=Path(args[0]); OUT=Path(args[1]); OUT.mkdir(parents=True,exist_ok=True)
REQ=json.loads(REQUEST.read_text()); SEED=REQ.get('inputHash','seed')

def sid(*parts): return hashlib.sha256((':'.join(map(str,parts))).encode()).hexdigest()[:24]
def intid(*parts): return int(hashlib.sha256((':'.join(map(str,parts))).encode()).hexdigest()[:7],16) or 1
def vec(v,default=(0,0,0)): return Vector(tuple(v) if isinstance(v,(list,tuple)) else default)
def obj(ref):
    if isinstance(ref,str):
        for o in bpy.data.objects:
            if o.get('hc_id')==ref or o.name==ref: return o
    if isinstance(ref,dict): return obj(ref.get('objectId') or ref.get('name'))
    raise ValueError('object not found: '+str(ref))
def ensure_ids(o):
    if not o.get('hc_id'): o['hc_id']='obj_'+sid(REQ.get('workspaceId'),o.name)
    if o.data and hasattr(o.data,'get') and not o.data.get('hc_data_id'): o.data['hc_data_id']='data_'+sid(REQ.get('workspaceId'),o.get('hc_id'),'data')
    if o.type=='MESH':
        m=o.data
        for name,domain,count in [('hc_vertex_id','POINT',len(m.vertices)),('hc_edge_id','EDGE',len(m.edges)),('hc_face_id','FACE',len(m.polygons))]:
            a=m.attributes.get(name) or m.attributes.new(name=name,type='INT',domain=domain)
            seen=set()
            for i in range(count):
                value=a.data[i].value
                if value==0 or value in seen:value=intid(o.get('hc_id'),name,i,SEED);a.data[i].value=value
                seen.add(value)

def ensure_all():
    for o in bpy.data.objects: ensure_ids(o)
def deselect():
    for o in bpy.context.selected_objects: o.select_set(False)
def active(o):
    deselect(); o.select_set(True); bpy.context.view_layer.objects.active=o

def create_object(op):
    kind=op.get('type','cube').lower(); location=vec(op.get('location')); rotation=op.get('rotation',[0,0,0])
    if kind=='cube': bpy.ops.mesh.primitive_cube_add(location=location,rotation=rotation); o=bpy.context.object
    elif kind=='cylinder': bpy.ops.mesh.primitive_cylinder_add(vertices=int(op.get('vertices',32)),radius=float(op.get('radius',1)),depth=float(op.get('depth',2)),location=location,rotation=rotation); o=bpy.context.object
    elif kind=='empty': o=bpy.data.objects.new(op.get('name','Empty'),None); bpy.context.collection.objects.link(o); o.location=location; o.rotation_euler=rotation
    elif kind=='camera': d=bpy.data.cameras.new(op.get('name','Camera')); o=bpy.data.objects.new(op.get('name','Camera'),d); bpy.context.collection.objects.link(o); o.location=location; o.rotation_euler=rotation
    elif kind=='light': d=bpy.data.lights.new(op.get('name','Light'),op.get('lightType','AREA')); d.energy=float(op.get('energy',1000)); d.color=op.get('color',[1,1,1]); d.shape='DISK'; d.size=float(op.get('size',5)); o=bpy.data.objects.new(op.get('name','Light'),d); bpy.context.collection.objects.link(o); o.location=location; o.rotation_euler=rotation
    else: raise ValueError('unsupported object type '+kind)
    o.name=op.get('name',o.name); o['hc_id']=op.get('objectId') or 'obj_'+sid(REQ.get('workspaceId'),o.name,op.get('purpose',''))
    if op.get('scale'): o.scale=op['scale']
    if op.get('dimensions'): o.dimensions=op['dimensions']
    bpy.context.view_layer.update(); ensure_ids(o); return o

def collection_create(op):
    name=op['name']; c=bpy.data.collections.get(name)
    if not c: c=bpy.data.collections.new(name); bpy.context.scene.collection.children.link(c)
    c['hc_id']=op.get('collectionId') or 'col_'+sid(REQ.get('workspaceId'),name)

def transform(op):
    o=obj(op.get('objectId') or op.get('name'))
    if 'location' in op:o.location=op['location']
    if 'rotation' in op:o.rotation_euler=op['rotation']
    if 'scale' in op:o.scale=op['scale']
    if 'dimensions' in op:o.dimensions=op['dimensions']
    bpy.context.view_layer.update()
    if op.get('apply'):
        active(o); bpy.ops.object.transform_apply(location=op.get('applyLocation',False),rotation=op.get('applyRotation',False),scale=op.get('applyScale',True))

def duplicate(op,linked=False):
    src=obj(op.get('sourceObjectId') or op.get('source')); o=src.copy(); o.data=src.data if linked else (src.data.copy() if src.data else None); bpy.context.collection.objects.link(o); o.name=op['name']; o['hc_id']=op.get('objectId') or 'obj_'+sid(REQ.get('workspaceId'),o.name)
    if op.get('location'):o.location=op['location']
    if op.get('rotation'):o.rotation_euler=op['rotation']
    if op.get('scale'):o.scale=op['scale']
    ensure_ids(o); return o

def selected_verts(bm,o,criteria):
    bm.verts.ensure_lookup_table(); ids={int(v) for v in criteria.get('vertexIds',[])}; indices={int(v) for v in criteria.get('indices',[])}; bounds=criteria.get('bounds'); attr=o.data.attributes.get('hc_vertex_id'); out=[]
    for v in bm.verts:
        ok=(not ids and not indices and not bounds)
        if v.index in indices:ok=True
        if ids and attr and v.index<len(attr.data) and attr.data[v.index].value in ids:ok=True
        if bounds:
            co=v.co; ok=all(float(bounds.get(a+'Min',-1e30))<=co[i]<=float(bounds.get(a+'Max',1e30)) for i,a in enumerate('xyz'))
        if ok:out.append(v)
    expected=criteria.get('expectedSelectionCount')
    if expected is not None and len(out)!=int(expected):raise ValueError(f'selection count {len(out)} != expected {expected}')
    return out

def edit_bmesh(o,fn):
    if o.type!='MESH':raise ValueError('mesh object required')
    bm=bmesh.new(); bm.from_mesh(o.data); fn(bm); bm.normal_update(); bm.to_mesh(o.data); bm.free(); o.data.update(); ensure_ids(o)

def mesh_vertex_move(op):
    o=obj(op.get('objectId') or op.get('name')); delta=vec(op.get('delta'))
    def run(bm):
        vs=selected_verts(bm,o,op.get('selection',{}))
        for v in vs:v.co+=delta
    edit_bmesh(o,run)

def mesh_loop_cut(op):
    o=obj(op.get('objectId') or op.get('name'))
    def run(bm):
        bm.edges.ensure_lookup_table(); inds=set(op.get('edgeIndices',[])); edges=[e for e in bm.edges if not inds or e.index in inds]; expected=op.get('expectedEdgeCount')
        if expected is not None and len(edges)!=int(expected):raise ValueError('edge selection mismatch')
        bmesh.ops.subdivide_edges(bm,edges=edges,cuts=int(op.get('cuts',1)),use_grid_fill=True)
    edit_bmesh(o,run)

def face_select(bm,criteria):
    bm.faces.ensure_lookup_table(); inds=set(criteria.get('indices',[])); normal=criteria.get('normal'); threshold=float(criteria.get('normalThreshold',.9)); out=[]
    for f in bm.faces:
        ok=not inds and normal is None
        if f.index in inds:ok=True
        if normal is not None and f.normal.dot(vec(normal).normalized())>=threshold:ok=True
        if ok:out.append(f)
    expected=criteria.get('expectedSelectionCount')
    if expected is not None and len(out)!=int(expected):raise ValueError('face selection mismatch')
    return out

def mesh_inset(op):
    o=obj(op.get('objectId') or op.get('name'))
    edit_bmesh(o,lambda bm:bmesh.ops.inset_region(bm,faces=face_select(bm,op.get('selection',{})),thickness=float(op.get('thickness',.1)),depth=float(op.get('depth',0)),use_even_offset=True))
def mesh_extrude(op):
    o=obj(op.get('objectId') or op.get('name')); distance=float(op.get('distance',.1)); direction=op.get('direction')
    def run(bm):
        faces=face_select(bm,op.get('selection',{})); result=bmesh.ops.extrude_face_region(bm,geom=faces); verts=[e for e in result['geom'] if isinstance(e,bmesh.types.BMVert)]; d=vec(direction).normalized()*distance if direction else Vector((0,0,distance)); bmesh.ops.translate(bm,verts=verts,vec=d)
    edit_bmesh(o,run)
def mesh_bridge(op):
    o=obj(op.get('objectId') or op.get('name'))
    def run(bm):
        bm.edges.ensure_lookup_table(); inds=set(op.get('edgeIndices',[])); edges=[e for e in bm.edges if e.index in inds]; bmesh.ops.bridge_loops(bm,edges=edges)
    edit_bmesh(o,run)
def mesh_bevel(op):
    o=obj(op.get('objectId') or op.get('name'))
    def run(bm):
        bm.edges.ensure_lookup_table(); inds=set(op.get('edgeIndices',[])); edges=[e for e in bm.edges if not inds or e.index in inds]; bmesh.ops.bevel(bm,geom=edges,offset=float(op.get('width',.05)),segments=int(op.get('segments',2)),affect='EDGES')
    edit_bmesh(o,run)
def mesh_sharp(op):
    o=obj(op.get('objectId') or op.get('name')); sharp=bool(op.get('sharp',True))
    def run(bm):
        bm.edges.ensure_lookup_table(); inds=set(op.get('edgeIndices',[]));
        for e in bm.edges:
            if not inds or e.index in inds:e.smooth=not sharp
    edit_bmesh(o,run)

def modifier(op):
    o=obj(op.get('objectId') or op.get('name')); typ=op['type'].upper(); m=o.modifiers.new(op.get('modifierName',typ.title()),typ)
    for k,v in (op.get('settings') or {}).items():
        if hasattr(m,k):setattr(m,k,v)
    if op.get('apply'):
        active(o); bpy.ops.object.modifier_apply(modifier=m.name)
def boolean(op):
    target=obj(op.get('objectId') or op.get('target')); cutter=obj(op.get('cutterObjectId') or op.get('cutter')); active(target); m=target.modifiers.new(op.get('modifierName','Boolean'),'BOOLEAN'); m.operation=op.get('operation','DIFFERENCE'); m.solver='EXACT'; m.object=cutter; bpy.ops.object.modifier_apply(modifier=m.name)
    if op.get('deleteCutter',True): bpy.data.objects.remove(cutter,do_unlink=True)
    ensure_ids(target)
def parent(op):
    child=obj(op.get('objectId') or op.get('child')); par=obj(op.get('parentObjectId') or op.get('parent')); world=child.matrix_world.copy(); child.parent=par
    if op.get('keepWorld',True):child.matrix_world=world
def origin(op):
    o=obj(op.get('objectId') or op.get('name')); point=vec(op.get('point')); scene=bpy.context.scene; old=scene.cursor.location.copy(); scene.cursor.location=point; active(o); bpy.ops.object.origin_set(type='ORIGIN_CURSOR'); scene.cursor.location=old
def join(op):
    objects=[obj(x) for x in op.get('objects',[])]; active(objects[0]);
    for o in objects:o.select_set(True)
    bpy.ops.object.join(); bpy.context.object.name=op.get('name',bpy.context.object.name); ensure_ids(bpy.context.object)
def constraint(op):
    o=obj(op.get('objectId') or op.get('name')); c=o.constraints.new(op['type']); c.name=op.get('constraintName',c.name)
    if op.get('target'):c.target=obj(op['target'])
    for k,v in (op.get('settings') or {}).items():
        if hasattr(c,k):setattr(c,k,v)
def material(op):
    name=op['name']; m=bpy.data.materials.get(name) or bpy.data.materials.new(name); m.diffuse_color=tuple(op.get('color',[.5,.5,.5,1])); m.metallic=float(op.get('metallic',0)); m.roughness=float(op.get('roughness',.5))
    if op.get('objectId') or op.get('object'):
        o=obj(op.get('objectId') or op.get('object'))
        if m.name not in [x.name for x in o.data.materials]:o.data.materials.append(m)
def smooth(op):
    o=obj(op.get('objectId') or op.get('name'))
    for p in o.data.polygons:p.use_smooth=bool(op.get('smooth',True))
def uv(op):
    o=obj(op.get('objectId') or op.get('name')); active(o); bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.smart_project(angle_limit=float(op.get('angleLimit',math.radians(66)))); bpy.ops.object.mode_set(mode='OBJECT')
def action(op):
    o=obj(op.get('objectId') or op.get('name')); action_name=op['action']; data_path=op.get('dataPath','rotation_euler'); index=int(op.get('index',0)); act=bpy.data.actions.new(action_name+'.'+o.name); o.animation_data_create(); o.animation_data.action=act
    for frame,value in op.get('keys',[]):
        setattr_value=o.path_resolve(data_path); setattr_value[index]=float(value); o.keyframe_insert(data_path=data_path,index=index,frame=float(frame),group=action_name)
    for fc in act.fcurves:
        for kp in fc.keyframe_points:kp.interpolation=op.get('interpolation','LINEAR')
    track=o.animation_data.nla_tracks.new(); track.name=action_name; track.strips.new(action_name,int(op.get('start',1)),act); o.animation_data.action=None

def apply_op(op):
    name=op.get('op')
    if name=='collection.create':collection_create(op)
    elif name=='object.create':create_object(op)
    elif name=='object.duplicate':duplicate(op,False)
    elif name in ('object.linked_duplicate','instance.create'):duplicate(op,True)
    elif name=='object.delete':bpy.data.objects.remove(obj(op.get('objectId') or op.get('name')),do_unlink=True)
    elif name=='object.rename':obj(op.get('objectId') or op.get('name')).name=op['newName']
    elif name in ('object.transform','object.dimensions'):transform(op)
    elif name=='object.parent':parent(op)
    elif name in ('object.origin','object.pivot'):origin(op)
    elif name=='mesh.vertex_move':mesh_vertex_move(op)
    elif name in ('mesh.loop_cut','mesh.support_loop'):mesh_loop_cut(op)
    elif name=='mesh.inset':mesh_inset(op)
    elif name=='mesh.extrude':mesh_extrude(op)
    elif name=='mesh.bridge':mesh_bridge(op)
    elif name=='mesh.bevel':mesh_bevel(op)
    elif name in ('mesh.sharp','mesh.crease'):mesh_sharp(op)
    elif name=='mesh.boolean':boolean(op)
    elif name in ('modifier.add','modifier.apply'):modifier({**op,'apply':name=='modifier.apply' or op.get('apply')})
    elif name in ('mesh.normals','mesh.smooth'):smooth(op)
    elif name=='mesh.join':join(op)
    elif name=='constraint.add':constraint(op)
    elif name=='material.create' or name=='material.assign':material(op)
    elif name=='uv.smart_project':uv(op)
    elif name in ('animation.keyframes','animation.action'):action(op)
    elif name=='workspace.restore':pass
    else:raise ValueError('unsupported typed Blender operation '+str(name))

def open_scene():
    source=REQ.get('sourcePath')
    if source and REQ.get('sourceFormat')=='blend':bpy.ops.wm.open_mainfile(filepath=source,load_ui=False,use_scripts=False)
    elif source and REQ.get('sourceFormat')=='glb':
        bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=source)
    else:bpy.ops.wm.read_factory_settings(use_empty=True)
    ensure_all()

def inspect_scene():
    objects=[]; warnings=[]
    for o in sorted(bpy.data.objects,key=lambda x:x.name):
        ensure_ids(o); item={'objectId':o.get('hc_id'),'dataId':o.data.get('hc_data_id') if o.data and hasattr(o.data,'get') else None,'name':o.name,'type':o.type,'parentId':o.parent.get('hc_id') if o.parent else None,'collections':sorted(c.name for c in o.users_collection),'transform':{'location':list(o.location),'rotationEuler':list(o.rotation_euler),'scale':list(o.scale)},'dimensions':list(o.dimensions),'originWorld':list(o.matrix_world.translation),'modifiers':[{'name':m.name,'type':m.type} for m in o.modifiers],'constraints':[{'name':c.name,'type':c.type,'targetId':c.target.get('hc_id') if getattr(c,'target',None) else None} for c in o.constraints],'materials':[m.name for m in getattr(o.data,'materials',[]) if m]}
        if o.type=='MESH':
            m=o.data;m.calc_loop_triangles(); bm=bmesh.new();bm.from_mesh(m); boundary=sum(1 for e in bm.edges if len(e.link_faces)==1); nonmanifold=sum(1 for e in bm.edges if len(e.link_faces)!=2); components=0; unseen=set(bm.verts)
            while unseen:
                components+=1; stack=[unseen.pop()]
                while stack:
                    v=stack.pop()
                    for e in v.link_edges:
                        n=e.other_vert(v)
                        if n in unseen:unseen.remove(n);stack.append(n)
            bm.free(); item['mesh']={'vertices':len(m.vertices),'edges':len(m.edges),'faces':len(m.polygons),'triangles':len(m.loop_triangles),'boundaryEdges':boundary,'nonManifoldEdges':nonmanifold,'connectedComponents':components,'boundsLocal':{'min':list(map(min,zip(*[v.co for v in m.vertices]))) if m.vertices else [0,0,0],'max':list(map(max,zip(*[v.co for v in m.vertices]))) if m.vertices else [0,0,0]},'linkedUsers':m.users}
            va=m.attributes.get('hc_vertex_id');ea=m.attributes.get('hc_edge_id');fa=m.attributes.get('hc_face_id');limit=20000
            item['componentCatalog']={'truncated':len(m.vertices)+len(m.edges)+len(m.polygons)>limit,'vertices':[{'vertexId':va.data[v.index].value,'index':v.index,'co':list(v.co)} for v in m.vertices[:limit]],'edges':[{'edgeId':ea.data[e.index].value,'index':e.index,'vertices':list(e.vertices)} for e in m.edges[:limit]],'faces':[{'faceId':fa.data[f.index].value,'index':f.index,'vertices':list(f.vertices),'center':list(f.center),'normal':list(f.normal)} for f in m.polygons[:limit]]}
            if item['componentCatalog']['truncated']:warnings.append({'code':'component_catalog_truncated','objectId':o.get('hc_id'),'limit':limit})
            if boundary: warnings.append({'code':'open_boundaries','objectId':o.get('hc_id'),'count':boundary})
        objects.append(item)
    actions=[]
    for a in bpy.data.actions:
        channels=[]
        for fc in a.fcurves:channels.append({'dataPath':fc.data_path,'arrayIndex':fc.array_index,'keyframes':[kp.co.x for kp in fc.keyframe_points]})
        actions.append({'name':a.name,'frameRange':list(a.frame_range),'channels':channels})
    return {'contractVersion':'home-center.blender-scene-inspection.v1','workspaceId':REQ.get('workspaceId'),'revisionId':REQ.get('revisionId'),'objects':objects,'collections':[{'name':c.name,'collectionId':c.get('hc_id'),'objectIds':[o.get('hc_id') for o in c.objects]} for c in bpy.data.collections],'actions':actions,'cameras':[o.get('hc_id') for o in bpy.data.objects if o.type=='CAMERA'],'lights':[o.get('hc_id') for o in bpy.data.objects if o.type=='LIGHT'],'warnings':warnings,'blenderVersion':bpy.app.version_string}

def validate_scene(inspection):
    deg=[]; duplicate=[]; coplanar=[]
    for o in bpy.data.objects:
        if o.type!='MESH':continue
        for p in o.data.polygons:
            if p.area<1e-10:deg.append({'objectId':o.get('hc_id'),'face':p.index})
        seen={}
        for p in o.data.polygons:
            key=tuple(round(x,6) for x in (*p.center,*p.normal))
            if key in seen:coplanar.append({'objectId':o.get('hc_id'),'faces':[seen[key],p.index]})
            else:seen[key]=p.index
    names={}
    for o in bpy.data.objects:names.setdefault(o.name,0);names[o.name]+=1
    duplicate=[n for n,c in names.items() if c>1]
    open_edges=sum((x.get('mesh') or {}).get('boundaryEdges',0) for x in inspection['objects']); non=sum((x.get('mesh') or {}).get('nonManifoldEdges',0) for x in inspection['objects'])
    broken=[]
    for o in bpy.data.objects:
        for c in o.constraints:
            if hasattr(c,'target') and c.target is None:broken.append({'objectId':o.get('hc_id'),'constraint':c.name})
    intersections=[];meshes=[o for o in bpy.data.objects if o.type=='MESH']
    for i,a in enumerate(meshes):
        ab=[a.matrix_world@Vector(c) for c in a.bound_box];amin=Vector((min(v.x for v in ab),min(v.y for v in ab),min(v.z for v in ab)));amax=Vector((max(v.x for v in ab),max(v.y for v in ab),max(v.z for v in ab)))
        for b in meshes[i+1:]:
            bb=[b.matrix_world@Vector(c) for c in b.bound_box];bmin=Vector((min(v.x for v in bb),min(v.y for v in bb),min(v.z for v in bb)));bmax=Vector((max(v.x for v in bb),max(v.y for v in bb),max(v.z for v in bb)))
            overlap=[min(amax[j],bmax[j])-max(amin[j],bmin[j]) for j in range(3)]
            if min(overlap)>1e-5:intersections.append({'objectA':a.get('hc_id'),'objectB':b.get('hc_id'),'aabbOverlap':overlap,'classification':'potential-unintended-intersection'})
    valid=open_edges==0 and non==0 and not deg and not duplicate and not coplanar and not broken and not intersections
    return {'contractVersion':'home-center.blender-validation.v1','workspaceId':REQ.get('workspaceId'),'revisionId':REQ.get('revisionId'),'openBoundaryEdges':open_edges,'nonManifoldEdges':non,'degenerateFaces':deg,'duplicateNames':duplicate,'coplanarDuplicateCandidates':coplanar,'brokenConstraints':broken,'missingAnimationTargets':[],'potentialIntersections':intersections,'glbWarnings':[],'vertexCount':sum((x.get('mesh') or {}).get('vertices',0) for x in inspection['objects']),'triangleCount':sum((x.get('mesh') or {}).get('triangles',0) for x in inspection['objects']),'machineValid':valid,'humanAcceptance':'unreviewed'}

def setup_camera(location,target=(0,0,0),ortho=False):
    c=bpy.data.cameras.new('Review_Camera'); cam=bpy.data.objects.new('Review_Camera',c); bpy.context.scene.collection.objects.link(cam); cam.location=location; direction=Vector(target)-cam.location; cam.rotation_euler=direction.to_track_quat('-Z','Y').to_euler(); c.type='ORTHO' if ortho else 'PERSP'; c.ortho_scale=10; c.lens=52; bpy.context.scene.camera=cam; return cam

def setup_light(location,energy=1600,size=5):
    d=bpy.data.lights.new('Review_Key','AREA');d.energy=energy;d.shape='DISK';d.size=size;o=bpy.data.objects.new('Review_Key',d);bpy.context.scene.collection.objects.link(o);o.location=location;o.rotation_euler=(Vector((0,0,0))-o.location).to_track_quat('-Z','Y').to_euler()
def render_views():
    scene=bpy.context.scene; scene.render.engine='BLENDER_EEVEE_NEXT'; scene.render.resolution_x=640;scene.render.resolution_y=480;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'; scene.world.color=(.035,.035,.045); scene.view_settings.look='AgX - Medium High Contrast'
    clay=bpy.data.materials.new('Review_Clay');clay.diffuse_color=(.32,.36,.38,1);clay.metallic=.05;clay.roughness=.6
    for o in bpy.data.objects:
        if o.type=='MESH':o.data.materials.clear();o.data.materials.append(clay)
    points=[Vector(c) for o in bpy.data.objects if o.type=='MESH' for c in o.bound_box]
    center=Vector((0,0,0)); radius=5
    if points:
        world=[o.matrix_world@Vector(c) for o in bpy.data.objects if o.type=='MESH' for c in o.bound_box]; center=sum(world,Vector())/len(world); radius=max((p-center).length for p in world)*1.6
    views={'front':(center.x-radius,center.y,center.z),'rear':(center.x+radius,center.y,center.z),'side':(center.x,center.y-radius,center.z),'top':(center.x,center.y,center.z+radius),'three-quarter':(center.x-radius*.75,center.y-radius*.75,center.z+radius*.5)}
    setup_light((center.x-radius,center.y-radius,center.z+radius),1800,radius)
    cam=None
    for name,loc in views.items():
        if cam:bpy.data.objects.remove(cam,do_unlink=True)
        cam=setup_camera(loc,center,name!='three-quarter');cam.data.ortho_scale=radius*1.45;scene.render.filepath=str(OUT/f'clay-{name}.png');bpy.ops.render.render(write_still=True)
    for o in bpy.data.objects:
        if o.type=='MESH':
            wire=bpy.data.materials.get('Review_Wire') or bpy.data.materials.new('Review_Wire');wire.diffuse_color=(.02,.02,.02,1);o.data.materials.append(wire);m=o.modifiers.new('Review_Wire','WIREFRAME');m.thickness=max(radius*.002,.004);m.material_offset=1
    for name in ('front','side','three-quarter'):
        loc=views[name]; bpy.data.objects.remove(cam,do_unlink=True);cam=setup_camera(loc,center,name!='three-quarter');cam.data.ortho_scale=radius*1.45;scene.render.filepath=str(OUT/f'wire-{name}.png');bpy.ops.render.render(write_still=True)
    for o in bpy.data.objects:
        if o.type=='MESH' and o.modifiers.get('Review_Wire'):o.modifiers.remove(o.modifiers['Review_Wire'])
    for o in list(bpy.data.objects):
        if o.type=='LIGHT':bpy.data.objects.remove(o,do_unlink=True)
    setup_light((center.x-radius*1.2,center.y-radius*.1,center.z+radius*.15),2400,radius*.35);bpy.data.objects.remove(cam,do_unlink=True);cam=setup_camera(views['three-quarter'],center,False);scene.render.filepath=str(OUT/'raking-three-quarter.png');bpy.ops.render.render(write_still=True)
    if bpy.data.actions:
        scene.render.resolution_x=480;scene.render.resolution_y=360;scene.frame_start=1;scene.frame_end=min(72,max(2,int(max(a.frame_range[1] for a in bpy.data.actions))));scene.render.image_settings.file_format='FFMPEG';scene.render.ffmpeg.format='MPEG4';scene.render.ffmpeg.codec='H264';scene.render.ffmpeg.constant_rate_factor='MEDIUM';scene.render.filepath=str(OUT/'animation-preview.mp4');bpy.ops.render.render(animation=True)

def export_scene():
    bpy.ops.export_scene.gltf(filepath=str(OUT/'scene.glb'),export_format='GLB',export_animations=True,export_animation_mode='NLA_TRACKS',export_force_sampling=True,export_apply=False)

open_scene(); kind=REQ.get('operation')
if kind in ('create','mutate'):
    for operation in REQ.get('recipe',{}).get('operations',[]):apply_op(operation)
    ensure_all(); inspection=inspect_scene(); validation=validate_scene(inspection); bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'scene.blend'),check_existing=False); (OUT/'inspection.json').write_text(json.dumps(inspection,indent=2));(OUT/'validation.json').write_text(json.dumps(validation,indent=2))
elif kind=='restore':
    ensure_all();inspection=inspect_scene();validation=validate_scene(inspection);bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'scene.blend'),check_existing=False);(OUT/'inspection.json').write_text(json.dumps(inspection,indent=2));(OUT/'validation.json').write_text(json.dumps(validation,indent=2))
elif kind=='render':render_views()
elif kind=='export':
    inspection=inspect_scene();validation=validate_scene(inspection);export_scene();shutil=None
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'scene.blend'),check_existing=False);(OUT/'inspection.json').write_text(json.dumps(inspection,indent=2));(OUT/'validation.json').write_text(json.dumps(validation,indent=2))
else:raise ValueError('unsupported operation kind '+str(kind))
