import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

EXPECTED_ACTION = 'WalkSwordCarryV2'
EXPECTED_FRAME_COUNT = 8
EXPECTED_TOTAL_MS = 820
FRAME_DURATIONS_MS = [110, 90, 100, 110, 110, 90, 100, 110]


def fail(message):
    raise SystemExit('vanguard_walk_render_failed: ' + message)


def args_after_dash():
    if '--' not in sys.argv:
        fail('missing renderer arguments')
    args = sys.argv[sys.argv.index('--') + 1:]
    if len(args) < 4:
        fail('expected input_glb output_dir settings_json manifest_json')
    return Path(args[0]), Path(args[1]), Path(args[2]), Path(args[3])


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()


def import_glb(path):
    if not path.exists():
        fail('input GLB is missing')
    bpy.ops.import_scene.gltf(filepath=str(path))
    objects = list(bpy.context.scene.objects)
    if not objects:
        fail('GLB imported no objects')
    return objects


def find_armature():
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE']
    if len(armatures) != 1:
        fail(f'expected one armature, found {len(armatures)}')
    return armatures[0]


def requested_action(settings):
    return str(settings.get('action') or settings.get('expectedAction') or EXPECTED_ACTION).strip() or EXPECTED_ACTION


def semantic_action_name(imported_name, requested):
    return requested if imported_name == requested + '_rig' else imported_name


def resolve_action(requested):
    available = sorted(a.name for a in bpy.data.actions)
    exact = [a for a in bpy.data.actions if a.name == requested]
    if len(exact) == 1:
        return exact[0], 'exact'
    if len(exact) > 1:
        fail('ambiguous exact action match for ' + requested)
    normalized_name = requested + '_rig'
    normalized = [a for a in bpy.data.actions if a.name == normalized_name]
    if len(normalized) == 1:
        return normalized[0], 'gltf_importer_suffix'
    if len(normalized) > 1:
        fail('ambiguous glTF importer _rig action match for ' + requested)
    forbidden = [name for name in available if name in {'Rest', 'Idle'}]
    suffix_note = '; Rest/Idle fallback is forbidden' if forbidden else ''
    fail('missing action ' + requested + ' or unique ' + normalized_name + '; available actions: ' + ', '.join(available[:40]) + suffix_note)


def activate_walk(armature, requested):
    action, resolution = resolve_action(requested)
    if action.name not in {requested, requested + '_rig'}:
        fail('wrong action selected: ' + action.name)
    if armature.animation_data is None:
        armature.animation_data_create()
    armature.animation_data.action = action
    if armature.animation_data.action is None or armature.animation_data.action.name != action.name:
        fail('resolved action did not become active')
    return action, resolution


def scene_bounds(objects):
    coords = []
    for obj in objects:
        if obj.type not in {'MESH', 'ARMATURE', 'EMPTY'}:
            continue
        if obj.type == 'MESH':
            for corner in obj.bound_box:
                coords.append(obj.matrix_world @ Vector(corner))
    if not coords:
        fail('no mesh bounds found')
    lo = Vector((min(v.x for v in coords), min(v.y for v in coords), min(v.z for v in coords)))
    hi = Vector((max(v.x for v in coords), max(v.y for v in coords), max(v.z for v in coords)))
    return lo, hi


def setup_scene(objects, settings):
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in [item.identifier for item in scene.render.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    samples = max(1, min(int(settings.get('samples', 64)), 128))
    if hasattr(scene, 'eevee') and hasattr(scene.eevee, 'taa_render_samples'):
        scene.eevee.taa_render_samples = samples
    scene.render.resolution_x = int(settings.get('width', 960))
    scene.render.resolution_y = int(settings.get('height', 720))
    scene.frame_start = 1
    scene.frame_end = EXPECTED_FRAME_COUNT
    scene.frame_set(1)
    lo, hi = scene_bounds(objects)
    center = (lo + hi) * 0.5
    size = hi - lo
    camera_data = bpy.data.cameras.new('vanguard_walk_locked_side_ortho_camera')
    camera = bpy.data.objects.new('vanguard_walk_locked_side_ortho_camera', camera_data)
    bpy.context.collection.objects.link(camera)
    distance = max(size.x, size.y, size.z, 1.0) * 3.0
    camera.location = (center.x + distance, center.y, center.z + max(size.z, 1.0) * 0.08)
    camera.rotation_euler = (math.radians(90), 0, math.radians(90))
    camera_data.type = 'ORTHO'
    camera_data.ortho_scale = max(size.z * 1.25, size.y * 1.25, 1.2)
    scene.camera = camera
    sun_data = bpy.data.lights.new('vanguard_walk_key_sun', 'SUN')
    sun = bpy.data.objects.new('vanguard_walk_key_sun', sun_data)
    bpy.context.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(50), 0, math.radians(35))
    sun_data.energy = 2.0
    area_data = bpy.data.lights.new('vanguard_walk_softbox', 'AREA')
    area = bpy.data.objects.new('vanguard_walk_softbox', area_data)
    bpy.context.collection.objects.link(area)
    area.location = (center.x + distance * 0.5, center.y - distance * 0.4, center.z + size.z)
    area_data.energy = 450
    area_data.size = max(size.z, 1.0)
    return camera


def render_frames(output_dir, action):
    frames_dir = output_dir / 'frames'
    fixed_dir = output_dir / 'fixed'
    diag_dir = output_dir / 'diagnostic'
    frames_dir.mkdir(parents=True, exist_ok=True)
    fixed_dir.mkdir(parents=True, exist_ok=True)
    diag_dir.mkdir(parents=True, exist_ok=True)
    start, end = action.frame_range
    if end <= start:
        fail('resolved action has invalid frame range')
    frame_values = [start + (end - start) * i / EXPECTED_FRAME_COUNT for i in range(EXPECTED_FRAME_COUNT)]
    rendered = []
    fixed = []
    diagnostics = []
    for i, frame in enumerate(frame_values):
        frame_int = math.floor(frame)
        bpy.context.scene.frame_set(frame_int, subframe=frame - frame_int)
        rel = f'frames/vanguard_walk_{i:02d}.png'
        fixed_rel = f'fixed/vanguard_walk_side_{i:02d}.png'
        bpy.context.scene.render.filepath = str(output_dir / rel)
        bpy.ops.render.render(write_still=True)
        rendered.append(rel)
        fixed_path = output_dir / fixed_rel
        fixed_path.write_bytes((output_dir / rel).read_bytes())
        fixed.append(fixed_rel)
        diagnostics.append(rel)
    return rendered, fixed, diagnostics, frame_values


def weapon_inventory():
    object_names = [obj.name for obj in bpy.context.scene.objects]
    mesh_names = [mesh.name for mesh in bpy.data.meshes]
    bone_names = []
    for armature in [obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE']:
        bone_names.extend([bone.name for bone in armature.data.bones])
    def is_sword_name(name):
        lower = name.lower()
        return 'sword' in lower or 'long_sword' in lower or (('weapon' in lower) and name != 'Weapon.R')
    sword_object_names = [name for name in object_names if is_sword_name(name)]
    sword_mesh_names = [name for name in mesh_names if is_sword_name(name)]
    counted_swords = sword_object_names if sword_object_names else sword_mesh_names
    weapon_r_present = any(name == 'Weapon.R' for name in object_names + mesh_names + bone_names)
    return {
        'objectNames': object_names,
        'meshNames': mesh_names,
        'boneNames': bone_names,
        'swordObjects': counted_swords,
        'swordObjectNames': sword_object_names,
        'swordMeshNames': sword_mesh_names,
        'swordObjectCount': len(counted_swords),
        'weaponRPresent': weapon_r_present,
    }


def main():
    input_glb, output_dir, settings_path, manifest_path = args_after_dash()
    output_dir.mkdir(parents=True, exist_ok=True)
    settings = json.loads(settings_path.read_text('utf8')) if settings_path.exists() else {}
    clear_scene()
    objects = import_glb(input_glb)
    armature = find_armature()
    expected_action = requested_action(settings)
    action, resolution = activate_walk(armature, expected_action)
    inventory = weapon_inventory()
    if not inventory['weaponRPresent']:
        fail('Weapon.R was not found in imported Vanguard GLB')
    if inventory['swordObjectCount'] != 1:
        fail('expected exactly one embedded sword object, found ' + str(inventory['swordObjectCount']))
    setup_scene(objects, settings)
    rendered, fixed, diagnostics, sampled = render_frames(output_dir, action)
    bpy.ops.wm.save_as_mainfile(filepath=str(output_dir / 'vanguard_walk.blend'))
    native = {
        'schema': 'home-center-vanguard-walk-render-v1',
        'sourcePolicy': 'exact imported GLB animation only; no retarget, reinterpretation, or re-authoring',
        'action': expected_action,
        'requestedSemanticAction': expected_action,
        'activeSemanticAction': semantic_action_name(action.name, expected_action),
        'importedActionName': action.name,
        'resolvedActiveAction': action.name,
        'actionResolution': resolution,
        'blenderAction': action.name,
        'expectedAction': expected_action,
        'frameCount': len(rendered),
        'expectedFrameCount': EXPECTED_FRAME_COUNT,
        'authoredTotalMs': EXPECTED_TOTAL_MS,
        'frameDurationsMs': FRAME_DURATIONS_MS,
        'sampledActionFrames': sampled,
        'subframeSampling': True,
        'camera': 'fixed side orthographic',
        'transparentBackground': True,
        'embeddedSwordPresent': True,
        'embeddedSwordCount': inventory['swordObjectCount'],
        'weaponRPresent': inventory['weaponRPresent'],
        'samples': int(settings.get('samples', 64)),
    }
    (output_dir / 'native-pose-animation.json').write_text(json.dumps(native, indent=2), 'utf8')
    manifest = {
        'renderedFrames': rendered,
        'fixedCameraRenders': fixed,
        'diagnosticViewRenders': diagnostics,
        'modifiedBlend': 'vanguard_walk.blend',
        'nativePoseAnimationData': 'native-pose-animation.json',
        'frameDurationsMs': FRAME_DURATIONS_MS,
        'expectedAction': expected_action,
        'expectedFrameCount': EXPECTED_FRAME_COUNT,
        'expectedTotalMs': EXPECTED_TOTAL_MS,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), 'utf8')


if __name__ == '__main__':
    main()
