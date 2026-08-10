from __future__ import annotations
import argparse, hashlib, json, math, os, sys, time
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument('--source', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--specimen', default='leviathan-001')
    p.add_argument('--views', default='front,rear,left,right,top,bottom')
    p.add_argument('--resolution', type=int, default=512)
    return p.parse_args(argv)


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras, bpy.data.lights):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)


def world_bounds(obj):
    corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    mins = [min(v[i] for v in corners) for i in range(3)]
    maxs = [max(v[i] for v in corners) for i in range(3)]
    return mins, maxs


def dimensions(obj):
    mins, maxs = world_bounds(obj)
    return [maxs[i] - mins[i] for i in range(3)]


def classify_dims(dims, verts, faces):
    eps = 1e-8
    ordered = sorted([max(float(x), eps) for x in dims])
    a, b, c = ordered
    flat = a / c
    mid = b / c
    if c <= eps * 10:
        return 'unknown'
    if flat < 0.12 and mid > 0.45:
        return 'plate_shell'
    if mid < 0.30:
        return 'tube_beam'
    if flat < 0.25 and mid > 0.70:
        return 'disc_wheel'
    if verts < 120 and faces < 200:
        return 'fastener_detail'
    if max(dims) / max(min(dims), eps) > 4.5:
        return 'articulated_segment'
    return 'organic_mass_or_housing'


def stable_id(source_sha, source_name, component_index, obj):
    mesh = obj.data
    dims = dimensions(obj)
    payload = f'{source_sha}:{source_name}:{component_index}:{len(mesh.vertices)}:{len(mesh.polygons)}:' + ','.join(f'{x:.8f}' for x in dims)
    return 'part_' + hashlib.sha256(payload.encode()).hexdigest()[:16]


def separate_loose(mesh_objects):
    parts = []
    source_rows = []
    for source_index, obj in enumerate(mesh_objects):
        source_name = obj.name
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        before = set(bpy.context.scene.objects)
        try:
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.separate(type='LOOSE')
            bpy.ops.object.mode_set(mode='OBJECT')
        except RuntimeError:
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
            except Exception:
                pass
        after = [x for x in bpy.context.scene.objects if x.type == 'MESH' and (x == obj or x not in before)]
        if not after:
            after = [obj]
        after.sort(key=lambda x: x.name)
        for component_index, part in enumerate(after):
            parts.append((source_index, source_name, component_index, part))
        source_rows.append({'sourceObjectIndex': source_index, 'sourceObjectName': source_name, 'componentCount': len(after)})
        for x in bpy.context.scene.objects:
            x.select_set(False)
    return parts, source_rows


def ensure_material(name, rgba=(0.6, 0.6, 0.6, 1.0)):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = rgba
    return mat


def add_camera():
    data = bpy.data.cameras.new('ArmoryCamera')
    cam = bpy.data.objects.new('ArmoryCamera', data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    data.type = 'ORTHO'
    return cam


def add_lights():
    world = bpy.context.scene.world
    world.color = (0.04, 0.04, 0.04)
    for name, loc, energy in [
        ('Key', (4, -6, 6), 1800), ('Fill', (-5, -2, 3), 1000), ('Rim', (2, 5, 5), 1200)
    ]:
        ld = bpy.data.lights.new(name, 'AREA')
        ld.energy = energy
        ld.shape = 'DISK'
        ld.size = 5
        lo = bpy.data.objects.new(name, ld)
        lo.location = loc
        bpy.context.collection.objects.link(lo)


def point_camera(cam, center, distance, axis):
    axis_v = Vector(axis).normalized()
    cam.location = center + axis_v * distance
    direction = center - cam.location
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()


def hide_all(parts, hidden=True):
    for row in parts:
        row[3].hide_render = hidden


def render_single_view(obj, cam, out_path, axis, resolution):
    hide = obj.hide_render
    obj.hide_render = False
    mins, maxs = world_bounds(obj)
    center = Vector([(mins[i] + maxs[i]) / 2 for i in range(3)])
    dims = [maxs[i] - mins[i] for i in range(3)]
    span = max(max(dims), 0.001)
    cam.data.ortho_scale = span * 1.35
    point_camera(cam, center, span * 3.0 + 1.0, axis)
    scene = bpy.context.scene
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = str(out_path)
    bpy.ops.render.render(write_still=True)
    obj.hide_render = hide


def view_axis(name):
    return {
        'front': (0, -1, 0), 'rear': (0, 1, 0),
        'left': (-1, 0, 0), 'right': (1, 0, 0),
        'top': (0, 0, 1), 'bottom': (0, 0, -1),
        'iso': (1, -1, 0.8),
    }[name]


def add_label(text, location, scale):
    curve = bpy.data.curves.new('label', type='FONT')
    curve.body = text
    curve.align_x = 'CENTER'
    curve.size = max(scale * 0.11, 0.02)
    obj = bpy.data.objects.new('label', curve)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (math.radians(90), 0, 0)
    return obj


def render_overview(part_rows, out_path, resolution=1600, category=None):
    selected = [r for r in part_rows if category is None or r['category'] == category]
    if not selected:
        return None
    original = {}
    for row in part_rows:
        obj = row['_obj']
        original[obj.name] = (obj.matrix_world.copy(), obj.hide_render)
        obj.hide_render = obj not in [r['_obj'] for r in selected]
    cols = max(1, math.ceil(math.sqrt(len(selected))))
    cell = max(max(row['dimensions']) for row in selected) * 1.8
    labels = []
    for i, row in enumerate(selected):
        obj = row['_obj']
        x = (i % cols) * cell
        y = -(i // cols) * cell
        obj.location += Vector((x - obj.location.x, y - obj.location.y, -obj.location.z))
        labels.append(add_label(row['partId'], (x, y - cell * 0.42, cell * 0.02), cell))
    cam = bpy.context.scene.camera
    rows = math.ceil(len(selected) / cols)
    center = Vector(((cols - 1) * cell / 2, -(rows - 1) * cell / 2, 0))
    span = max(cols, rows) * cell
    cam.data.ortho_scale = span * 1.1
    point_camera(cam, center, span * 2 + 2, (0, -0.15, 1))
    scene = bpy.context.scene
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = str(out_path)
    bpy.ops.render.render(write_still=True)
    for label in labels:
        bpy.data.objects.remove(label, do_unlink=True)
    for row in part_rows:
        obj = row['_obj']
        matrix, hidden = original[obj.name]
        obj.matrix_world = matrix
        obj.hide_render = hidden
    return str(out_path)


def main():
    args = parse_args()
    source = Path(args.source).resolve()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    parts_dir = out / 'parts'
    parts_dir.mkdir(exist_ok=True)
    source_sha = file_sha(source)

    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(source))
    imported_meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    imported_meshes.sort(key=lambda o: o.name)
    original_object_count = len(imported_meshes)
    separated, source_rows = separate_loose(imported_meshes)
    parts = [x[3] for x in separated]
    add_lights()
    cam = add_camera()
    hide_all(separated, True)

    rows = []
    views = [v.strip() for v in args.views.split(',') if v.strip() in {'front','rear','left','right','top','bottom','iso'}]
    if not views:
        views = ['front','rear','left','right','top','bottom']

    for source_index, source_name, component_index, obj in separated:
        dims = dimensions(obj)
        part_id = stable_id(source_sha, source_name, component_index, obj)
        category = classify_dims(dims, len(obj.data.vertices), len(obj.data.polygons))
        diag = []
        for view in views:
            path = parts_dir / f'{part_id}_{view}.png'
            render_single_view(obj, cam, path, view_axis(view), args.resolution)
            diag.append({'view': view, 'path': str(path)})
        mins, maxs = world_bounds(obj)
        rows.append({
            'partId': part_id,
            'sourceObjectIndex': source_index,
            'sourceObjectName': source_name,
            'componentIndex': component_index,
            'meshName': obj.data.name,
            'vertices': len(obj.data.vertices),
            'edges': len(obj.data.edges),
            'faces': len(obj.data.polygons),
            'dimensions': dims,
            'bounds': {'min': mins, 'max': maxs},
            'worldMatrix': [list(row) for row in obj.matrix_world],
            'materials': [m.name if m else None for m in obj.data.materials],
            'category': category,
            'semanticCategory': 'unknown',
            'semanticConfidence': 0.0,
            'diagnostics': diag,
            '_obj': obj,
        })

    overview = render_overview(rows, out / 'contact_sheet_all_parts.png')
    category_sheets = {}
    for cat in sorted(set(r['category'] for r in rows)):
        path = render_overview(rows, out / f'contact_sheet_category_{cat}.png', category=cat)
        if path:
            category_sheets[cat] = path

    for r in rows:
        r.pop('_obj', None)
    ledger = {
        'schemaVersion': 'fleshpunk-armory.parts.v1',
        'specimen': args.specimen,
        'source': {'path': str(source), 'sha256': source_sha, 'bytes': source.stat().st_size},
        'originalMeshObjectCount': original_object_count,
        'sourceObjects': source_rows,
        'partCount': len(rows),
        'categories': {cat: sum(1 for r in rows if r['category'] == cat) for cat in sorted(set(r['category'] for r in rows))},
        'parts': rows,
        'contactSheetAllParts': overview,
        'categorySheets': category_sheets,
        'generatedAtMs': int(time.time() * 1000),
    }
    parts_json = out / 'parts.json'
    parts_json.write_text(json.dumps(ledger, indent=2) + '\n')

    # Export the separated-but-source-positioned assembly as an independent reconstruction artifact.
    for o in bpy.context.scene.objects:
        o.select_set(o.type == 'MESH')
        if o.type == 'MESH':
            o.hide_render = False
    reassembled = out / 'reassembled.glb'
    bpy.ops.export_scene.gltf(filepath=str(reassembled), export_format='GLB', use_selection=True)
    receipt = {
        'schemaVersion': 'fleshpunk-armory.slice-receipt.v1',
        'specimen': args.specimen,
        'sourceSha256': source_sha,
        'partCount': len(rows),
        'partsJson': str(parts_json),
        'contactSheetAllParts': overview,
        'categorySheets': category_sheets,
        'reassembled': {'path': str(reassembled), 'sha256': file_sha(reassembled), 'bytes': reassembled.stat().st_size},
        'completedAtMs': int(time.time() * 1000),
    }
    receipt_path = out / 'slice_receipt.json'
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
