import {createHash} from 'node:crypto';
import {Document, NodeIO, Accessor, getBounds, Logger, Verbosity} from '@gltf-transform/core';
import {KHRONOS_EXTENSIONS} from '@gltf-transform/extensions';
import {Matrix4, Quaternion, Vector3} from 'three';
import initManifold from 'manifold-3d';
import {MeshoptDecoder, MeshoptEncoder} from 'meshoptimizer';
import {createSubdivisionCage, fitSubdivisionCageToModelSheet, subdivideCage} from './foundry_model_sheet.mjs';

export const FOUNDRY_KERNEL_VERSION = 'fortress-model-foundry.v2';
export const FOUNDRY_RUN_VERSION = 'home-center.foundry-run.v2';
const MAX_VERTICES = 250000;
const MAX_TRIANGLES = 500000;
const SUPPORTED_VIEWS = Object.freeze(['front', 'back', 'left', 'right', 'top', 'perspective']);
let manifoldModulePromise = null;

function fail(code, message, details = {}) {
  const error = new Error(message);
  error.code = code;
  error.status = 400;
  error.details = details;
  return error;
}

function hashBytes(bytes) { return createHash('sha256').update(bytes).digest('hex'); }
function stable(value) {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stable(value[key])]));
  return value;
}
function hashJson(value) { return hashBytes(Buffer.from(JSON.stringify(stable(value)))); }
function boundedName(value, field = 'name') {
  const name = typeof value === 'string' ? value.trim().slice(0, 180) : '';
  if (!name) throw fail('foundry.script.invalid_argument', field + ' is required.', {field});
  return name;
}
function vector(value, length, fallback, field) {
  const source = Array.isArray(value) ? value : fallback;
  if (!Array.isArray(source) || source.length !== length || source.some((entry) => !Number.isFinite(Number(entry)))) throw fail('foundry.script.invalid_argument', field + ' must contain ' + length + ' finite numbers.', {field});
  return source.map(Number);
}
function options(value) { return value && typeof value === 'object' && !Array.isArray(value) ? value : {}; }

const VERTEX_PURPOSES = Object.freeze([
  'silhouette',
  'manufactured_form_transition',
  'mechanical_interface',
  'articulation',
  'closure',
  'stable_edge_highlight',
  'demonstrated_shading_correction',
]);
function positiveInteger(value, field, maximum = Number.MAX_SAFE_INTEGER) {
  const number = Number(value);
  if (!Number.isInteger(number) || number <= 0 || number > maximum) throw fail('foundry.geometry.invalid_budget', field + ' must be a positive integer.', {field, value});
  return number;
}
function purposeEntry(value, field) {
  const entry = options(value), purpose = String(entry.purpose || ''), rationale = String(entry.rationale || '').trim();
  if (!VERTEX_PURPOSES.includes(purpose)) throw fail('foundry.geometry.purpose_required', field + ' requires an allowed vertex purpose.', {field, allowed: VERTEX_PURPOSES});
  if (rationale.length < 12 || rationale.length > 500) throw fail('foundry.geometry.purpose_required', field + ' requires a concrete rationale.', {field});
  return {purpose, rationale};
}
function topologyContract(specValue, operation, requirements = {}) {
  const spec = options(specValue), contract = options(spec.topology);
  if (contract.coverage !== 'all_output_vertices') throw fail('foundry.geometry.purpose_coverage', operation + ' must cover all output vertices.', {operation});
  const primary = purposeEntry(contract, operation + '.topology');
  const maxOutputVertices = positiveInteger(contract.maxOutputVertices, operation + '.topology.maxOutputVertices', MAX_VERTICES);
  const maxOutputTriangles = positiveInteger(contract.maxOutputTriangles, operation + '.topology.maxOutputTriangles', MAX_TRIANGLES);
  const maxGrowthRatio = Number(contract.maxGrowthRatio);
  if (!Number.isFinite(maxGrowthRatio) || maxGrowthRatio < 1 || maxGrowthRatio > 100) throw fail('foundry.geometry.invalid_budget', operation + '.topology.maxGrowthRatio must be between 1 and 100.', {operation});
  const simplification = options(contract.simplification), maxVisibleErrorPx = Number(simplification.maxVisibleErrorPx);
  if (simplification.method !== 'remove_or_merge' || simplification.status !== 'pending_review' || !Number.isFinite(maxVisibleErrorPx) || maxVisibleErrorPx <= 0 || maxVisibleErrorPx > 4) {
    throw fail('foundry.geometry.simplification_required', operation + ' requires a pending remove-or-merge challenge with a bounded visible-error tolerance.', {operation});
  }
  const validatePurposeList = (name, expected) => {
    if (!expected) return [];
    const list = Array.isArray(contract[name]) ? contract[name] : [];
    if (list.length !== expected) throw fail('foundry.geometry.purpose_coverage', operation + '.topology.' + name + ' must cover exactly ' + expected + ' generated coordinates.', {operation, expected, actual: list.length});
    return list.map((entry, index) => ({index, ...purposeEntry(entry, operation + '.topology.' + name + '[' + index + ']')}));
  };
  const sectionPurposes = validatePurposeList('sectionPurposes', requirements.sectionCount || 0);
  const profilePointPurposes = validatePurposeList('profilePointPurposes', requirements.profileCount || 0);
  let sampling = null;
  if (requirements.segmentCount) {
    sampling = options(contract.sampling);
    if (sampling.basis !== 'projected_error' || positiveInteger(sampling.segmentCount, operation + '.topology.sampling.segmentCount', 128) !== requirements.segmentCount || !(Number(sampling.projectedRadiusPx) > 0) || !(Number(sampling.maxErrorPx) > 0)) {
      throw fail('foundry.geometry.sampling_required', operation + ' requires projected-error sampling that matches the generated segment count.', {operation, expectedSegments: requirements.segmentCount});
    }
    sampling = {basis: 'projected_error', segmentCount: requirements.segmentCount, projectedRadiusPx: Number(sampling.projectedRadiusPx), maxErrorPx: Number(sampling.maxErrorPx)};
  }
  return {operation, coverage: contract.coverage, ...primary, maxOutputVertices, maxOutputTriangles, maxGrowthRatio, simplification: {method: 'remove_or_merge', status: 'pending_review', maxVisibleErrorPx}, sectionPurposes, profilePointPurposes, sampling};
}
function geometryCounts(data) {
  return {vertices: data.positions.length / 3, triangles: data.indices.length / 3};
}
function enforceOperationBudget(contract, counts, inputCounts = null, phase = 'output') {
  if (counts.vertices > contract.maxOutputVertices || counts.triangles > contract.maxOutputTriangles) {
    throw fail('foundry.geometry.operation_budget_exceeded', contract.operation + ' exceeds its declared output budget.', {operation: contract.operation, phase, counts, maxOutputVertices: contract.maxOutputVertices, maxOutputTriangles: contract.maxOutputTriangles});
  }
  const growthRatio = inputCounts ? Math.max(counts.vertices / Math.max(1, inputCounts.vertices), counts.triangles / Math.max(1, inputCounts.triangles)) : 1;
  if (growthRatio > contract.maxGrowthRatio) throw fail('foundry.geometry.growth_budget_exceeded', contract.operation + ' exceeds its declared growth ratio.', {operation: contract.operation, phase, counts, inputCounts, growthRatio, maxGrowthRatio: contract.maxGrowthRatio});
  return {...contract, counts, inputCounts, growthRatio, budgetValid: true, purposeDeclared: true};
}
function normalizeProductionBudget(value) {
  const budget = options(value), asset = options(budget.asset), scene = options(budget.scene), componentsValue = options(budget.components);
  const components = Object.fromEntries(Object.entries(componentsValue).map(([name, component]) => [boundedName(name, 'component'), {
    maxVertices: positiveInteger(options(component).maxVertices, 'components.' + name + '.maxVertices', MAX_VERTICES),
    maxTriangles: positiveInteger(options(component).maxTriangles, 'components.' + name + '.maxTriangles', MAX_TRIANGLES),
  }]));
  if (!Object.keys(components).length) throw fail('foundry.geometry.production_budget_required', 'A hard-surface production budget must allocate every component.');
  return {
    asset: {maxVertices: positiveInteger(asset.maxVertices, 'asset.maxVertices', MAX_VERTICES), maxTriangles: positiveInteger(asset.maxTriangles, 'asset.maxTriangles', MAX_TRIANGLES)},
    components,
    scene: {
      instances: positiveInteger(scene.instances, 'scene.instances', 10000),
      maxExpandedVertices: positiveInteger(scene.maxExpandedVertices, 'scene.maxExpandedVertices'),
      maxExpandedTriangles: positiveInteger(scene.maxExpandedTriangles, 'scene.maxExpandedTriangles'),
    },
  };
}
function enforceProductionBudget(report, budget) {
  if (!budget) throw fail('foundry.geometry.production_budget_required', 'Hard-surface work requires component, asset, and commissioned-scene budgets.');
  if (report.sourceVertexCount > budget.asset.maxVertices || report.sourceTriangleCount > budget.asset.maxTriangles) throw fail('foundry.geometry.asset_budget_exceeded', 'Unique source geometry exceeds the declared asset budget.', {vertices: report.sourceVertexCount, triangles: report.sourceTriangleCount, budget: budget.asset});
  const seen = new Set();
  for (const component of report.components) {
    const allocation = budget.components[component.node];
    if (!allocation) throw fail('foundry.geometry.component_budget_missing', 'No production allocation exists for component: ' + component.node, {component: component.node});
    seen.add(component.node);
    if (component.vertices > allocation.maxVertices || component.triangles > allocation.maxTriangles) throw fail('foundry.geometry.component_budget_exceeded', 'Component exceeds its declared production allocation.', {component: component.node, vertices: component.vertices, triangles: component.triangles, budget: allocation});
  }
  for (const name of Object.keys(budget.components)) if (!seen.has(name)) throw fail('foundry.geometry.component_budget_unused', 'Declared component allocation did not resolve to output geometry: ' + name, {component: name});
  const expandedVertices = report.expandedVertexCount * budget.scene.instances, expandedTriangles = report.expandedTriangleCount * budget.scene.instances;
  if (expandedVertices > budget.scene.maxExpandedVertices || expandedTriangles > budget.scene.maxExpandedTriangles) throw fail('foundry.geometry.scene_budget_exceeded', 'Commissioned scene exceeds its declared expanded geometry budget.', {instances: budget.scene.instances, expandedVertices, expandedTriangles, budget: budget.scene});
  return {...budget, expandedVertices, expandedTriangles, budgetValid: true};
}

async function io() {
  await Promise.all([MeshoptDecoder.ready, MeshoptEncoder.ready]);
  return new NodeIO()
    .registerExtensions(KHRONOS_EXTENSIONS)
    .registerDependencies({'meshopt.decoder': MeshoptDecoder, 'meshopt.encoder': MeshoptEncoder})
    .setLogger(new Logger(Verbosity.SILENT));
}

function newDocument() {
  const doc = new Document();
  doc.setLogger(new Logger(Verbosity.SILENT));
  return {doc, buffer: doc.createBuffer('foundry-buffer'), scene: doc.createScene('Foundry Scene')};
}
function rootBuffer(doc) { return doc.getRoot().listBuffers()[0] || doc.createBuffer('foundry-buffer'); }
function accessor(doc, buffer, name, type, array) { return doc.createAccessor(name, buffer).setType(type).setArray(array); }
function nodeByName(doc, name) {
  const clean = boundedName(name, 'node');
  const found = doc.getRoot().listNodes().find((node) => node.getName() === clean);
  if (!found) throw fail('foundry.scene.node_not_found', 'Node not found: ' + clean, {name: clean});
  return found;
}
function uniqueNodeName(doc, name) {
  const clean = boundedName(name);
  if (doc.getRoot().listNodes().some((node) => node.getName() === clean)) throw fail('foundry.scene.name_conflict', 'Node already exists: ' + clean, {name: clean});
  return clean;
}
function materialByName(doc, name) {
  const clean = boundedName(name, 'material');
  const found = doc.getRoot().listMaterials().find((entry) => entry.getName() === clean);
  if (!found) throw fail('foundry.material.not_found', 'Material not found: ' + clean, {name: clean});
  return found;
}

function faceNormal(a, b, c) {
  const ux = b[0] - a[0], uy = b[1] - a[1], uz = b[2] - a[2];
  const vx = c[0] - a[0], vy = c[1] - a[1], vz = c[2] - a[2];
  const x = uy * vz - uz * vy, y = uz * vx - ux * vz, z = ux * vy - uy * vx;
  const length = Math.hypot(x, y, z) || 1;
  return [x / length, y / length, z / length];
}
function flatMeshData(vertices, faces) {
  const positions = [], normals = [], indices = [];
  for (const face of faces) {
    const a = vertices[face[0]], b = vertices[face[1]], c = vertices[face[2]];
    const normal = faceNormal(a, b, c), base = positions.length / 3;
    for (const point of [a, b, c]) { positions.push(...point); normals.push(...normal); }
    indices.push(base, base + 1, base + 2);
  }
  return {positions: new Float32Array(positions), normals: new Float32Array(normals), indices: new Uint32Array(indices)};
}
function indexedMeshData(vertices, faces) {
  const positions = new Float32Array(vertices.flat());
  const normals = new Float32Array(positions.length);
  const indices = new Uint32Array(faces.flat());
  for (const face of faces) {
    const normal = faceNormal(vertices[face[0]], vertices[face[1]], vertices[face[2]]);
    for (const index of face) for (let component = 0; component < 3; component++) normals[index * 3 + component] += normal[component];
  }
  for (let index = 0; index < normals.length; index += 3) {
    const length = Math.hypot(normals[index], normals[index + 1], normals[index + 2]) || 1;
    normals[index] /= length; normals[index + 1] /= length; normals[index + 2] /= length;
  }
  return {positions, normals, indices};
}
function boxData(size = [1, 1, 1], bevel = 0) {
  const [sx, sy, sz] = vector(size, 3, [1, 1, 1], 'size');
  const hx = sx / 2, hy = sy / 2, hz = sz / 2;
  const c = Math.max(0, Math.min(Number(bevel) || 0, hx * 0.45, hz * 0.45));
  const profile = [[-hx + c, -hz], [hx - c, -hz], [hx, -hz + c], [hx, hz - c], [hx - c, hz], [-hx + c, hz], [-hx, hz - c], [-hx, -hz + c]];
  const vertices = [];
  for (const y of [-hy, hy]) for (const [x, z] of profile) vertices.push([x, y, z]);
  const faces = [];
  for (let i = 1; i < profile.length - 1; i++) faces.push([0, i + 1, i], [8, 8 + i, 8 + i + 1]);
  for (let i = 0; i < profile.length; i++) { const j = (i + 1) % profile.length; faces.push([i, j, 8 + j], [i, 8 + j, 8 + i]); }
  return flatMeshData(vertices, faces);
}
function cylinderData(radius = 0.5, depth = 1, segments = 24) {
  const count = Math.max(6, Math.min(128, Math.floor(Number(segments) || 24)));
  const vertices = [];
  for (const x of [-depth / 2, depth / 2]) for (let i = 0; i < count; i++) { const angle = i * Math.PI * 2 / count; vertices.push([x, Math.cos(angle) * radius, Math.sin(angle) * radius]); }
  const faces = [];
  for (let i = 1; i < count - 1; i++) faces.push([0, i, i + 1], [count, count + i + 1, count + i]);
  for (let i = 0; i < count; i++) { const j = (i + 1) % count; faces.push([i, count + j, j], [i, count + i, count + j]); }
  return flatMeshData(vertices, faces);
}
function profileExtrusionData(profileValue, depth) {
  const profile = Array.isArray(profileValue) ? profileValue.map((point, index) => vector(point, 2, null, 'profile[' + index + ']')) : [];
  if (profile.length < 3 || profile.length > 512) throw fail('foundry.geometry.invalid_profile', 'Profile extrusion requires 3-512 points.');
  const half = Number(depth) / 2;
  if (!Number.isFinite(half) || half <= 0) throw fail('foundry.geometry.invalid_depth', 'Profile extrusion depth must be positive.');
  const vertices = [];
  for (const y of [-half, half]) for (const [x, z] of profile) vertices.push([x, y, z]);
  const faces = [], count = profile.length;
  for (let i = 1; i < count - 1; i++) faces.push([0, i + 1, i], [count, count + i, count + i + 1]);
  for (let i = 0; i < count; i++) { const j = (i + 1) % count; faces.push([i, j, count + j], [i, count + j, count + i]); }
  return flatMeshData(vertices, faces);
}
function sectionLoftData(sectionsValue, optionsValue = {}) {
  const options = optionsValue && typeof optionsValue === 'object' && !Array.isArray(optionsValue) ? optionsValue : {};
  if (!Array.isArray(sectionsValue) || sectionsValue.length < 2 || sectionsValue.length > 96) {
    throw fail('foundry.geometry.invalid_sections', 'Section loft requires 2-96 ordered sections.');
  }
  const sections = sectionsValue.map((entry, sectionIndex) => {
    if (!entry || typeof entry !== 'object' || Array.isArray(entry)) throw fail('foundry.geometry.invalid_section', 'Each loft section must be an object.', {sectionIndex});
    const z = Number(entry.z);
    if (!Number.isFinite(z)) throw fail('foundry.geometry.invalid_section', 'Each loft section requires a finite z station.', {sectionIndex});
    const profile = Array.isArray(entry.profile) ? entry.profile.map((point, pointIndex) => vector(point, 2, null, 'sections[' + sectionIndex + '].profile[' + pointIndex + ']')) : [];
    if (profile.length < 3 || profile.length > 256) throw fail('foundry.geometry.invalid_section_profile', 'Each loft section requires 3-256 profile points.', {sectionIndex});
    return {z, profile};
  });
  const pointCount = sections[0].profile.length;
  if (sections.some((section) => section.profile.length !== pointCount)) throw fail('foundry.geometry.section_correspondence', 'All loft sections must have identical profile point counts.');
  if (sections.length * pointCount > 32768) throw fail('foundry.geometry.section_vertex_limit', 'Section loft exceeds 32,768 side vertices.');
  for (let index = 1; index < sections.length; index++) if (!(sections[index].z > sections[index - 1].z)) throw fail('foundry.geometry.section_order', 'Loft section z stations must be strictly increasing.', {sectionIndex: index});
  const signedArea = (profile) => profile.reduce((sum, point, index) => {
    const next = profile[(index + 1) % profile.length];
    return sum + point[0] * next[1] - next[0] * point[1];
  }, 0) / 2;
  const signs = sections.map((section, sectionIndex) => {
    const area = signedArea(section.profile);
    if (Math.abs(area) < 1e-10) throw fail('foundry.geometry.section_area', 'Loft section profile area must be non-zero.', {sectionIndex});
    return Math.sign(area);
  });
  if (signs.some((sign) => sign !== signs[0])) throw fail('foundry.geometry.section_winding', 'All loft section profiles must use the same winding.');
  if (signs[0] < 0) for (const section of sections) section.profile.reverse();

  const sideVertices = sections.flatMap((section) => section.profile.map(([x, y]) => [x, y, section.z]));
  const positions = sideVertices.flat();
  const normals = new Array(positions.length).fill(0);
  const indices = [];
  const addTriangle = (a, b, c) => {
    indices.push(a, b, c);
    const pa = sideVertices[a], pb = sideVertices[b], pc = sideVertices[c];
    if (!pa || !pb || !pc) return;
    const ux = pb[0] - pa[0], uy = pb[1] - pa[1], uz = pb[2] - pa[2];
    const vx = pc[0] - pa[0], vy = pc[1] - pa[1], vz = pc[2] - pa[2];
    const nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
    for (const vertex of [a, b, c]) {
      normals[vertex * 3] += nx;
      normals[vertex * 3 + 1] += ny;
      normals[vertex * 3 + 2] += nz;
    }
  };
  for (let sectionIndex = 0; sectionIndex < sections.length - 1; sectionIndex++) {
    const lower = sectionIndex * pointCount, upper = (sectionIndex + 1) * pointCount;
    for (let pointIndex = 0; pointIndex < pointCount; pointIndex++) {
      const next = (pointIndex + 1) % pointCount;
      addTriangle(lower + pointIndex, lower + next, upper + next);
      addTriangle(lower + pointIndex, upper + next, upper + pointIndex);
    }
  }
  const addCap = (sectionIndex, outward) => {
    const base = sectionIndex * pointCount;
    for (let index = 1; index < pointCount - 1; index++) {
      if (outward > 0) addTriangle(base, base + index, base + index + 1);
      else addTriangle(base, base + index + 1, base + index);
    }
  };
  if (options.capStart !== false) addCap(0, -1);
  if (options.capEnd !== false) addCap(sections.length - 1, 1);
  for (let index = 0; index < normals.length; index += 3) {
    const length = Math.hypot(normals[index], normals[index + 1], normals[index + 2]) || 1;
    normals[index] /= length; normals[index + 1] /= length; normals[index + 2] /= length;
  }
  return {positions: new Float32Array(positions), normals: new Float32Array(normals), indices: new Uint32Array(indices)};
}
function makeMesh(doc, name, data, material = null) {
  const buffer = rootBuffer(doc);
  const primitive = doc.createPrimitive()
    .setAttribute('POSITION', accessor(doc, buffer, name + ':POSITION', Accessor.Type.VEC3, data.positions))
    .setAttribute('NORMAL', accessor(doc, buffer, name + ':NORMAL', Accessor.Type.VEC3, data.normals))
    .setIndices(accessor(doc, buffer, name + ':INDICES', Accessor.Type.SCALAR, data.indices));
  if (material) primitive.setMaterial(material);
  return doc.createMesh(name).addPrimitive(primitive);
}
function addNodeWithMesh(doc, scene, name, data, material = null, transform = {}) {
  const node = doc.createNode(uniqueNodeName(doc, name)).setMesh(makeMesh(doc, name + '-mesh', data, material));
  if (transform.translation) node.setTranslation(vector(transform.translation, 3, [0, 0, 0], 'translation'));
  if (transform.rotation) node.setRotation(vector(transform.rotation, 4, [0, 0, 0, 1], 'rotation'));
  if (transform.scale) node.setScale(vector(transform.scale, 3, [1, 1, 1], 'scale'));
  scene.addChild(node);
  return node;
}
function detach(doc, node) {
  const parent = node.getParentNode();
  if (parent) parent.removeChild(node);
  for (const scene of doc.getRoot().listScenes()) scene.removeChild(node);
}
function attachTo(doc, node, parentName = '') {
  detach(doc, node);
  if (parentName) nodeByName(doc, parentName).addChild(node);
  else (doc.getRoot().listScenes()[0] || doc.createScene('Foundry Scene')).addChild(node);
}
function cloneNode(doc, source, name) {
  const clone = doc.createNode(uniqueNodeName(doc, name));
  clone.setMesh(source.getMesh()).setCamera(source.getCamera()).setSkin(source.getSkin());
  clone.setTranslation(source.getTranslation()).setRotation(source.getRotation()).setScale(source.getScale()).setWeights(source.getWeights());
  attachTo(doc, clone, source.getParentNode()?.getName() || '');
  return clone;
}

function typedArrayDigest(array) {
  if (!array) return null;
  return {constructor: array.constructor.name, length: array.length, sha256: hashBytes(Buffer.from(array.buffer, array.byteOffset, array.byteLength))};
}
export function preservationEvidence(doc) {
  const root = doc.getRoot();
  const meshes = root.listMeshes().map((mesh) => ({name: mesh.getName(), weights: mesh.getWeights(), primitives: mesh.listPrimitives().map((primitive) => ({
    attributes: Object.fromEntries(primitive.listSemantics().sort().map((semantic) => [semantic, typedArrayDigest(primitive.getAttribute(semantic)?.getArray())])),
    indices: typedArrayDigest(primitive.getIndices()?.getArray()),
    targets: primitive.listTargets().map((target) => Object.fromEntries(target.listSemantics().sort().map((semantic) => [semantic, typedArrayDigest(target.getAttribute(semantic)?.getArray())]))),
    material: primitive.getMaterial()?.getName() || '',
  }))}));
  const skins = root.listSkins().map((skin) => ({name: skin.getName(), joints: skin.listJoints().map((node) => node.getName()), inverseBindMatrices: typedArrayDigest(skin.getInverseBindMatrices()?.getArray())}));
  const animations = root.listAnimations().map((animation) => ({name: animation.getName(), channels: animation.listChannels().map((channel) => ({target: channel.getTargetNode()?.getName(), path: channel.getTargetPath(), interpolation: channel.getSampler()?.getInterpolation(), input: typedArrayDigest(channel.getSampler()?.getInput()?.getArray()), output: typedArrayDigest(channel.getSampler()?.getOutput()?.getArray())}))}));
  const materials = root.listMaterials().map((material) => ({name: material.getName(), baseColorFactor: material.getBaseColorFactor(), metallicFactor: material.getMetallicFactor(), roughnessFactor: material.getRoughnessFactor(), baseColorTexture: material.getBaseColorTexture()?.getName() || null}));
  const textures = root.listTextures().map((texture) => ({name: texture.getName(), mimeType: texture.getMimeType(), image: typedArrayDigest(texture.getImage())}));
  const evidence = {meshes, skins, animations, materials, textures};
  return {...evidence, hashes: Object.fromEntries(Object.entries(evidence).map(([key, value]) => [key, hashJson(value)]))};
}

function recalculatePrimitiveNormals(doc, primitive, label) {
  const positions = primitive.getAttribute('POSITION')?.getArray();
  if (!positions) throw fail('foundry.mesh.position_required', 'Mesh has no POSITION attribute.', {node: label});
  const raw = primitive.getIndices()?.getArray();
  const indices = raw ? Array.from(raw) : Array.from({length: positions.length / 3}, (_, index) => index);
  const normals = new Float32Array(positions.length);
  for (let i = 0; i + 2 < indices.length; i += 3) {
    const ai = indices[i], bi = indices[i + 1], ci = indices[i + 2];
    const a = [positions[ai * 3], positions[ai * 3 + 1], positions[ai * 3 + 2]];
    const b = [positions[bi * 3], positions[bi * 3 + 1], positions[bi * 3 + 2]];
    const c = [positions[ci * 3], positions[ci * 3 + 1], positions[ci * 3 + 2]];
    const normal = faceNormal(a, b, c);
    for (const index of [ai, bi, ci]) for (let component = 0; component < 3; component++) normals[index * 3 + component] += normal[component];
  }
  for (let i = 0; i < normals.length; i += 3) { const length = Math.hypot(normals[i], normals[i + 1], normals[i + 2]) || 1; normals[i] /= length; normals[i + 1] /= length; normals[i + 2] /= length; }
  primitive.setAttribute('NORMAL', accessor(doc, rootBuffer(doc), label + ':NORMAL', Accessor.Type.VEC3, normals));
}
function weldPrimitive(doc, primitive, tolerance = 1e-6) {
  const positions = primitive.getAttribute('POSITION')?.getArray();
  const rawIndices = primitive.getIndices()?.getArray();
  if (!positions) throw fail('foundry.mesh.position_required', 'Weld requires POSITION data.');
  const indices = rawIndices ? Array.from(rawIndices) : Array.from({length: positions.length / 3}, (_, index) => index);
  const semantics = primitive.listSemantics();
  const arrays = Object.fromEntries(semantics.map((semantic) => [semantic, primitive.getAttribute(semantic)?.getArray()]));
  const widths = Object.fromEntries(semantics.map((semantic) => [semantic, arrays[semantic].length / (positions.length / 3)]));
  const keyToIndex = new Map(), remap = new Uint32Array(positions.length / 3), unique = Object.fromEntries(semantics.map((semantic) => [semantic, []]));
  for (let index = 0; index < positions.length / 3; index++) {
    const key = semantics.map((semantic) => Array.from(arrays[semantic].slice(index * widths[semantic], (index + 1) * widths[semantic])).map((value) => Math.round(value / tolerance)).join(',')).join('|');
    if (!keyToIndex.has(key)) {
      const next = keyToIndex.size; keyToIndex.set(key, next);
      for (const semantic of semantics) unique[semantic].push(...arrays[semantic].slice(index * widths[semantic], (index + 1) * widths[semantic]));
    }
    remap[index] = keyToIndex.get(key);
  }
  for (const semantic of semantics) {
    const original = arrays[semantic];
    const Ctor = original.constructor;
    primitive.setAttribute(semantic, accessor(doc, rootBuffer(doc), 'weld:' + semantic, primitive.getAttribute(semantic).getType(), new Ctor(unique[semantic])));
  }
  primitive.setIndices(accessor(doc, rootBuffer(doc), 'weld:INDICES', Accessor.Type.SCALAR, new Uint32Array(indices.map((index) => remap[index]))));
}
async function manifoldModule() {
  if (!manifoldModulePromise) manifoldModulePromise = initManifold().then((module) => { module.setup(); return module; });
  return manifoldModulePromise;
}
function nodeMatrix(node) {
  return new Matrix4().compose(new Vector3(...node.getTranslation()), new Quaternion(...node.getRotation()), new Vector3(...node.getScale()));
}
async function booleanNodes(doc, targetName, toolName, mode, resultName, contractSpec) {
  const target = nodeByName(doc, targetName), tool = nodeByName(doc, toolName);
  const primitiveOf = (node) => {
    const primitives = node.getMesh()?.listPrimitives() || [];
    if (primitives.length !== 1 || primitives[0].listTargets().length || node.getSkin()) throw fail('foundry.mesh.boolean_unsupported', 'Boolean operands must be single-primitive unskinned meshes without morph targets.', {node: node.getName()});
    return primitives[0];
  };
  const module = await manifoldModule();
  const toManifold = (node) => {
    const primitive = primitiveOf(node), position = primitive.getAttribute('POSITION')?.getArray(), raw = primitive.getIndices()?.getArray();
    if (!position || !raw) throw fail('foundry.mesh.boolean_unsupported', 'Boolean operands require indexed POSITION data.', {node: node.getName()});
    const matrix = nodeMatrix(node), point = new Vector3(), transformed = new Float32Array(position.length);
    for (let index = 0; index < position.length; index += 3) { point.set(position[index], position[index + 1], position[index + 2]).applyMatrix4(matrix); transformed.set([point.x, point.y, point.z], index); }
    const manifoldMesh = new module.Mesh({numProp: 3, triVerts: new Uint32Array(raw), vertProperties: transformed});
    manifoldMesh.merge();
    return {manifold: new module.Manifold(manifoldMesh), material: primitive.getMaterial()};
  };
  const a = toManifold(target), b = toManifold(tool);
  const primitiveCounts = (node) => { const primitive = primitiveOf(node); return {vertices: primitive.getAttribute('POSITION').getArray().length / 3, triangles: primitive.getIndices().getArray().length / 3}; };
  const targetCounts = primitiveCounts(target), toolCounts = primitiveCounts(tool), inputCounts = {vertices: targetCounts.vertices + toolCounts.vertices, triangles: targetCounts.triangles + toolCounts.triangles};
  const contract = topologyContract(contractSpec, 'mesh.boolean');
  let result;
  try {
    if (mode === 'union') result = a.manifold.add(b.manifold);
    else if (mode === 'subtract') result = a.manifold.subtract(b.manifold);
    else if (mode === 'intersect') result = a.manifold.intersect(b.manifold);
    else throw fail('foundry.mesh.boolean_mode', 'Boolean mode must be union, subtract, or intersect.', {mode});
    if (result.isEmpty()) throw fail('foundry.mesh.boolean_empty', 'Boolean produced an empty result.');
    const output = result.getMesh();
    output.merge();
    const positions = new Float32Array(output.numVert * 3);
    for (let index = 0; index < output.numVert; index++) positions.set(output.position(index), index * 3);
    const data = {positions, normals: new Float32Array(positions.length), indices: new Uint32Array(output.triVerts)};
    const topology = enforceOperationBudget(contract, geometryCounts(data), inputCounts, 'transactional_output');
    const name = resultName ? uniqueNodeName(doc, resultName) : target.getName();
    const scene = doc.getRoot().listScenes()[0] || doc.createScene('Foundry Scene');
    const targetMesh = target.getMesh(), toolMesh = tool.getMesh();
    detach(doc, target); detach(doc, tool); target.dispose(); tool.dispose(); targetMesh?.dispose(); toolMesh?.dispose();
    const node = addNodeWithMesh(doc, scene, name, data, a.material);
    recalculatePrimitiveNormals(doc, node.getMesh().listPrimitives()[0], name);
    return {node, topology};
  } finally {
    a.manifold.delete(); b.manifold.delete(); if (result) result.delete();
  }
}

function interpolationSample(channel, time) {
  const sampler = channel.getSampler(), input = sampler?.getInput()?.getArray(), output = sampler?.getOutput()?.getArray();
  if (!input || !output || sampler.getInterpolation() === 'CUBICSPLINE') throw fail('foundry.animation.unsupported_channel', 'Only STEP and LINEAR channels are currently editable.');
  const width = output.length / input.length;
  let upper = 1; while (upper < input.length && input[upper] < time) upper += 1;
  upper = Math.min(upper, input.length - 1); const lower = Math.max(0, upper - 1);
  const span = input[upper] - input[lower], alpha = span > 0 ? (time - input[lower]) / span : 0;
  const values = [];
  for (let component = 0; component < width; component++) values.push(output[lower * width + component] + (output[upper * width + component] - output[lower * width + component]) * alpha);
  if (channel.getTargetPath() === 'rotation') { const length = Math.hypot(...values) || 1; return values.map((value) => value / length); }
  return values;
}
function clipByName(doc, name) {
  const clean = boundedName(name, 'clip');
  const found = doc.getRoot().listAnimations().find((clip) => clip.getName() === clean);
  if (!found) throw fail('foundry.animation.clip_not_found', 'Animation clip not found: ' + clean, {name: clean});
  return found;
}
function editAnimationRange(doc, clip, start, end, duration) {
  if (!(start >= 0 && end > start && duration > 0 && duration <= 3600)) throw fail('foundry.animation.invalid_range', 'Animation range is invalid.');
  let changed = 0;
  for (const channel of clip.listChannels()) {
    const sampler = channel.getSampler(), input = sampler?.getInput()?.getArray(), output = sampler?.getOutput()?.getArray();
    if (!input || !output || sampler.getInterpolation() === 'CUBICSPLINE') continue;
    const width = output.length / input.length, sourceTimes = [start, ...Array.from(input).filter((time) => time > start && time < end), end];
    const times = new Float32Array(sourceTimes.length), values = new Float32Array(sourceTimes.length * width);
    sourceTimes.forEach((sourceTime, index) => { times[index] = (sourceTime - start) / (end - start) * duration; values.set(interpolationSample(channel, sourceTime), index * width); });
    sampler.getInput().setArray(times); sampler.getOutput().setArray(values); changed += 1;
  }
  if (!changed) throw fail('foundry.animation.no_editable_channels', 'No editable channels were found.');
  return changed;
}
function setAnimationKey(doc, clip, nodeName, path, time, value) {
  const node = nodeByName(doc, nodeName);
  if (!['translation', 'rotation', 'scale'].includes(path)) throw fail('foundry.animation.invalid_path', 'Animation path must be translation, rotation, or scale.');
  const expectedWidth = path === 'rotation' ? 4 : 3, normalizedValue = vector(value, expectedWidth, null, 'value');
  let channel = clip.listChannels().find((entry) => entry.getTargetNode() === node && entry.getTargetPath() === path);
  if (!channel) {
    const sampler = doc.createAnimationSampler(nodeName + ':' + path + ':sampler').setInput(accessor(doc, rootBuffer(doc), nodeName + ':' + path + ':times', Accessor.Type.SCALAR, new Float32Array())).setOutput(accessor(doc, rootBuffer(doc), nodeName + ':' + path + ':values', path === 'rotation' ? Accessor.Type.VEC4 : Accessor.Type.VEC3, new Float32Array())).setInterpolation('LINEAR');
    channel = doc.createAnimationChannel(nodeName + ':' + path + ':channel').setSampler(sampler).setTargetNode(node).setTargetPath(path); clip.addSampler(sampler).addChannel(channel);
  }
  const sampler = channel.getSampler(), input = Array.from(sampler.getInput().getArray() || []), output = Array.from(sampler.getOutput().getArray() || []), width = expectedWidth;
  const entries = input.map((entryTime, index) => ({time: entryTime, value: output.slice(index * width, (index + 1) * width)}));
  const existing = entries.find((entry) => Math.abs(entry.time - time) < 1e-6);
  if (existing) existing.value = normalizedValue; else entries.push({time: Number(time), value: normalizedValue});
  entries.sort((a, b) => a.time - b.time);
  sampler.getInput().setArray(new Float32Array(entries.map((entry) => entry.time)));
  sampler.getOutput().setArray(new Float32Array(entries.flatMap((entry) => entry.value)));
}
function deleteAnimationKey(clip, nodeName, path, time) {
  const channel = clip.listChannels().find((entry) => entry.getTargetNode()?.getName() === nodeName && entry.getTargetPath() === path);
  if (!channel) throw fail('foundry.animation.channel_not_found', 'Animation channel was not found.', {node: nodeName, path});
  const sampler = channel.getSampler(), input = Array.from(sampler.getInput().getArray()), output = Array.from(sampler.getOutput().getArray()), width = output.length / input.length;
  const keep = input.map((entryTime, index) => ({time: entryTime, values: output.slice(index * width, (index + 1) * width)})).filter((entry) => Math.abs(entry.time - time) >= 1e-6);
  if (!keep.length) throw fail('foundry.animation.empty_channel', 'Deleting the key would empty the channel.');
  sampler.getInput().setArray(new Float32Array(keep.map((entry) => entry.time))); sampler.getOutput().setArray(new Float32Array(keep.flatMap((entry) => entry.values)));
}

export async function sourceDocument(sourceBytes) {
  if (!sourceBytes) return newDocument().doc;
  try { return await (await io()).readBinary(new Uint8Array(sourceBytes)); }
  catch (error) { throw fail('foundry.source.unsupported_glb', 'GLB could not be decoded without data loss: ' + String(error.message || error).slice(0, 600)); }
}

export async function executeFoundryPlan({doc, plan, domain = 'hard_surface', modelSheet = null}) {
  if (!plan || !Array.isArray(plan.operations)) throw fail('foundry.script.invalid_plan', 'Foundry operation plan is required.');
  const before = preservationEvidence(doc), changes = [], touched = new Set(), topology = [], scene = doc.getRoot().listScenes()[0] || doc.createScene('Foundry Scene');
  const cages = new Map();
  let reviewViews = [...SUPPORTED_VIEWS], productionBudget = null, modelSheetReview = null, modelSheetFitAssertion = null;
  for (let index = 0; index < plan.operations.length; index++) {
    const entry = plan.operations[index], args = Array.isArray(entry.args) ? entry.args : [], key = entry.namespace + '.' + entry.operation;
    try {
      if (key === 'asset.inspect') { changes.push({index, operation: key, effect: 'inspection_requested'}); continue; }
      if (key === 'validation.productionBudget') { if (productionBudget) throw fail('foundry.geometry.production_budget_duplicate', 'Only one production budget may be declared.'); productionBudget = normalizeProductionBudget(args[0]); }
      else if (key === 'scene.createGroup') { const name = boundedName(args[0]); const spec = options(args[1]); const node = doc.createNode(uniqueNodeName(doc, name)); if (spec.translation) node.setTranslation(vector(spec.translation, 3, [0, 0, 0], 'translation')); if (spec.rotation) node.setRotation(vector(spec.rotation, 4, [0, 0, 0, 1], 'rotation')); if (spec.scale) node.setScale(vector(spec.scale, 3, [1, 1, 1], 'scale')); scene.addChild(node); touched.add(name); }
      else if (key === 'scene.createSubdivisionCage') { const name = boundedName(args[0], 'cage'); if (cages.has(name)) throw fail('foundry.cage.name_conflict', 'Subdivision cage already exists: ' + name); cages.set(name, createSubdivisionCage(args[1])); touched.add(name); }
      else if (key === 'scene.createBox') {
        const name = boundedName(args[0]), spec = options(args[1]), contract = topologyContract(spec, key), data = boxData(spec.size || [1, 1, 1], spec.bevel || 0);
        topology.push({...enforceOperationBudget(contract, geometryCounts(data), null, 'preflight'), component: name});
        addNodeWithMesh(doc, scene, name, data, spec.material ? materialByName(doc, spec.material) : null, spec); touched.add(name);
      }
      else if (key === 'scene.createCylinder') {
        const name = boundedName(args[0]), spec = options(args[1]), segments = Math.max(6, Math.min(128, Math.floor(Number(spec.segments) || 24))), contract = topologyContract(spec, key, {segmentCount: segments}), data = cylinderData(Number(spec.radius || 0.5), Number(spec.depth || 1), segments);
        topology.push({...enforceOperationBudget(contract, geometryCounts(data), null, 'preflight'), component: name});
        addNodeWithMesh(doc, scene, name, data, spec.material ? materialByName(doc, spec.material) : null, spec); touched.add(name);
      }
      else if (key === 'scene.createProfileExtrusion') {
        const name = boundedName(args[0]), spec = options(args[1]), profileCount = Array.isArray(spec.profile) ? spec.profile.length : 0, contract = topologyContract(spec, key, {profileCount}), data = profileExtrusionData(spec.profile, spec.depth);
        topology.push({...enforceOperationBudget(contract, geometryCounts(data), null, 'preflight'), component: name});
        addNodeWithMesh(doc, scene, name, data, spec.material ? materialByName(doc, spec.material) : null, spec); touched.add(name);
      }
      else if (key === 'scene.createSectionLoft') {
        const name = boundedName(args[0]), spec = options(args[1]), sectionCount = Array.isArray(spec.sections) ? spec.sections.length : 0, profileCount = sectionCount && Array.isArray(spec.sections[0].profile) ? spec.sections[0].profile.length : 0;
        const contract = topologyContract(spec, key, {sectionCount, profileCount});
        const predicted = {vertices: sectionCount * profileCount, triangles: Math.max(0, sectionCount - 1) * profileCount * 2 + (spec.capStart === false ? 0 : Math.max(0, profileCount - 2)) + (spec.capEnd === false ? 0 : Math.max(0, profileCount - 2))};
        enforceOperationBudget(contract, predicted, null, 'preflight');
        const data = sectionLoftData(spec.sections, spec);
        topology.push({...enforceOperationBudget(contract, geometryCounts(data), null, 'output'), component: name});
        addNodeWithMesh(doc, scene, name, data, spec.material ? materialByName(doc, spec.material) : null, spec); touched.add(name);
      }
      else if (key === 'scene.transform') { const node = nodeByName(doc, args[0]), spec = options(args[1]); if (spec.translation) node.setTranslation(vector(spec.translation, 3, null, 'translation')); if (spec.rotation) node.setRotation(vector(spec.rotation, 4, null, 'rotation')); if (spec.scale) node.setScale(vector(spec.scale, 3, null, 'scale')); touched.add(node.getName()); }
      else if (key === 'scene.rename') { const node = nodeByName(doc, args[0]), name = uniqueNodeName(doc, args[1]); touched.add(node.getName()); node.setName(name); touched.add(name); }
      else if (key === 'scene.reparent') { const node = nodeByName(doc, args[0]); attachTo(doc, node, args[1] || ''); touched.add(node.getName()); }
      else if (key === 'scene.remove') { const node = nodeByName(doc, args[0]); touched.add(node.getName()); node.dispose(); }
      else if (key === 'scene.instance') { const source = nodeByName(doc, args[0]), clone = cloneNode(doc, source, args[1]); const spec = options(args[2]); if (spec.translation) clone.setTranslation(vector(spec.translation, 3, null, 'translation')); if (spec.rotation) clone.setRotation(vector(spec.rotation, 4, null, 'rotation')); if (spec.scale) clone.setScale(vector(spec.scale, 3, null, 'scale')); touched.add(clone.getName()); }
      else if (key === 'scene.array') { const source = nodeByName(doc, args[0]), spec = options(args[1]), count = Math.max(1, Math.min(512, Math.floor(Number(spec.count) || 1))), offset = vector(spec.offset, 3, [1, 0, 0], 'offset'); for (let item = 1; item < count; item++) { const clone = cloneNode(doc, source, String(spec.namePrefix || source.getName() + '-array') + '-' + item); clone.setTranslation(source.getTranslation().map((value, axis) => value + offset[axis] * item)); touched.add(clone.getName()); } }
      else if (key === 'scene.mirror') { const source = nodeByName(doc, args[0]), spec = options(args[2]), axis = String(args[1] || 'x'), axisIndex = {x: 0, y: 1, z: 2}[axis]; if (axisIndex === undefined) throw fail('foundry.scene.invalid_axis', 'Mirror axis must be x, y, or z.'); const clone = cloneNode(doc, source, spec.name || source.getName() + '-mirror-' + axis); const translation = [...source.getTranslation()], scale = [...source.getScale()]; translation[axisIndex] *= -1; scale[axisIndex] *= -1; clone.setTranslation(translation).setScale(scale); touched.add(clone.getName()); }
      else if (key === 'scene.separate') { const source = nodeByName(doc, args[0]), primitives = source.getMesh()?.listPrimitives() || []; if (primitives.length < 2) throw fail('foundry.scene.separate_unneeded', 'Separate requires a mesh with multiple primitives.'); primitives.forEach((primitive, primitiveIndex) => { const mesh = doc.createMesh(source.getName() + '-part-' + primitiveIndex).addPrimitive(primitive); const node = doc.createNode(uniqueNodeName(doc, source.getName() + '-part-' + primitiveIndex)).setMesh(mesh).setTranslation(source.getTranslation()).setRotation(source.getRotation()).setScale(source.getScale()); attachTo(doc, node, source.getParentNode()?.getName() || ''); touched.add(node.getName()); }); source.dispose(); }
      else if (key === 'mesh.recalculateNormals') { const node = nodeByName(doc, args[0]); for (const primitive of node.getMesh()?.listPrimitives() || []) recalculatePrimitiveNormals(doc, primitive, node.getName()); touched.add(node.getName()); }
      else if (key === 'mesh.weld') { const node = nodeByName(doc, args[0]), tolerance = Math.max(1e-9, Math.min(1, Number(args[1]) || 1e-6)); for (const primitive of node.getMesh()?.listPrimitives() || []) weldPrimitive(doc, primitive, tolerance); touched.add(node.getName()); }
      else if (key === 'mesh.boolean') { const result = await booleanNodes(doc, args[0], args[1], String(args[2] || 'union'), args[3] || '', args[4]); topology.push({...result.topology, component: result.node.getName()}); touched.add(result.node.getName()); }
      else if (key === 'mesh.fitSubdivisionCage') { const cageName = boundedName(args[0], 'cage'), cage = cages.get(cageName); if (!cage) throw fail('foundry.cage.not_found', 'Subdivision cage not found: ' + cageName); if (!modelSheet) throw fail('foundry.model_sheet.required', 'fitSubdivisionCage requires a calibrated model-sheet input.'); if (cage.subdivision) throw fail('foundry.cage.fit_after_subdivide', 'Subdivision cage must be fitted before mesh.subdivide.', {cage: cageName}); cages.set(cageName, fitSubdivisionCageToModelSheet(cage, modelSheet, options(args[1]))); touched.add(cageName); }
      else if (key === 'mesh.subdivide') { const cageName = boundedName(args[0], 'cage'), cage = cages.get(cageName); if (!cage) throw fail('foundry.cage.not_found', 'Subdivision cage not found: ' + cageName); const spec = options(args[1]), contract = topologyContract(spec, key), output = boundedName(spec.output || cageName + '-surface', 'output'), subdivision = subdivideCage(cage, spec.levels ?? 2); const data = indexedMeshData(subdivision.positions, subdivision.faces), inputCounts = {vertices: cage.positions.length, triangles: cage.faces.length * 2}; topology.push({...enforceOperationBudget(contract, geometryCounts(data), inputCounts, 'output'), component: output}); addNodeWithMesh(doc, scene, output, data, spec.material ? materialByName(doc, spec.material) : null, spec); cage.subdivision = {output, levels: subdivision.levels, triangleCount: subdivision.triangleCount}; touched.add(output); }
      else if (key === 'material.create') { const name = boundedName(args[0], 'material'), spec = options(args[1]); if (doc.getRoot().listMaterials().some((entry) => entry.getName() === name)) throw fail('foundry.material.name_conflict', 'Material already exists: ' + name); doc.createMaterial(name).setBaseColorFactor(vector(spec.baseColor, 4, [0.5, 0.5, 0.5, 1], 'baseColor')).setMetallicFactor(Math.max(0, Math.min(1, Number(spec.metallic) || 0))).setRoughnessFactor(Math.max(0, Math.min(1, Number(spec.roughness ?? 0.7)))); }
      else if (key === 'material.assign') { const node = nodeByName(doc, args[0]), material = materialByName(doc, args[1]); for (const primitive of node.getMesh()?.listPrimitives() || []) primitive.setMaterial(material); touched.add(node.getName()); }
      else if (key === 'rig.addBone') { const parent = nodeByName(doc, args[0]), name = uniqueNodeName(doc, args[1]), spec = options(args[2]), bone = doc.createNode(name).setTranslation(vector(spec.translation, 3, [0, 0, 0], 'translation')).setRotation(vector(spec.rotation, 4, [0, 0, 0, 1], 'rotation')); parent.addChild(bone); if (spec.addToSkin !== false) { const skin = doc.getRoot().listSkins().find((entry) => entry.listJoints().includes(parent)); if (!skin) throw fail('foundry.rig.skin_not_found', 'Parent bone is not part of a skin.', {parent: parent.getName()}); const old = skin.getInverseBindMatrices()?.getArray(), next = new Float32Array((skin.listJoints().length + 1) * 16); for (let matrix = 0; matrix < skin.listJoints().length + 1; matrix++) next.set([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1], matrix * 16); if (old) next.set(old); skin.setInverseBindMatrices(accessor(doc, rootBuffer(doc), name + ':inverse-bind', Accessor.Type.MAT4, next)).addJoint(bone); } touched.add(name); }
      else if (key === 'rig.renameBone') { const bone = nodeByName(doc, args[0]), name = uniqueNodeName(doc, args[1]); touched.add(bone.getName()); bone.setName(name); touched.add(name); }
      else if (key === 'rig.orientBone') { const bone = nodeByName(doc, args[0]); bone.setRotation(vector(args[1], 4, null, 'rotation')); touched.add(bone.getName()); }
      else if (key === 'rig.reparentBone') { const bone = nodeByName(doc, args[0]), parent = nodeByName(doc, args[1]); parent.addChild(bone); touched.add(bone.getName()); }
      else if (key === 'rig.attachRigid') { const node = nodeByName(doc, args[0]), bone = nodeByName(doc, args[1]), spec = options(args[2]); if (node.getSkin()) throw fail('foundry.rig.rigid_attachment_skinned', 'Rigid attachments must not have a skin.', {node: node.getName()}); bone.addChild(node); if (spec.translation) node.setTranslation(vector(spec.translation, 3, null, 'translation')); if (spec.rotation) node.setRotation(vector(spec.rotation, 4, null, 'rotation')); if (spec.scale) node.setScale(vector(spec.scale, 3, null, 'scale')); touched.add(node.getName()); }
      else if (key === 'animation.trim') { const clip = clipByName(doc, args[0]), spec = options(args[1]); const start = Number(spec.start ?? 0), end = Number(spec.end), duration = Number(spec.duration ?? end - start); editAnimationRange(doc, clip, start, end, duration); if (spec.outputClip) clip.setName(boundedName(spec.outputClip, 'outputClip')); }
      else if (key === 'animation.retime') { const clip = clipByName(doc, args[0]), duration = Number(args[1]); const current = Math.max(0, ...clip.listSamplers().map((sampler) => { const values = sampler.getInput()?.getArray(); return values?.length ? values[values.length - 1] : 0; })); editAnimationRange(doc, clip, 0, current, duration); }
      else if (key === 'animation.setKey') { const clip = clipByName(doc, args[0]); setAnimationKey(doc, clip, args[1], args[2], Number(args[3]), args[4]); touched.add(String(args[1])); }
      else if (key === 'animation.deleteKey') { const clip = clipByName(doc, args[0]); deleteAnimationKey(clip, String(args[1]), String(args[2]), Number(args[3])); touched.add(String(args[1])); }
      else if (key === 'animation.loop') { const clip = clipByName(doc, args[0]); for (const channel of clip.listChannels()) { const sampler = channel.getSampler(), input = sampler.getInput()?.getArray(), output = sampler.getOutput()?.getArray(); if (!input?.length || !output?.length) continue; const width = output.length / input.length; output.set(output.slice(0, width), output.length - width); } }
      else if (key === 'animation.rootMotion') { const clip = clipByName(doc, args[0]), rootName = String(args[1]), spec = options(args[2]); const channel = clip.listChannels().find((entry) => entry.getTargetNode()?.getName() === rootName && entry.getTargetPath() === 'translation'); if (!channel) throw fail('foundry.animation.root_motion_not_found', 'Root translation channel was not found.', {root: rootName}); const values = channel.getSampler().getOutput().getArray(); const offset = vector(spec.offset, 3, [0, 0, 0], 'offset'); for (let valueIndex = 0; valueIndex < values.length; valueIndex += 3) for (let axis = 0; axis < 3; axis++) values[valueIndex + axis] += offset[axis]; touched.add(rootName); }
      else if (key === 'review.modelSheet') { if (!modelSheet) throw fail('foundry.model_sheet.required', 'review.modelSheet requires a calibrated model-sheet input.'); const spec = options(args[0]), cageName = boundedName(spec.cage, 'cage'), target = boundedName(spec.target, 'target'); if (!cages.has(cageName)) throw fail('foundry.cage.not_found', 'Review cage not found: ' + cageName); nodeByName(doc, target); const suppliedViews = Object.keys(modelSheet.views || {}), availableViews = suppliedViews.length ? suppliedViews : modelSheet.contractVersion === 'home-center.foundry-model-sheet.v1' ? ['front', 'side', 'top'] : [], views = Array.isArray(spec.views) ? [...new Set(spec.views.map(String))] : availableViews; if (views.length < 2 || !views.includes('front') || !views.includes('side') || views.some((view) => !availableViews.includes(view)) || availableViews.some((view) => !views.includes(view))) throw fail('foundry.review.invalid_model_sheet_views', 'Model-sheet review must cover every declared plane and requires front and side.', {views, availableViews}); modelSheetReview = {cage: cageName, target, views}; }
      else if (key === 'review.fixedViews') { const requested = Array.isArray(args[0]) ? args[0].map(String) : []; if (!requested.length || requested.some((view) => !SUPPORTED_VIEWS.includes(view))) throw fail('foundry.review.invalid_views', 'Fixed views must use supported camera names.', {supported: SUPPORTED_VIEWS}); reviewViews = [...new Set(requested)]; }
      else if (key === 'validation.assert') { const assertion = String(args[0]), value = args[1]; if (assertion === 'model_sheet_fit') { if (!modelSheetReview) throw fail('foundry.review.model_sheet_missing', 'model_sheet_fit requires review.modelSheet first.'); const spec = options(value); modelSheetFitAssertion = {minIou: Math.max(0, Math.min(1, Number(spec.minIou ?? 0.9))), maxP95BoundaryErrorRingFraction: Math.max(0, Number(spec.maxP95BoundaryErrorRingFraction ?? 0.03)), maxLandmarkErrorRingFraction: Math.max(0, Number(spec.maxLandmarkErrorRingFraction ?? 0.02))}; } else if (assertion === 'node_exists') nodeByName(doc, value); else if (assertion === 'clip_exists') clipByName(doc, value); else if (assertion === 'skin_exists' && !doc.getRoot().listSkins().some((skin) => skin.getName() === value)) throw fail('foundry.validation.assertion_failed', 'Skin assertion failed: ' + value); else if (!['node_exists', 'clip_exists', 'skin_exists', 'model_sheet_fit'].includes(assertion)) throw fail('foundry.validation.unsupported_assertion', 'Unsupported validation assertion: ' + assertion); }
      else throw fail('foundry.script.unsupported_operation', 'Unsupported Foundry operation: ' + key, {operation: key});
      changes.push({index, operation: key, touched: Array.from(touched).slice(-10)});
    } catch (error) {
      error.details = {...(error.details || {}), operationIndex: index, operation: key};
      throw error;
    }
  }
  if (domain === 'hard_surface' && !productionBudget) throw fail('foundry.geometry.production_budget_required', 'Hard-surface work requires a production budget before output can become a candidate.');
  const after = preservationEvidence(doc);
  const cageEvidence = Object.fromEntries(Array.from(cages.entries()).map(([name, cage]) => [name, cage]));
  return {domain, reviewViews, productionBudget, topology: topology.slice(0, 500), modelSheetReview, modelSheetFitAssertion, cageEvidence, notes: plan.notes || [], changes: changes.slice(0, 500), touched: Array.from(touched).sort().slice(0, 500), before, after, preservation: {untouchedDataRecorded: true, beforeHashes: before.hashes, afterHashes: after.hashes}};
}

function edgeKey(a, b) { return a < b ? a + ':' + b : b + ':' + a; }
function vertexKey(position, index) { return [position[index * 3], position[index * 3 + 1], position[index * 3 + 2]].map((value) => Math.round(value * 1000000000)).join(','); }
export function inspectDocument(doc) {
  const root = doc.getRoot(); let triangles = 0, vertices = 0, sourceTriangles = 0, sourceVertices = 0, degenerateTriangles = 0, invalidNormals = 0; const components = [], seenMeshes = new Set();
  for (const node of root.listNodes()) {
    const mesh = node.getMesh(); if (!mesh) continue; let nodeTriangles = 0, nodeVertices = 0, boundaryEdges = 0, nonManifoldEdges = 0;
    for (const primitive of mesh.listPrimitives()) {
      const position = primitive.getAttribute('POSITION')?.getArray(), normal = primitive.getAttribute('NORMAL')?.getArray(), index = primitive.getIndices()?.getArray(), count = position ? position.length / 3 : 0; nodeVertices += count;
      if (normal) for (let i = 0; i < normal.length; i += 3) if (Math.abs(Math.hypot(normal[i], normal[i + 1], normal[i + 2]) - 1) > 0.02) invalidNormals += 1;
      const indices = index ? Array.from(index) : Array.from({length: count}, (_, i) => i), coordinateEdges = new Map(), indexEdges = new Map();
      for (let i = 0; i + 2 < indices.length; i += 3) {
        const raw = [indices[i], indices[i + 1], indices[i + 2]], keys = raw.map((entry) => vertexKey(position, entry));
        if (keys[0] === keys[1] || keys[1] === keys[2] || keys[2] === keys[0]) degenerateTriangles += 1;
        for (const [a, b] of [[0, 1], [1, 2], [2, 0]]) {
          const coordinateKey = edgeKey(keys[a], keys[b]), indexKey = edgeKey(raw[a], raw[b]);
          coordinateEdges.set(coordinateKey, (coordinateEdges.get(coordinateKey) || 0) + 1);
          indexEdges.set(indexKey, (indexEdges.get(indexKey) || 0) + 1);
        }
        nodeTriangles += 1;
      }
      const edgeScore = (edges) => Array.from(edges.values()).filter((value) => value !== 2).length;
      const edges = edgeScore(indexEdges) <= edgeScore(coordinateEdges) ? indexEdges : coordinateEdges;
      for (const countValue of edges.values()) { if (countValue === 1) boundaryEdges += 1; if (countValue > 2) nonManifoldEdges += 1; }
    }
    triangles += nodeTriangles; vertices += nodeVertices; if (!seenMeshes.has(mesh)) { seenMeshes.add(mesh); sourceTriangles += nodeTriangles; sourceVertices += nodeVertices; } components.push({node: node.getName(), mesh: mesh.getName(), triangles: nodeTriangles, vertices: nodeVertices, boundaryEdges, nonManifoldEdges, instanced: root.listNodes().filter((candidate) => candidate.getMesh() === mesh).length > 1});
  }
  if (vertices > MAX_VERTICES || triangles > MAX_TRIANGLES) throw fail('foundry.limit.geometry', 'Geometry exceeds Foundry limits.', {vertices, triangles, maxVertices: MAX_VERTICES, maxTriangles: MAX_TRIANGLES});
  const boundRoot = root.listScenes()[0] || root.listNodes()[0];
  const bounds = boundRoot ? getBounds(boundRoot) : {min: [0, 0, 0], max: [0, 0, 0]};
  const nonManifoldComponents = components.filter((entry) => entry.nonManifoldEdges > 0).length, openComponents = components.filter((entry) => entry.boundaryEdges > 0).length;
  return {kernelVersion: FOUNDRY_KERNEL_VERSION, bounds: {min: Array.from(bounds.min), max: Array.from(bounds.max), size: Array.from(bounds.min).map((value, index) => bounds.max[index] - value)}, triangleCount: triangles, vertexCount: vertices, sourceTriangleCount: sourceTriangles, sourceVertexCount: sourceVertices, expandedTriangleCount: triangles, expandedVertexCount: vertices, componentCount: components.length, components: components.slice(0, 200), validation: {degenerateTriangles, invalidNormals, nonManifoldComponents, openComponents, manifoldClosedComponents: components.filter((entry) => entry.boundaryEdges === 0 && entry.nonManifoldEdges === 0).length, topologyValid: degenerateTriangles === 0 && invalidNormals === 0 && nonManifoldComponents === 0 && openComponents === 0}, hierarchy: root.listNodes().slice(0, 500).map((node) => ({name: node.getName(), parent: node.getParentNode()?.getName() || null, mesh: node.getMesh()?.getName() || null, skin: node.getSkin()?.getName() || null})), animations: root.listAnimations().map((animation) => ({name: animation.getName(), channelCount: animation.listChannels().length, duration: Math.max(0, ...animation.listSamplers().map((sampler) => { const values = sampler.getInput()?.getArray(); return values?.length ? values[values.length - 1] : 0; }))})), skins: root.listSkins().map((skin) => ({name: skin.getName(), joints: skin.listJoints().map((node) => node.getName())}))};
}

export async function runFoundryKernel({sourceBytes = null, plan, domain = 'hard_surface', reviewPreset = 'fixed-six-view', modelSheet = null}) {
  if (!['hard_surface', 'character_setup', 'animation', 'inspect'].includes(domain)) throw fail('foundry.domain.unsupported', 'Unsupported Foundry domain: ' + domain);
  const doc = await sourceDocument(sourceBytes);
  const evidence = await executeFoundryPlan({doc, plan, domain, modelSheet});
  const report = inspectDocument(doc), production = domain === 'hard_surface' ? enforceProductionBudget(report, evidence.productionBudget) : null;
  report.validation = {...report.validation, budgetValid: domain === 'hard_surface' ? true : null, purposeValid: domain === 'hard_surface' ? false : null, purposeState: domain === 'hard_surface' ? 'pending_remove_or_merge_review' : 'not_applicable'};
  report.production = production;
  report.topologyEvidence = evidence.topology;
  const glb = domain === 'inspect' && sourceBytes
    ? Buffer.from(sourceBytes)
    : Buffer.from(await (await io()).writeBinary(doc));
  return {glb, report: {...report, runVersion: FOUNDRY_RUN_VERSION, domain, reviewPreset, preservation: evidence.preservation}, evidence, reviewViews: evidence.reviewViews, hashes: {glb: hashBytes(glb)}};
}

export async function inspectGlbBytes(bytes) {
  const doc = await sourceDocument(bytes);
  return {report: inspectDocument(doc), preservation: preservationEvidence(doc)};
}
