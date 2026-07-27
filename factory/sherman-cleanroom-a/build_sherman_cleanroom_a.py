"""Clean-room Blender build for a late Fisher M4A3(75)W Sherman.

This script imports no prior tank mesh or build script.  It starts from an empty
factory scene, creates the model with Blender geometry, saves the native .blend,
exports a GLB, and renders a review ring.
"""

import argparse
import json
import math
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector


ASSET_ID = "M4A3_75W_CLEANROOM_A"
INCH = 0.0254


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    return parser.parse_args(argv)


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)
    assert len(bpy.context.scene.objects) == 0


def material(name, color, metallic=0.0, roughness=0.55):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def finish(obj, name, mat=None, smooth=False):
    obj.name = name
    if mat:
        obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.use_smooth = smooth
    return obj


def apply_modifier(obj, name):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=name)
    obj.select_set(False)


def bevel(obj, width=0.025, segments=2):
    mod = obj.modifiers.new("Manufactured edge radii", "BEVEL")
    mod.width = width
    mod.segments = segments
    mod.limit_method = "ANGLE"
    mod.angle_limit = math.radians(24)
    apply_modifier(obj, mod.name)
    return obj


def cube(name, location, scale, mat, bevel_width=0.02, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(location=location, rotation=rotation)
    obj = bpy.context.object
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel_width:
        bevel(obj, bevel_width, 2)
    return finish(obj, name, mat)


def cylinder(
    name,
    location,
    radius,
    depth,
    mat,
    vertices=32,
    rotation=(math.pi / 2, 0, 0),
    bevel_width=0.012,
    smooth=True,
):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        end_fill_type="NGON",
        location=location,
        rotation=rotation,
    )
    obj = bpy.context.object
    if bevel_width:
        bevel(obj, bevel_width, 2)
    return finish(obj, name, mat, smooth)


def uv_sphere(name, location, scale, mat, segments=48, rings=24):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments, ring_count=rings, location=location
    )
    obj = bpy.context.object
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(obj, name, mat, True)


def mesh_from_rings(name, rings, mat, cap=True, smooth=False):
    """rings: [(z, [(x,y), ...]), ...] with consistent vertex counts."""
    vertices = []
    faces = []
    count = len(rings[0][1])
    for z, points in rings:
        vertices.extend((x, y, z) for x, y in points)
    for r in range(len(rings) - 1):
        a = r * count
        b = (r + 1) * count
        for i in range(count):
            j = (i + 1) % count
            faces.append((a + i, a + j, b + j, b + i))
    if cap:
        faces.append(tuple(reversed(range(count))))
        top = (len(rings) - 1) * count
        faces.append(tuple(top + i for i in range(count)))
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return finish(obj, name, mat, smooth)


def box_ring(x_rear, x_front, half_width):
    return [
        (x_rear, -half_width),
        (x_front, -half_width),
        (x_front, half_width),
        (x_rear, half_width),
    ]


def parent_keep(child, parent):
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()


def make_hull(armor, dark, bare):
    hull_root = bpy.data.objects.new("HULL_ROOT", None)
    bpy.context.collection.objects.link(hull_root)

    lower = mesh_from_rings(
        "Hull_Lower_WeldedTub",
        [
            (0.42, box_ring(-2.52, 2.55, 0.90)),
            (0.78, box_ring(-2.62, 2.67, 1.08)),
        ],
        armor,
    )
    bevel(lower, 0.035, 3)
    parent_keep(lower, hull_root)

    upper = mesh_from_rings(
        "Hull_Upper_47degLargeHatch",
        [
            (0.76, box_ring(-2.58, 2.69, 1.08)),
            (1.58, box_ring(-2.31, 1.82, 1.28)),
        ],
        armor,
    )
    bevel(upper, 0.028, 2)
    parent_keep(upper, hull_root)

    roof = cube(
        "Hull_Roof_Armor",
        (-0.18, 0, 1.585),
        (2.12, 1.27, 0.035),
        armor,
        0.018,
    )
    parent_keep(roof, hull_root)

    rear = cube(
        "Hull_Rear_Armor",
        (-2.52, 0, 1.16),
        (0.10, 1.20, 0.42),
        armor,
        0.025,
        rotation=(0, math.radians(-10), 0),
    )
    parent_keep(rear, hull_root)

    # Three-piece cast differential housing: broad rounded nose, bolted seams.
    diff = uv_sphere(
        "Transmission_Cover_Cast",
        (2.55, 0, 0.73),
        (0.46, 1.22, 0.50),
        armor,
        48,
        24,
    )
    parent_keep(diff, hull_root)
    for y in (-0.43, 0.43):
        seam = cube(
            f"Transmission_Cover_Joint_{y:+.2f}",
            (2.89, y, 0.75),
            (0.018, 0.018, 0.35),
            bare,
            0.006,
            rotation=(0, math.radians(-8), 0),
        )
        parent_keep(seam, hull_root)
        for z in (0.50, 0.67, 0.84, 1.01):
            bolt = cylinder(
                f"Transmission_Bolt_{y:+.2f}_{z:.2f}",
                (2.92, y, z),
                0.025,
                0.025,
                dark,
                vertices=12,
                rotation=(0, math.pi / 2, 0),
                bevel_width=0.003,
            )
            parent_keep(bolt, hull_root)

    # Large driver and bow-gunner hatches seated on the 47-degree plate.
    for label, y in (("Driver", -0.57), ("BowGunner", 0.57)):
        hatch = cube(
            f"{label}_LargeHatch_Solid",
            (2.04, y, 1.38),
            (0.34, 0.27, 0.045),
            armor,
            0.055,
            rotation=(0, math.radians(46.5), 0),
        )
        parent_keep(hatch, hull_root)
        hinge = cylinder(
            f"{label}_Hatch_Hinge",
            (1.80, y, 1.58),
            0.055,
            0.46,
            dark,
            vertices=20,
            rotation=(math.pi / 2, 0, 0),
            bevel_width=0.008,
        )
        parent_keep(hinge, hull_root)
        periscope = cube(
            f"{label}_Periscope_Guard",
            (1.88, y, 1.63),
            (0.10, 0.08, 0.12),
            armor,
            0.018,
        )
        parent_keep(periscope, hull_root)

    # Bow machine-gun ball and barrel.
    ball = uv_sphere("Bow_MG_BallMount", (2.26, 0.63, 1.25), (0.19, 0.19, 0.19), armor)
    parent_keep(ball, hull_root)
    mg = cylinder(
        "Bow_M1919_Barrel",
        (2.54, 0.63, 1.25),
        0.026,
        0.45,
        dark,
        vertices=20,
        rotation=(0, math.pi / 2, 0),
        bevel_width=0.004,
    )
    parent_keep(mg, hull_root)

    # Engine deck: raised plate, grilles, armored filler caps, rear exhausts.
    deck = cube(
        "Engine_Deck",
        (-1.55, 0, 1.66),
        (0.77, 1.20, 0.045),
        armor,
        0.018,
    )
    parent_keep(deck, hull_root)
    for y in (-0.58, 0.0, 0.58):
        grille = cube(
            f"Engine_Grille_{y:+.2f}",
            (-1.62, y, 1.715),
            (0.55, 0.20, 0.018),
            dark,
            0.008,
        )
        parent_keep(grille, hull_root)
        for x in (-1.98, -1.80, -1.62, -1.44, -1.26):
            slat = cube(
                f"Engine_Grille_Slat_{y:+.2f}_{x:+.2f}",
                (x, y, 1.738),
                (0.015, 0.18, 0.014),
                bare,
                0.003,
            )
            parent_keep(slat, hull_root)
    for y in (-0.91, 0.91):
        cap = cylinder(
            f"Fuel_Filler_Cap_{y:+.2f}",
            (-1.18, y, 1.74),
            0.11,
            0.045,
            armor,
            vertices=24,
            rotation=(0, 0, 0),
            bevel_width=0.01,
        )
        parent_keep(cap, hull_root)
        exhaust = cylinder(
            f"Rear_Exhaust_{y:+.2f}",
            (-2.68, y, 0.86),
            0.09,
            0.40,
            dark,
            vertices=24,
            rotation=(0, math.pi / 2, 0),
            bevel_width=0.006,
        )
        parent_keep(exhaust, hull_root)

    # Fenders and welded side strips.
    for y in (-1.38, 1.38):
        fender = cube(
            f"Fender_{'L' if y < 0 else 'R'}",
            (-0.02, y, 1.10),
            (2.60, 0.08, 0.035),
            armor,
            0.012,
        )
        parent_keep(fender, hull_root)
        rail = cube(
            f"Fender_Rail_{'L' if y < 0 else 'R'}",
            (-0.02, y + (-0.07 if y < 0 else 0.07), 1.16),
            (2.55, 0.018, 0.065),
            armor,
            0.006,
        )
        parent_keep(rail, hull_root)

    # Headlights, guards, tow lugs, and lifting eyes carry the front identity.
    for y in (-0.91, 0.91):
        lamp = cylinder(
            f"Headlamp_{y:+.2f}",
            (2.22, y, 1.49),
            0.09,
            0.10,
            dark,
            vertices=24,
            rotation=(0, math.pi / 2, 0),
            bevel_width=0.008,
        )
        parent_keep(lamp, hull_root)
        guard = cube(
            f"Headlamp_Guard_{y:+.2f}",
            (2.19, y, 1.58),
            (0.16, 0.025, 0.025),
            armor,
            0.01,
            rotation=(0, math.radians(-12), 0),
        )
        parent_keep(guard, hull_root)
        lug = cube(
            f"Tow_Lug_{y:+.2f}",
            (2.83, y, 0.48),
            (0.14, 0.07, 0.13),
            armor,
            0.03,
        )
        parent_keep(lug, hull_root)
    return hull_root


def turret_ring_points(z, cx, front_radius, rear_radius, half_width, count=64):
    pts = []
    for i in range(count):
        angle = 2.0 * math.pi * i / count
        c = math.cos(angle)
        radius_x = front_radius if c >= 0 else rear_radius
        pts.append((cx + radius_x * c, half_width * math.sin(angle)))
    return z, pts


def make_turret(armor, dark, bare):
    traverse = bpy.data.objects.new("TURRET_TRAVERSE_PIVOT", None)
    traverse.location = (-0.05, 0, 1.64)
    bpy.context.collection.objects.link(traverse)

    turret = mesh_from_rings(
        "Turret_D78461_HighBustle_Cast",
        [
            turret_ring_points(1.67, -0.05, 0.88, 0.91, 0.88),
            turret_ring_points(1.79, -0.07, 0.99, 1.06, 0.95),
            turret_ring_points(2.10, -0.10, 1.03, 1.16, 0.98),
            turret_ring_points(2.39, -0.12, 0.92, 1.08, 0.88),
            turret_ring_points(2.52, -0.13, 0.72, 0.88, 0.70),
        ],
        armor,
        True,
        True,
    )
    bevel(turret, 0.025, 3)
    parent_keep(turret, traverse)

    ring = cylinder(
        "Turret_Ring_69in",
        (-0.05, 0, 1.66),
        34.5 * INCH,
        0.12,
        dark,
        vertices=64,
        rotation=(0, 0, 0),
        bevel_width=0.012,
    )
    parent_keep(ring, traverse)

    gun_pivot = bpy.data.objects.new("GUN_ELEVATION_PIVOT", None)
    gun_pivot.location = (0.91, 0, 2.16)
    bpy.context.collection.objects.link(gun_pivot)
    parent_keep(gun_pivot, traverse)

    mantlet = cube(
        "M34A1_Wide_Gun_Shield",
        (1.00, 0, 2.16),
        (0.20, 0.60, 0.38),
        armor,
        0.09,
    )
    parent_keep(mantlet, gun_pivot)
    rotor = cylinder(
        "M34A1_Rotor_Shield",
        (1.15, 0, 2.16),
        0.29,
        0.56,
        armor,
        vertices=48,
        rotation=(math.pi / 2, 0, 0),
        bevel_width=0.025,
    )
    rotor.scale.z = 1.18
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    parent_keep(rotor, gun_pivot)

    # Tapered 75 mm M3 barrel in three real sections, with a bored muzzle.
    barrel_specs = [
        ("Gun_Barrel_Base", 1.57, 0.105, 0.90),
        ("Gun_Barrel_Mid", 2.32, 0.080, 0.72),
        ("Gun_Barrel_Muzzle", 2.94, 0.066, 0.54),
    ]
    for name, x, radius, depth in barrel_specs:
        part = cylinder(
            name,
            (x, 0, 2.16),
            radius,
            depth,
            armor if "Base" in name else dark,
            vertices=32,
            rotation=(0, math.pi / 2, 0),
            bevel_width=0.008,
        )
        parent_keep(part, gun_pivot)
    bore = cylinder(
        "Gun_Muzzle_Bore",
        (3.225, 0, 2.16),
        0.040,
        0.018,
        dark,
        vertices=32,
        rotation=(0, math.pi / 2, 0),
        bevel_width=0,
    )
    parent_keep(bore, gun_pivot)

    # Commander cupola, split hatch, loader hatch, periscopes, lifting eyes.
    cupola = cylinder(
        "Commander_Cupola",
        (-0.24, -0.48, 2.62),
        0.34,
        0.21,
        armor,
        vertices=48,
        rotation=(0, 0, 0),
        bevel_width=0.025,
    )
    parent_keep(cupola, traverse)
    for i, dx in enumerate((-0.17, 0.17)):
        hatch = cube(
            f"Commander_Hatch_Half_{i+1}",
            (-0.24 + dx, -0.48, 2.755),
            (0.15, 0.29, 0.035),
            armor,
            0.045,
        )
        parent_keep(hatch, traverse)
    loader = cylinder(
        "Loader_Hatch_Solid",
        (-0.10, 0.52, 2.57),
        0.28,
        0.065,
        armor,
        vertices=40,
        rotation=(0, 0, 0),
        bevel_width=0.025,
    )
    parent_keep(loader, traverse)
    for x, y in ((0.33, -0.38), (0.32, 0.38), (-0.55, 0.0)):
        peri = cube(
            f"Turret_Periscope_{x:+.2f}_{y:+.2f}",
            (x, y, 2.56),
            (0.09, 0.07, 0.12),
            armor,
            0.018,
        )
        parent_keep(peri, traverse)
    for y in (-0.72, 0.72):
        eye = cylinder(
            f"Turret_Lifting_Eye_{y:+.2f}",
            (-0.42, y, 2.40),
            0.065,
            0.045,
            bare,
            vertices=20,
            rotation=(math.pi / 2, 0, 0),
            bevel_width=0.006,
        )
        parent_keep(eye, traverse)
    return traverse


def make_bogie(name, x, y, armor, rubber, dark, side):
    root = bpy.data.objects.new(name, None)
    root.location = (x, y, 0)
    bpy.context.collection.objects.link(root)
    housing = cube(
        name + "_CastHousing",
        (x, y, 0.72),
        (0.46, 0.18, 0.34),
        armor,
        0.055,
    )
    parent_keep(housing, root)
    spring = cube(
        name + "_VoluteSpring",
        (x, y, 0.76),
        (0.16, 0.205, 0.27),
        dark,
        0.035,
    )
    parent_keep(spring, root)
    for index, dx in enumerate((-0.30, 0.30)):
        wheel = cylinder(
            f"{name}_RoadWheel_{index+1}",
            (x + dx, y, 0.42),
            0.31,
            0.18,
            rubber,
            vertices=40,
            rotation=(math.pi / 2, 0, 0),
            bevel_width=0.015,
        )
        parent_keep(wheel, root)
        hub = cylinder(
            f"{name}_RoadWheelHub_{index+1}",
            (x + dx, y + side * 0.105, 0.42),
            0.13,
            0.055,
            armor,
            vertices=32,
            rotation=(math.pi / 2, 0, 0),
            bevel_width=0.01,
        )
        parent_keep(hub, root)
        arm = cube(
            f"{name}_TrailingArm_{index+1}",
            (x + dx * 0.52, y, 0.56),
            (0.23, 0.08, 0.055),
            armor,
            0.025,
            rotation=(0, math.radians(-25 * (1 if dx > 0 else -1)), 0),
        )
        parent_keep(arm, root)
    roller = cylinder(
        name + "_ReturnRoller",
        (x + 0.16, y, 1.07),
        0.14,
        0.17,
        rubber,
        vertices=32,
        rotation=(math.pi / 2, 0, 0),
        bevel_width=0.01,
    )
    parent_keep(roller, root)
    return root


def make_sprocket(name, x, y, armor, dark, side):
    root = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(root)
    disc = cylinder(
        name + "_Disc",
        (x, y, 0.68),
        0.43,
        0.19,
        armor,
        vertices=48,
        rotation=(math.pi / 2, 0, 0),
        bevel_width=0.018,
    )
    parent_keep(disc, root)
    hub = cylinder(
        name + "_Hub",
        (x, y + side * 0.12, 0.68),
        0.15,
        0.07,
        dark,
        vertices=32,
        rotation=(math.pi / 2, 0, 0),
        bevel_width=0.008,
    )
    parent_keep(hub, root)
    for i in range(13):
        a = 2 * math.pi * i / 13
        tooth = cube(
            f"{name}_Tooth_{i:02d}",
            (x + 0.45 * math.cos(a), y, 0.68 + 0.45 * math.sin(a)),
            (0.065, 0.12, 0.055),
            dark,
            0.012,
            rotation=(0, -a, 0),
        )
        parent_keep(tooth, root)
    return root


def path_points():
    points = [(-2.15, 1.15), (2.15, 1.15)]
    for i in range(1, 17):
        a = math.pi / 2 - math.pi * i / 16
        points.append((2.15 + 0.49 * math.cos(a), 0.66 + 0.49 * math.sin(a)))
    points.append((-2.15, 0.17))
    for i in range(1, 17):
        a = -math.pi / 2 - math.pi * i / 16
        points.append((-2.15 + 0.49 * math.cos(a), 0.66 + 0.49 * math.sin(a)))
    return points


def sample_closed_path(points, count):
    closed = points + [points[0]]
    lengths = []
    total = 0.0
    for a, b in zip(closed, closed[1:]):
        length = math.dist(a, b)
        lengths.append(length)
        total += length
    samples = []
    for i in range(count):
        target = total * i / count
        acc = 0.0
        for seg, length in enumerate(lengths):
            if target <= acc + length or seg == len(lengths) - 1:
                t = (target - acc) / max(length, 1e-8)
                a = Vector(closed[seg])
                b = Vector(closed[seg + 1])
                p = a.lerp(b, t)
                tangent = (b - a).normalized()
                samples.append((p.x, p.y, math.atan2(tangent.y, tangent.x)))
                break
            acc += length
    return samples


def make_shoe_source(track, bare):
    parts = []
    base = cube("T48_Shoe_Source_Base", (0, 0, 0), (0.064, 0.205, 0.032), track, 0.008)
    parts.append(base)
    for sign in (-1, 1):
        bar = cube(
            f"T48_Shoe_Chevron_{sign:+d}",
            (0, sign * 0.085, 0.042),
            (0.052, 0.075, 0.018),
            bare,
            0.005,
            rotation=(0, 0, sign * math.radians(28)),
        )
        parts.append(bar)
    horn = cube("T48_Shoe_GuideHorn", (0, 0, 0.095), (0.035, 0.035, 0.070), track, 0.008)
    parts.append(horn)
    bpy.ops.object.select_all(action="DESELECT")
    for part in parts:
        part.select_set(True)
    bpy.context.view_layer.objects.active = base
    bpy.ops.object.join()
    base.name = "T48_TRACK_SHOE_CANONICAL"
    return base


def make_running_gear(armor, track, rubber, dark, bare):
    root = bpy.data.objects.new("RUNNING_GEAR_ROOT", None)
    bpy.context.collection.objects.link(root)
    for side, y in ((-1, -1.18), (1, 1.18)):
        side_name = "L" if side < 0 else "R"
        for index, x in enumerate((-1.55, 0.0, 1.55)):
            bogie = make_bogie(f"VVSS_{side_name}_Bogie_{index+1}", x, y, armor, rubber, dark, side)
            parent_keep(bogie, root)
        sprocket = make_sprocket(f"Sprocket_{side_name}", 2.18, y, armor, dark, side)
        parent_keep(sprocket, root)
        idler = cylinder(
            f"Idler_{side_name}",
            (-2.18, y, 0.66),
            0.42,
            0.19,
            rubber,
            vertices=48,
            rotation=(math.pi / 2, 0, 0),
            bevel_width=0.018,
        )
        parent_keep(idler, root)
        idler_hub = cylinder(
            f"IdlerHub_{side_name}",
            (-2.18, y + side * 0.12, 0.66),
            0.15,
            0.07,
            armor,
            vertices=32,
            rotation=(math.pi / 2, 0, 0),
            bevel_width=0.008,
        )
        parent_keep(idler_hub, root)

    source = make_shoe_source(track, bare)
    source.hide_render = True
    source.hide_viewport = True
    shoe_mesh = source.data
    samples = sample_closed_path(path_points(), 79)
    for side, y in ((-1, -1.39), (1, 1.39)):
        side_name = "L" if side < 0 else "R"
        for index, (x, z, angle) in enumerate(samples):
            shoe = bpy.data.objects.new(f"T48_{side_name}_Shoe_{index:02d}", shoe_mesh)
            bpy.context.collection.objects.link(shoe)
            shoe.location = (x, y, z)
            shoe.rotation_euler = (0, -angle, 0)
            parent_keep(shoe, root)
    return root


def add_weld_lines(hull_root, bare):
    # Raised weld beads are geometry because they stabilize plate boundaries.
    lines = [
        ((1.83, -1.23, 1.58), (1.83, 1.23, 1.58), "GlacisTop"),
        ((-2.30, -1.23, 1.58), (-2.30, 1.23, 1.58), "RearRoof"),
    ]
    for start, end, label in lines:
        midpoint = (Vector(start) + Vector(end)) * 0.5
        length = (Vector(end) - Vector(start)).length
        bead = cylinder(
            f"Weld_Bead_{label}",
            midpoint,
            0.018,
            length,
            bare,
            vertices=12,
            rotation=(math.pi / 2, 0, 0),
            bevel_width=0.003,
        )
        parent_keep(bead, hull_root)


def add_markings(hull_root, white):
    # Star uses five narrow bars as actual geometry; no UV dependency.
    center = (-0.45, -1.305, 1.47)
    for i in range(5):
        bar = cube(
            f"LeftHull_StarArm_{i}",
            center,
            (0.22, 0.010, 0.028),
            white,
            0.006,
            rotation=(math.pi / 2, 0, 2 * math.pi * i / 5),
        )
        parent_keep(bar, hull_root)


def setup_lighting():
    world = bpy.context.scene.world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.035, 0.045, 0.055, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.32
    lights = [
        ("Key", (6.5, -5.5, 8.0), 1800, 5.0),
        ("Fill", (-4.0, -2.5, 5.0), 1050, 4.0),
        ("Rim", (-4.5, 5.0, 6.5), 1550, 3.5),
    ]
    for name, location, energy, size in lights:
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        obj = bpy.data.objects.new(name, data)
        obj.location = location
        bpy.context.collection.objects.link(obj)
        direction = Vector((0, 0, 1.1)) - obj.location
        obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def setup_ground(mat):
    ground = cube("Review_Ground", (0, 0, -0.09), (6.5, 6.5, 0.08), mat, 0.06)
    ground.display_type = "SOLID"


def camera_at(name, location, target, lens=58):
    data = bpy.data.cameras.new(name)
    data.lens = lens
    data.sensor_width = 36
    obj = bpy.data.objects.new(name, data)
    obj.location = location
    obj.rotation_euler = (Vector(target) - Vector(location)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.collection.objects.link(obj)
    return obj


def render_review_ring(output):
    scene = bpy.context.scene
    scene.render.engine = (
        "BLENDER_EEVEE_NEXT"
        if bpy.app.version >= (4, 2, 0)
        else "BLENDER_EEVEE"
    )
    scene.render.resolution_x = 768
    scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.image_settings.compression = 15
    scene.render.resolution_percentage = 100
    views = {
        "front": ((7.7, 0, 2.15), (0, 0, 1.25), 62),
        "left": ((0, -7.5, 2.15), (0, 0, 1.25), 62),
        "rear": ((-7.7, 0, 2.15), (0, 0, 1.25), 62),
        "right": ((0, 7.5, 2.15), (0, 0, 1.25), 62),
        "top": ((0, 0, 10.2), (0, 0, 1.0), 66),
        "front_three_quarter": ((6.4, -6.4, 4.0), (0, 0, 1.15), 62),
        "rear_three_quarter": ((-6.4, 6.4, 3.7), (0, 0, 1.15), 62),
        "low_front_three_quarter": ((5.8, 5.3, 1.30), (0.2, 0, 1.05), 58),
    }
    rendered = []
    camera = None
    for name, (location, target, lens) in views.items():
        if camera:
            bpy.data.objects.remove(camera, do_unlink=True)
        camera = camera_at("REVIEW_CAMERA", location, target, lens)
        scene.camera = camera
        path = output / f"{name}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        rendered.append(path.name)
    return rendered


def mesh_stats():
    triangles = 0
    vertices = 0
    mesh_objects = 0
    unique_meshes = set()
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH" or obj.name == "Review_Ground":
            continue
        mesh_objects += 1
        unique_meshes.add(obj.data.as_pointer())
        vertices += len(obj.data.vertices)
        triangles += sum(max(0, len(poly.vertices) - 2) for poly in obj.data.polygons)
    return {
        "meshObjects": mesh_objects,
        "uniqueMeshes": len(unique_meshes),
        "logicalVerticesAcrossInstances": vertices,
        "logicalTrianglesAcrossInstances": triangles,
    }


def main():
    args = parse_args()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    clear_scene()

    armor = material("Olive_Drab_319", (0.17, 0.20, 0.095), 0.05, 0.66)
    dark = material("Gunmetal_Dark", (0.035, 0.040, 0.038), 0.62, 0.28)
    bare = material("Polished_Wear", (0.24, 0.25, 0.23), 0.78, 0.22)
    rubber = material("Roadwheel_Rubber", (0.025, 0.025, 0.022), 0.0, 0.82)
    track = material("Track_Manganese_Steel", (0.085, 0.078, 0.062), 0.70, 0.36)
    white = material("Recognition_White", (0.62, 0.63, 0.57), 0.02, 0.72)
    ground_mat = material("Studio_Ground", (0.075, 0.085, 0.095), 0.0, 0.78)

    hull = make_hull(armor, dark, bare)
    make_turret(armor, dark, bare)
    make_running_gear(armor, track, rubber, dark, bare)
    add_weld_lines(hull, bare)
    add_markings(hull, white)
    setup_ground(ground_mat)
    setup_lighting()

    # Explicit clean-room evidence: no linked/imported libraries or images.
    assert not bpy.data.libraries
    assert not [
        image
        for image in bpy.data.images
        if image.source == "FILE" and str(image.filepath or "").strip()
    ]
    assert bpy.data.objects.get("TURRET_TRAVERSE_PIVOT")
    assert bpy.data.objects.get("GUN_ELEVATION_PIVOT")
    assert len([o for o in bpy.data.objects if o.name.startswith("T48_L_Shoe_")]) == 79
    assert len([o for o in bpy.data.objects if o.name.startswith("T48_R_Shoe_")]) == 79

    stats = mesh_stats()
    blend_path = output / "sherman-m4a3-75w-cleanroom-a.blend"
    glb_path = output / "sherman-m4a3-75w-cleanroom-a.glb"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), compress=True)
    bpy.ops.export_scene.gltf(
        filepath=str(glb_path),
        export_format="GLB",
        export_apply=True,
        export_yup=True,
        export_cameras=False,
        export_lights=False,
    )
    rendered = render_review_ring(output)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), compress=True)

    manifest = {
        "schema": "sherman-factory.cleanroom-build.v1",
        "assetId": ASSET_ID,
        "status": "unreviewed_candidate",
        "cleanRoom": {
            "startsFromFactoryEmptyScene": True,
            "importsPriorGeometry": False,
            "importsPriorScripts": False,
            "externalLibraries": 0,
            "externalImages": 0,
        },
        "variant": {
            "designation": "Late Fisher M4A3(75)W",
            "hull": "47-degree welded large-hatch wet-stowage hull",
            "turret": "D78461 high-bustle 75 mm cast turret",
            "gunMount": "M34A1",
            "suspension": "VVSS",
            "track": "T48-style rigid shoes, 79 per side",
        },
        "sourcedDimensions": {
            "overallLengthIn": 247.0,
            "overallWidthIn": 105.0,
            "cupolaHeightIn": 115.7,
            "turretRingInsideDiameterIn": 69.0,
            "treadIn": 83.0,
            "groundClearanceIn": 17.0,
            "upperGlacisDegreesFromVertical": 47.0,
        },
        "axes": {"length": "+X front", "width": "Y", "height": "Z", "units": "meters"},
        "mechanicalHierarchy": {
            "turretTraverse": "TURRET_TRAVERSE_PIVOT",
            "gunElevation": "GUN_ELEVATION_PIVOT",
            "runningGear": "RUNNING_GEAR_ROOT",
        },
        "geometry": stats,
        "outputs": {
            "blend": blend_path.name,
            "glb": glb_path.name,
            "reviewRenders": rendered,
        },
        "referenceProvenance": [
            {
                "title": "Medium Tank M4A3(75)W (Late production) specification sheet",
                "url": "https://www.theshermantank.com/wp-content/uploads/M4A3-75w-spec-sheet.pdf",
                "usedFor": "overall dimensions, 69-inch ring, 47-degree upper glacis",
            },
            {
                "title": "AFV Database — Medium Tank M4 Sherman",
                "url": "https://afvdatabase.com/usa/m4sherman.html",
                "usedFor": "track pitch, width, 79 shoes, ground-contact relationship",
            },
            {
                "title": "Sherman Minutia — Sherman 75 mm turrets",
                "url": "https://the.shadock.free.fr/sherman_minutia/turret_types/75mm_turrets.html",
                "usedFor": "D78461 high-bustle turret and M34A1 identity",
            },
        ],
        "rejectionGate": [
            "must read unmistakably as late large-hatch M4A3(75)W in front, side, rear, top, and three-quarter views",
            "turret must read as a purposeful high-bustle casting, not a sphere or turnip",
            "wheels must occupy the track opening and visibly meet the lower run",
            "79 rigid shoes per side must remain discrete around returns",
            "solid hatches and M34A1 mount must survive the target review distance",
            "no promotion without human visual acceptance",
        ],
    }
    (output / "build-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "assetId": ASSET_ID, "output": str(output), "stats": stats}))


if __name__ == "__main__":
    main()
