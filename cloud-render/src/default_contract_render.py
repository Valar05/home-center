import json
import math
import os
import sys

import bpy
from mathutils import Vector

REQUIRED_VIEWS = {
    'front': (0, -1, 0.35),
    'side': (1, 0, 0.35),
    'top': (0, -0.05, 1.4),
    'front_3q': (0.75, -1, 0.45),
}


def argv_after_separator():
    if '--' not in sys.argv:
        return []
    return sys.argv[sys.argv.index('--') + 1:]


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()


def import_glb(path):
    bpy.ops.import_scene.gltf(filepath=path)
    return list(bpy.context.scene.objects)


def mesh_bounds(objects):
    points = []
    for obj in objects:
        if obj.type != 'MESH':
            continue
        for corner in obj.bound_box:
            points.append(obj.matrix_world @ Vector(corner))
    if not points:
        return Vector((0, 0, 0)), 1.0
    mn = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    mx = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    radius = max((mx - mn).length * 0.5, 0.5)
    return (mn + mx) * 0.5, radius


def look_at(obj, target):
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()


def setup_light(center, radius):
    key_data = bpy.data.lights.new('Key', type='AREA')
    key = bpy.data.objects.new('Key', key_data)
    bpy.context.collection.objects.link(key)
    key.location = center + Vector((radius * 2.5, -radius * 3.0, radius * 3.0))
    key.data.energy = 600
    key.data.size = max(2.0, radius)
    fill_data = bpy.data.lights.new('Fill', type='POINT')
    fill = bpy.data.objects.new('Fill', fill_data)
    bpy.context.collection.objects.link(fill)
    fill.location = center + Vector((-radius * 2.0, radius * 1.8, radius * 1.5))
    fill.data.energy = 100


def ensure_camera(name, center, radius, direction):
    cam_data = bpy.data.cameras.new(name)
    cam = bpy.data.objects.new(name, cam_data)
    bpy.context.collection.objects.link(cam)
    vec = Vector(direction)
    if vec.length == 0:
        vec = Vector((0.75, -1, 0.45))
    vec.normalize()
    cam.location = center + vec * radius * 3.2
    cam.data.lens = 45
    look_at(cam, center + Vector((0, 0, radius * 0.1)))
    return cam


def render(path, camera, width, height):
    bpy.context.scene.camera = camera
    bpy.context.scene.render.filepath = path
    bpy.context.scene.render.resolution_x = width
    bpy.context.scene.render.resolution_y = height
    bpy.ops.render.render(write_still=True)


def main():
    args = argv_after_separator()
    if len(args) < 4:
        raise SystemExit('Usage after --: glb output_dir settings_json manifest_json')
    glb_path, output_dir, settings_path, script_manifest_path = args[:4]
    with open(settings_path, 'r', encoding='utf-8') as fh:
        settings = json.load(fh)
    os.makedirs(output_dir, exist_ok=True)
    frames_dir = os.path.join(output_dir, 'frames')
    diagnostic_dir = os.path.join(output_dir, 'diagnostic')
    os.makedirs(frames_dir, exist_ok=True)
    os.makedirs(diagnostic_dir, exist_ok=True)

    clear_scene()
    objects = import_glb(glb_path)
    center, radius = mesh_bounds(objects)
    setup_light(center, radius)
    bpy.context.scene.render.engine = settings.get('engine', 'BLENDER_EEVEE_NEXT')
    width = int(settings.get('width', 1280))
    height = int(settings.get('height', 960))

    fixed_cameras = settings.get('fixedCameras') or ['front_3q']
    diagnostic_views = settings.get('diagnosticViews') or ['front', 'side', 'top']
    rendered_frames = []
    fixed = []
    diagnostics = []
    for name in fixed_cameras:
        cam = ensure_camera('fixed_' + str(name), center, radius, REQUIRED_VIEWS.get(str(name), REQUIRED_VIEWS['front_3q']))
        out = os.path.join(frames_dir, str(name) + '.png')
        render(out, cam, width, height)
        rendered_frames.append(out)
        fixed.append(out)
    for name in diagnostic_views:
        cam = ensure_camera('diagnostic_' + str(name), center, radius, REQUIRED_VIEWS.get(str(name), REQUIRED_VIEWS['front']))
        out = os.path.join(diagnostic_dir, str(name) + '.png')
        render(out, cam, width, height)
        diagnostics.append(out)

    blend_path = os.path.join(output_dir, 'modified.blend')
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    glb_out = os.path.join(output_dir, 'animated.glb')
    bpy.ops.export_scene.gltf(filepath=glb_out, export_format='GLB')
    native_data = {
        'schema': 'command-center.native-pose-animation.v1',
        'objectCount': len(objects),
        'armatures': [obj.name for obj in objects if obj.type == 'ARMATURE'],
        'meshes': [obj.name for obj in objects if obj.type == 'MESH'],
        'actions': [action.name for action in bpy.data.actions],
        'bounds': {'center': [center.x, center.y, center.z], 'radius': radius},
    }
    native_path = os.path.join(output_dir, 'native-pose-animation.json')
    with open(native_path, 'w', encoding='utf-8') as fh:
        json.dump(native_data, fh, indent=2)
    with open(script_manifest_path, 'w', encoding='utf-8') as fh:
        json.dump({
            'renderedFrames': rendered_frames,
            'fixedCameraRenders': fixed,
            'diagnosticViewRenders': diagnostics,
            'modifiedBlend': blend_path,
            'animatedGlb': glb_out,
            'nativePoseAnimationData': native_path,
            'blenderVersion': bpy.app.version_string,
            'settings': settings,
        }, fh, indent=2)


if __name__ == '__main__':
    main()
