# Ministry of Substance Design-ur

Status: candidate
Owner: DRU / material-systems layer
Canonical ministry: `MINISTRY_OF_SUBSTANCE_DESIGN_UR`

## Purpose

Turn material identity into a manipulable design system.

The Ministry treats wood, glass, silicone, steel, ceramic, resin, rubber, flesh-like synthetic matter, paint, coatings, composites, and future substrates as behaviors with causes, not as decorative texture labels.

Canonical commission:

> NO SUBSTANCE SHALL REMAIN MERELY WHAT IT WAS SOLD AS.

The joke spelling is canonical: **Substance Design-ur**.

## Governing law

A material treatment is not finished because it looks plausible in one frame. It must expose enough of its causal grammar that the result can be varied, reconstructed, combined, or deliberately broken.

`material = substrate + structure + interface + history + environment + transformation`

If those terms cannot be named at least approximately, the work is styling rather than Substance Design-ur.

## Ministry primitives

### SUBSTANCE_SPEC

The bounded description of what a material is allowed to do.

Minimum fields:

- substrate;
- scale;
- structural organization;
- surface response;
- deformation / fracture / flow behavior when relevant;
- environmental response;
- fabrication or rendering constraints;
- parameters that are intentionally variable.

### EDGEWARE

Canonical term for boundary-conditioned material behavior.

Edges, seams, holes, flanges, couplers, folds, contacts, wear zones, stress risers, interfaces, and transitions are not afterthoughts. They are where a material proves what it is.

Edgeware answers questions such as:

- what accumulates here?
- what abrades here?
- what stretches, chips, scars, oxidizes, smears, compresses, delaminates, or stays clean here?
- what changes because this region touches another material?

### WEAR_CAUSE_MAP

Wear must have a reason.

A mark without a cause is decoration. A causal wear map associates visible change with contact, motion, pressure, heat, moisture, age, tooling, handling, manufacturing, maintenance, or another explicit source.

### PROCEDURAL_RECIPE

A reproducible transformation from bounded inputs to a family of material outcomes.

Seeds, randomness, thresholds, masks, fields, noise, graph structure, and mathematical abstractions are allowed. If variation affects the result, the variation source must be explicit enough to reproduce or intentionally vary.

### MATERIAL_LINEAGE

A transformed substance does not erase its ancestry.

Record enough lineage to answer:

`what was this -> what happened to it -> what did it become`

A descendant may solve a different problem from its parent. Failure as one implementation does not erase value as ancestral material.

## Procedure

1. **Name the substrate.** Start with the actual or intended material, not the shader trick.
2. **Name the forces.** Contact, gravity, tension, compression, abrasion, heat, chemistry, growth, cutting, polishing, handling, age, or another explicit cause.
3. **Find the interfaces.** Identify edges, seams, joins, voids, penetrations, contact zones, and transitions before polishing broad surfaces.
4. **Choose the abstraction.** Use the smallest mathematical or procedural rule that can produce meaningful variation.
5. **Expose controls.** Convert the abstraction into parameters a human or downstream tool can intentionally manipulate.
6. **Generate a family, not one lucky frame.** Confirm the rule survives variation.
7. **Inspect causality.** Remove marks, wear, or structure that cannot be explained by the material history unless deliberate fantasy behavior is part of the spec.
8. **Preserve lineage.** Record source, transformation, and resulting material identity.
9. **Export the useful denominator.** Bake, mesh, texture, shader, node graph, recipe, reference sheet, or other artifact only after the generative rule is understood well enough to survive export.

## Irresponsible abstractions

Mathematics is encouraged to behave irresponsibly only when the irresponsibility is inspectable.

A beautiful equation, field, noise function, graph, simulation, or procedural stack earns its place when it produces a controllable material distinction.

FAIL: abstraction exists mainly to sound clever.

PASS: changing the abstraction's exposed controls causes predictable, useful changes in the material family.

## PASS / FAIL

PASS when the material can be recognized as a bounded system with explicit causes, interfaces, controllable variation, and enough provenance to reconstruct or descend from it.

FAIL when the output is a one-off texture treatment with no causal story, when random variation cannot be reproduced, when wear is sprinkled uniformly, when edges are ignored, or when the underlying material can be swapped without changing any meaningful rule.

Repair:

`name substance -> name forces -> inspect interfaces -> expose parameters -> generate family -> preserve lineage`

## Scope boundary

The Ministry does not claim authority over every visual style, model, or fabrication decision.

It owns the question:

> What is this substance doing, why is it doing that, and how can the behavior become a reusable design primitive?

It may collaborate with Fleshpunk, ordinary-object training, Blender/Godot pipelines, image generation, industrial design, toy making, procedural generation, or future ministries without collapsing those domains into material science.

## First standing joke, retained as a test fixture

`stainless steel` is a material claim, not an immunity spell.

The Ministry may stain it when the causal history justifies the result.
