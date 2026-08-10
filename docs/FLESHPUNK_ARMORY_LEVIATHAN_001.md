# Fleshpunk Armory — Specimen 001: Crimson Iron Leviathan

## Mission
Turn the existing Meshy smart-topology Crimson Iron Leviathan GLB into reusable manufacturing memory without destroying its authored part boundaries.

The target configuration is the existing fleshpunk Great War tank reference: armored landship anatomy with organic/mechanical integration and canonical bacon-tread locomotor structures. Mapping from generated parts to target anatomy may be approximate; provenance must remain explicit.

## Texture decision
Do **not** block slicing on texture generation.

Geometry identity and material identity are separate layers. First preserve the exact source GLB and enumerate/slice every existing Meshy part. If Meshy can texture the same smart-topology asset without changing object/part identity, ingest that as a sibling enrichment artifact and attach its materials to the already-stable part IDs. Never replace the untextured geometry source with a textured regeneration whose boundaries cannot be proven identical.

This preserves a clean shape corpus for future quota-free learning while still capturing Meshy's texture knowledge.

## Factory loop
1. Ingest immutable source GLB and goal reference with hashes/provenance.
2. Inspect scene graph, meshes, materials, transforms, vertex/face counts, bounds, and stable part ordering.
3. Preserve each Meshy part as a stable `part_id` based on source hash + object/primitive identity; do not join meshes.
4. Slice every part into a standardized diagnostic contact sheet: perspective, front, rear, left, right, top, bottom, silhouette/wireframe where useful.
5. Produce a machine-readable parts ledger containing source identity, geometry statistics, dimensions, transforms, material slots, symmetry/repetition hints, attachment candidates, and confidence-scored semantic categories.
6. Categorize first by geometry/manufacturing role, then by Fleshpunk semantic role. Examples: plate/shell, beam/rib, tube/barrel, ring/socket, wheel/disc, articulated segment, cable/tendon, organic mass, ornament, fastener/detail, unknown. Semantic labels such as `bacon_tread` are allowed only where evidence supports them.
7. Map parts/groups approximately to goal anatomy: hull, glacis, superstructure, gun/mantlet, side armor, locomotor/tread organs, suspension/roadwheel analogues, tendons/cabling, ornament, unknown.
8. Generate assembly/exploded overview renders with numbered part IDs and category overlays.
9. Register reusable geometry signatures so later specimens can retrieve/adapt known shapes before spending Meshy quota.
10. Reassemble from registered parts and render comparison evidence.

## Required outputs
- `source_manifest.json`
- `parts.json`
- per-part diagnostic images
- numbered exploded contact sheet(s)
- category contact sheet(s)
- `goal_mapping.json`
- reassembled GLB or blend/export artifact
- comparison renders
- execution receipt containing hashes and counts

## Acceptance
Acceptance is not "script exists" or "Blender ran".

PASS requires:
- every source mesh/primitive represented exactly once in the parts ledger;
- no silent joining or loss of Meshy smart-topology boundaries;
- every part has diagnostic visual evidence;
- every part has a geometry category or explicit `unknown`;
- repeated/symmetric components are identified where measurable;
- goal mapping distinguishes confident, approximate, and unknown correspondences;
- reassembly preserves source transforms closely enough to reproduce the source configuration;
- artifacts and receipts are durable through Home Center/GitHub-authorized lanes.

## Texture enrichment acceptance
A Meshy texture pass is accepted only if source geometry correspondence can be verified by stable counts/topology or an explicit mapping. Otherwise it remains a visual reference, not canonical geometry.
