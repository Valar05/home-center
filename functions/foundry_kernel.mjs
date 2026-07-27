import {createHash} from 'node:crypto';
import {Document, NodeIO, Accessor, getBounds, Logger, Verbosity} from '@gltf-transform/core';
import {KHRONOS_EXTENSIONS} from '@gltf-transform/extensions';
import pngjs from 'pngjs';

const {PNG} = pngjs;
export const FOUNDRY_RECIPE_VERSION = 'home-center.foundry-recipe.v1';
export const FOUNDRY_KERNEL_VERSION = 'fortress-model-foundry.v1';
export const FIXTURES = Object.freeze(['foundry-character-v1']);
const MAX_COMMANDS = 64;
const MAX_VERTICES = 250000;
const MAX_TRIANGLES = 500000;

function fail(code, message, details = {}) {
  const error = new Error(message);
  error.code = code;
  error.status = 400;
  error.details = details;
  return error;
}

function hashBytes(bytes) {
  return createHash('sha256').update(bytes).digest('hex');
}

function stable(value) {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stable(value[key])]));
  return value;
}

function hashJson(value) {
  return hashBytes(Buffer.from(JSON.stringify(stable(value))));
}

function io() {
  return new NodeIO().registerExtensions(KHRONOS_EXTENSIONS).setLogger(new Logger(Verbosity.SILENT));
}

function accessor(doc, buffer, name, type, array) {
  return doc.createAccessor(name, buffer).setType(type).setArray(array);
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
    const normal = faceNormal(a, b, c);
    const base = positions.length / 3;
    for (const point of [a, b, c]) {
      positions.push(...point);
      normals.push(...normal);
    }
    indices.push(base, base + 1, base + 2);
  }
  return {positions: new Float32Array(positions), normals: new Float32Array(normals), indices: new Uint32Array(indices)};
}

function makeMesh(doc, buffer, name, data, material, extras = {}) {
  const primitive = doc.createPrimitive()
    .setAttribute('POSITION', accessor(doc, buffer, `${name}:POSITION`, Accessor.Type.VEC3, data.positions))
    .setAttribute('NORMAL', accessor(doc, buffer, `${name}:NORMAL`, Accessor.Type.VEC3, data.normals))
    .setIndices(accessor(doc, buffer, `${name}:INDICES`, Accessor.Type.SCALAR, data.indices))
    .setMaterial(material);
  for (const [semantic, entry] of Object.entries(extras.attributes || {})) {
    primitive.setAttribute(semantic, accessor(doc, buffer, `${name}:${semantic}`, entry.type, entry.array));
  }
  if (extras.morphPosition) {
    primitive.addTarget(doc.createPrimitiveTarget(`${name}:morph`).setAttribute('POSITION', accessor(doc, buffer, `${name}:MORPH_POSITION`, Accessor.Type.VEC3, extras.morphPosition)));
  }
  return doc.createMesh(name).addPrimitive(primitive).setWeights(extras.morphPosition ? [0] : []);
}

function chamferedBoxData(size = [1, 1, 1], bevel = 0.08) {
  const [sx, sy, sz] = size.map(Number);
  const hx = sx / 2, hy = sy / 2, hz = sz / 2;
  const c = Math.max(0, Math.min(Number(bevel) || 0, hx * 0.45, hz * 0.45));
  const profile = [[-hx + c, -hz], [hx - c, -hz], [hx, -hz + c], [hx, hz - c], [hx - c, hz], [-hx + c, hz], [-hx, hz - c], [-hx, -hz + c]];
  const vertices = [];
  for (const y of [-hy, hy]) for (const [x, z] of profile) vertices.push([x, y, z]);
  const faces = [];
  for (let i = 1; i < profile.length - 1; i++) faces.push([0, i + 1, i]);
  for (let i = 1; i < profile.length - 1; i++) faces.push([8, 8 + i, 8 + i + 1]);
  for (let i = 0; i < profile.length; i++) {
    const j = (i + 1) % profile.length;
    faces.push([i, j, 8 + j], [i, 8 + j, 8 + i]);
  }
  return flatMeshData(vertices, faces);
}

function boxData(size = [1, 1, 1]) {
  return chamferedBoxData(size, 0);
}

function cylinderData(radius = 0.2, depth = 0.2, segments = 16) {
  const count = Math.max(6, Math.min(64, Math.floor(segments)));
  const vertices = [];
  for (const x of [-depth / 2, depth / 2]) for (let i = 0; i < count; i++) {
    const angle = i * Math.PI * 2 / count;
    vertices.push([x, Math.cos(angle) * radius, Math.sin(angle) * radius]);
  }
  const faces = [];
  for (let i = 1; i < count - 1; i++) faces.push([0, i, i + 1], [count, count + i + 1, count + i]);
  for (let i = 0; i < count; i++) {
    const j = (i + 1) % count;
    faces.push([i, count + j, j], [i, count + i, count + j]);
  }
  return flatMeshData(vertices, faces);
}

function material(doc, name, color, metallic = 0, roughness = 0.7) {
  return doc.createMaterial(name).setBaseColorFactor(color).setMetallicFactor(metallic).setRoughnessFactor(roughness);
}

function newDocument() {
  const doc = new Document();
  doc.setLogger(new Logger(Verbosity.SILENT));
  return {doc, buffer: doc.createBuffer('foundry-buffer'), scene: doc.createScene('Foundry Scene')};
}

export function buildMechanicalDocument(parameters = {}) {
  const {doc, buffer, scene} = newDocument();
  const steel = material(doc, 'Foundry gunmetal', [0.16, 0.19, 0.2, 1], 0.72, 0.28);
  const accent = material(doc, 'Foundry safety red', [0.62, 0.055, 0.04, 1], 0.25, 0.42);
  const baseMesh = makeMesh(doc, buffer, 'profile-extruded-base', chamferedBoxData([2.8, 0.45, 1.4], 0.16), steel);
  scene.addChild(doc.createNode('profile-extruded-base').setMesh(baseMesh));
  const bracketMesh = makeMesh(doc, buffer, 'mirrored-bracket', chamferedBoxData([0.34, 0.9, 0.78], 0.08), accent);
  for (const side of [-1, 1]) scene.addChild(doc.createNode(side < 0 ? 'bracket-left-mirrored' : 'bracket-right').setMesh(bracketMesh).setTranslation([side * 1.06, 0.52, 0]));
  const wheelMesh = makeMesh(doc, buffer, 'instanced-wheel', cylinderData(0.34, 0.22, parameters.segments || 20), steel);
  for (const x of [-0.72, 0, 0.72]) for (const z of [-0.54, 0.54]) {
    scene.addChild(doc.createNode(`wheel-${x}-${z}`).setMesh(wheelMesh).setTranslation([x, -0.34, z]));
  }
  const socketMesh = makeMesh(doc, buffer, 'socket', cylinderData(0.23, 0.52, 24), accent);
  scene.addChild(doc.createNode('socket').setMesh(socketMesh).setTranslation([0, 0.54, 0]));
  return doc;
}

function identityMatrices(count) {
  const out = new Float32Array(count * 16);
  for (let i = 0; i < count; i++) out.set([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1], i * 16);
  return out;
}

export function buildCharacterFixtureDocument() {
  const {doc, buffer, scene} = newDocument();
  const bodyMaterial = material(doc, 'fixture-body', [0.18, 0.34, 0.58, 1], 0, 0.78);
  const data = boxData([0.75, 1.65, 0.38]);
  const vertexCount = data.positions.length / 3;
  const joints = new Uint16Array(vertexCount * 4);
  const weights = new Float32Array(vertexCount * 4);
  for (let i = 0; i < vertexCount; i++) { joints[i * 4] = data.positions[i * 3 + 1] > 0 ? 1 : 0; weights[i * 4] = 1; }
  const morph = new Float32Array(data.positions.length);
  for (let i = 0; i < vertexCount; i++) morph[i * 3] = data.positions[i * 3 + 1] > 0.5 ? 0.025 : 0;
  const mesh = makeMesh(doc, buffer, 'fixture-character-mesh', data, bodyMaterial, {attributes: {
    JOINTS_0: {type: Accessor.Type.VEC4, array: joints},
    WEIGHTS_0: {type: Accessor.Type.VEC4, array: weights},
  }, morphPosition: morph});
  const hips = doc.createNode('hips').setTranslation([0, -0.7, 0]);
  const spine = doc.createNode('spine').setTranslation([0, 0.75, 0]);
  const hand = doc.createNode('hand_r').setTranslation([0.66, 0.5, 0]);
  hips.addChild(spine); spine.addChild(hand); scene.addChild(hips);
  const ibm = accessor(doc, buffer, 'fixture-inverse-bind-matrices', Accessor.Type.MAT4, identityMatrices(3));
  const skin = doc.createSkin('fixture-skin').setSkeleton(hips).setInverseBindMatrices(ibm).addJoint(hips).addJoint(spine).addJoint(hand);
  scene.addChild(doc.createNode('fixture-character').setMesh(mesh).setSkin(skin).setWeights([0]));
  const times = accessor(doc, buffer, 'idle-times', Accessor.Type.SCALAR, new Float32Array([0, 0.5, 1]));
  const rotations = accessor(doc, buffer, 'idle-hand-rotations', Accessor.Type.VEC4, new Float32Array([0, 0, 0, 1, 0, 0, 0.130526, 0.991445, 0, 0, 0, 1]));
  const sampler = doc.createAnimationSampler('idle-hand-sampler').setInput(times).setOutput(rotations).setInterpolation('LINEAR');
  const channel = doc.createAnimationChannel('idle-hand-channel').setSampler(sampler).setTargetNode(hand).setTargetPath('rotation');
  doc.createAnimation('fixture_idle').addSampler(sampler).addChannel(channel);
  return doc;
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
  const evidence = {meshes, skins, animations};
  return {...evidence, hashes: {meshes: hashJson(meshes), skins: hashJson(skins), animations: hashJson(animations)}};
}

function nodeByName(doc, name) {
  const node = doc.getRoot().listNodes().find((candidate) => candidate.getName() === name);
  if (!node) throw fail('foundry.recipe.node_not_found', `Node not found: ${name}`, {name});
  return node;
}

export function applyCharacterSetup(doc, parameters = {}) {
  const handName = String(parameters.handBone || 'hand_r');
  const weaponBoneName = String(parameters.weaponBone || 'weapon_socket_r');
  const hand = nodeByName(doc, handName);
  if (doc.getRoot().listNodes().some((node) => node.getName() === weaponBoneName)) throw fail('foundry.recipe.name_conflict', `Node already exists: ${weaponBoneName}`);
  const before = preservationEvidence(doc);
  const socket = doc.createNode(weaponBoneName).setTranslation(parameters.translation || [0.24, 0, 0]).setRotation(parameters.rotation || [0, 0, 0, 1]);
  hand.addChild(socket);
  const skin = doc.getRoot().listSkins()[0];
  if (!skin) throw fail('foundry.recipe.skin_required', 'Character setup requires an existing skin.');
  const oldMatrices = skin.getInverseBindMatrices()?.getArray();
  const nextMatrices = identityMatrices(skin.listJoints().length + 1);
  if (oldMatrices) nextMatrices.set(oldMatrices.slice(0, skin.listJoints().length * 16));
  const buffer = doc.getRoot().listBuffers()[0] || doc.createBuffer('foundry-buffer');
  skin.setInverseBindMatrices(accessor(doc, buffer, `${weaponBoneName}:inverse-bind-matrices`, Accessor.Type.MAT4, nextMatrices)).addJoint(socket);
  const propMaterial = material(doc, 'fixture-rigid-weapon', [0.48, 0.5, 0.52, 1], 0.8, 0.22);
  const prop = doc.createNode(String(parameters.propName || 'fixture_weapon')).setMesh(makeMesh(doc, buffer, 'fixture-rigid-weapon', chamferedBoxData([0.62, 0.08, 0.1], 0.018), propMaterial)).setTranslation([0.3, 0, 0]);
  socket.addChild(prop);
  const after = preservationEvidence(doc);
  const oldJointCount = before.skins[0].joints.length;
  const originalMeshNames = new Set(before.meshes.map((mesh) => mesh.name));
  const originalMeshesAfter = after.meshes.filter((mesh) => originalMeshNames.has(mesh.name));
  const preserved = {
    meshHashEqual: hashJson(before.meshes) === hashJson(originalMeshesAfter),
    animationHashEqual: before.hashes.animations === after.hashes.animations,
    originalJointOrderPreserved: JSON.stringify(after.skins[0].joints.slice(0, oldJointCount)) === JSON.stringify(before.skins[0].joints),
    originalInverseBindPrefixPreserved: oldMatrices ? hashBytes(Buffer.from(oldMatrices.buffer, oldMatrices.byteOffset, oldMatrices.byteLength)) === hashBytes(Buffer.from(nextMatrices.buffer, nextMatrices.byteOffset, oldMatrices.byteLength)) : true,
    addedJoint: after.skins[0].joints.at(-1),
    rigidPropSkinned: !!prop.getSkin(),
  };
  if (!preserved.meshHashEqual || !preserved.animationHashEqual || !preserved.originalJointOrderPreserved || !preserved.originalInverseBindPrefixPreserved || preserved.rigidPropSkinned) {
    throw fail('foundry.preservation.failed', 'Character setup changed unrelated character data.', preserved);
  }
  return {before, after, preserved};
}

function lerp(a, b, t) { return a + (b - a) * t; }
function normalizeQuaternion(values) {
  const length = Math.hypot(...values) || 1;
  return values.map((value) => value / length);
}

export function applyAnimationEdit(doc, parameters = {}) {
  const clipName = String(parameters.clip || 'fixture_idle');
  const animation = doc.getRoot().listAnimations().find((entry) => entry.getName() === clipName);
  if (!animation) throw fail('foundry.recipe.clip_not_found', `Animation clip not found: ${clipName}`);
  const before = preservationEvidence(doc);
  const start = Number(parameters.start ?? 0.2), end = Number(parameters.end ?? 0.8), duration = Number(parameters.duration ?? 1.2);
  if (!(start >= 0 && end > start && duration > 0 && duration <= 30)) throw fail('foundry.recipe.invalid_time_range', 'Animation trim/retime range is invalid.');
  let changedChannels = 0;
  for (const channel of animation.listChannels()) {
    const sampler = channel.getSampler();
    const input = sampler?.getInput()?.getArray();
    const output = sampler?.getOutput()?.getArray();
    if (!input || !output || sampler.getInterpolation() === 'CUBICSPLINE') continue;
    const width = output.length / input.length;
    const sourceTimes = [start, ...Array.from(input).filter((time) => time > start && time < end), end];
    const sample = (time) => {
      let upper = 1; while (upper < input.length && input[upper] < time) upper += 1;
      upper = Math.min(upper, input.length - 1); const lower = Math.max(0, upper - 1);
      const span = input[upper] - input[lower]; const alpha = span > 0 ? (time - input[lower]) / span : 0;
      const valuesAtTime = [];
      for (let component = 0; component < width; component++) valuesAtTime.push(lerp(output[lower * width + component], output[upper * width + component], alpha));
      return channel.getTargetPath() === 'rotation' ? normalizeQuaternion(valuesAtTime) : valuesAtTime;
    };
    const times = new Float32Array(sourceTimes.length);
    const values = new Float32Array(sourceTimes.length * width);
    sourceTimes.forEach((sourceTime, index) => {
      times[index] = (sourceTime - start) / (end - start) * duration;
      values.set(sample(sourceTime), index * width);
    });
    if (channel.getTargetNode()?.getName() === String(parameters.targetBone || 'hand_r') && channel.getTargetPath() === 'rotation' && values.length >= 4) {
      const offset = Math.floor(sourceTimes.length / 2) * width;
      const adjusted = normalizeQuaternion([values[offset], values[offset + 1], values[offset + 2] + Number(parameters.rotationDeltaZ ?? 0.12), values[offset + 3]]);
      values.set(adjusted, offset);
    }
    sampler.getInput().setArray(times);
    sampler.getOutput().setArray(values);
    changedChannels += 1;
  }
  if (!changedChannels) throw fail('foundry.recipe.no_editable_channels', 'No bounded animation channels matched the edit.');
  animation.setName(String(parameters.outputClip || `${clipName}_foundry`));
  const after = preservationEvidence(doc);
  const preserved = {geometryHashEqual: before.hashes.meshes === after.hashes.meshes, skinHashEqual: before.hashes.skins === after.hashes.skins, changedChannels, sourceClip: clipName, outputClip: animation.getName(), duration};
  if (!preserved.geometryHashEqual || !preserved.skinHashEqual) throw fail('foundry.preservation.failed', 'Animation edit changed geometry or skin data.', preserved);
  return {before, after, preserved};
}

function edgeKey(a, b) { return a < b ? `${a}:${b}` : `${b}:${a}`; }
function vertexKey(position, index) { return [position[index * 3], position[index * 3 + 1], position[index * 3 + 2]].map((value) => Math.round(value * 1000000)).join(','); }

export function inspectDocument(doc) {
  const root = doc.getRoot();
  let triangles = 0, vertices = 0, degenerateTriangles = 0, invalidNormals = 0;
  const components = [];
  for (const node of root.listNodes()) {
    const mesh = node.getMesh();
    if (!mesh) continue;
    let nodeTriangles = 0, nodeVertices = 0, boundaryEdges = 0, nonManifoldEdges = 0;
    for (const primitive of mesh.listPrimitives()) {
      const position = primitive.getAttribute('POSITION')?.getArray();
      const normal = primitive.getAttribute('NORMAL')?.getArray();
      const index = primitive.getIndices()?.getArray();
      const count = position ? position.length / 3 : 0;
      nodeVertices += count;
      if (normal) for (let i = 0; i < normal.length; i += 3) if (Math.abs(Math.hypot(normal[i], normal[i + 1], normal[i + 2]) - 1) > 0.02) invalidNormals += 1;
      const indices = index ? Array.from(index) : Array.from({length: count}, (_, i) => i);
      const edges = new Map();
      for (let i = 0; i + 2 < indices.length; i += 3) {
        const a = vertexKey(position, indices[i]), b = vertexKey(position, indices[i + 1]), c = vertexKey(position, indices[i + 2]);
        if (a === b || b === c || c === a) degenerateTriangles += 1;
        for (const key of [edgeKey(a, b), edgeKey(b, c), edgeKey(c, a)]) edges.set(key, (edges.get(key) || 0) + 1);
        nodeTriangles += 1;
      }
      for (const countValue of edges.values()) { if (countValue === 1) boundaryEdges += 1; if (countValue > 2) nonManifoldEdges += 1; }
    }
    triangles += nodeTriangles; vertices += nodeVertices;
    components.push({node: node.getName(), mesh: mesh.getName(), triangles: nodeTriangles, vertices: nodeVertices, boundaryEdges, nonManifoldEdges, instanced: root.listNodes().filter((candidate) => candidate.getMesh() === mesh).length > 1});
  }
  if (vertices > MAX_VERTICES || triangles > MAX_TRIANGLES) throw fail('foundry.limit.geometry', 'Geometry exceeds Foundry MVP limits.', {vertices, triangles, maxVertices: MAX_VERTICES, maxTriangles: MAX_TRIANGLES});
  const bounds = getBounds(doc.getRoot().listScenes()[0] || root.listNodes()[0]);
  return {
    kernelVersion: FOUNDRY_KERNEL_VERSION,
    bounds: {min: Array.from(bounds.min), max: Array.from(bounds.max), size: bounds.min.map((value, i) => bounds.max[i] - value)},
    triangleCount: triangles,
    vertexCount: vertices,
    componentCount: components.length,
    components: components.slice(0, 100),
    validation: {degenerateTriangles, invalidNormals, nonManifoldComponents: components.filter((entry) => entry.nonManifoldEdges > 0).length, manifoldClosedComponents: components.filter((entry) => entry.boundaryEdges === 0 && entry.nonManifoldEdges === 0).length},
    hierarchy: root.listNodes().slice(0, 200).map((node) => ({name: node.getName(), parent: node.getParentNode()?.getName() || null, mesh: node.getMesh()?.getName() || null, skin: node.getSkin()?.getName() || null})),
    animations: root.listAnimations().map((animation) => ({name: animation.getName(), channelCount: animation.listChannels().length, duration: Math.max(0, ...animation.listSamplers().map((sampler) => { const values = sampler.getInput()?.getArray(); return values && values.length ? values[values.length - 1] : 0; }))})),
    skins: root.listSkins().map((skin) => ({name: skin.getName(), joints: skin.listJoints().map((node) => node.getName())})),
  };
}

function color(hex) {
  return [parseInt(hex.slice(1, 3), 16), parseInt(hex.slice(3, 5), 16), parseInt(hex.slice(5, 7), 16), 255];
}

function pixel(png, x, y, rgba) {
  if (x < 0 || y < 0 || x >= png.width || y >= png.height) return;
  const index = (Math.floor(y) * png.width + Math.floor(x)) * 4;
  for (let i = 0; i < 4; i++) png.data[index + i] = rgba[i];
}

function line(png, x0, y0, x1, y1, rgba) {
  let dx = Math.abs(x1 - x0), sx = x0 < x1 ? 1 : -1, dy = -Math.abs(y1 - y0), sy = y0 < y1 ? 1 : -1, error = dx + dy;
  while (true) { pixel(png, x0, y0, rgba); if (x0 === x1 && y0 === y1) break; const e2 = 2 * error; if (e2 >= dy) { error += dy; x0 += sx; } if (e2 <= dx) { error += dx; y0 += sy; } }
}

function fill(png, rgba) {
  for (let i = 0; i < png.data.length; i += 4) png.data.set(rgba, i);
}

function collectPositionEdges(doc) {
  const edges = [];
  for (const node of doc.getRoot().listNodes()) {
    const translation = node.getTranslation();
    const scale = node.getScale();
    for (const primitive of node.getMesh()?.listPrimitives() || []) {
      const positions = primitive.getAttribute('POSITION')?.getArray();
      const indices = primitive.getIndices()?.getArray();
      if (!positions || !indices) continue;
      const point = (index) => [positions[index * 3] * scale[0] + translation[0], positions[index * 3 + 1] * scale[1] + translation[1], positions[index * 3 + 2] * scale[2] + translation[2]];
      for (let i = 0; i < indices.length; i += 3) {
        const a = point(indices[i]), b = point(indices[i + 1]), c = point(indices[i + 2]);
        edges.push([a, b], [b, c], [c, a]);
      }
    }
  }
  return edges;
}

function project(point, view) {
  if (view === 'front') return [point[0], point[1]];
  if (view === 'right') return [point[2], point[1]];
  if (view === 'top') return [point[0], point[2]];
  return [point[0] - point[2] * 0.55, point[1] + point[2] * 0.32];
}

export function renderContactSheet(doc, options = {}) {
  const views = options.views || ['front', 'right', 'top', 'perspective'];
  const panel = 320, png = new PNG({width: panel * views.length, height: panel});
  fill(png, color('#f4f2ec'));
  const edges = collectPositionEdges(doc);
  views.forEach((view, panelIndex) => {
    const points = edges.flat().map((point) => project(point, view));
    const xs = points.map((point) => point[0]), ys = points.map((point) => point[1]);
    const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
    const scale = 250 / Math.max(maxX - minX || 1, maxY - minY || 1);
    const map = (point) => [panelIndex * panel + 160 + (point[0] - (minX + maxX) / 2) * scale, 160 - (point[1] - (minY + maxY) / 2) * scale];
    for (const edge of edges) { const a = map(project(edge[0], view)), b = map(project(edge[1], view)); line(png, Math.round(a[0]), Math.round(a[1]), Math.round(b[0]), Math.round(b[1]), color('#263238')); }
    line(png, panelIndex * panel + 18, 290, panelIndex * panel + 302, 290, color('#b7372f'));
  });
  return PNG.sync.write(png, {colorType: 6});
}

export function renderSkeletonOverlay(doc) {
  const png = new PNG({width: 640, height: 480}); fill(png, color('#11171a'));
  const nodes = doc.getRoot().listNodes();
  const world = new Map();
  const position = (node) => {
    if (world.has(node)) return world.get(node);
    const local = node.getTranslation(); const parent = node.getParentNode(); const base = parent ? position(parent) : [0, 0, 0];
    const result = [base[0] + local[0], base[1] + local[1], base[2] + local[2]]; world.set(node, result); return result;
  };
  for (const node of nodes) {
    const parent = node.getParentNode(); if (!parent) continue;
    const a = position(parent), b = position(node);
    line(png, Math.round(320 + a[0] * 180), Math.round(410 - a[1] * 180), Math.round(320 + b[0] * 180), Math.round(410 - b[1] * 180), node.getName().includes('weapon') ? color('#ff6259') : color('#69d5ff'));
  }
  return PNG.sync.write(png, {colorType: 6});
}

function validateRecipe(recipe) {
  if (!recipe || recipe.version !== FOUNDRY_RECIPE_VERSION) throw fail('foundry.recipe.unsupported_version', `Unsupported recipe version: ${recipe?.version || 'missing'}`, {supported: [FOUNDRY_RECIPE_VERSION]});
  if (!['hard_surface', 'character_setup', 'animation', 'inspect'].includes(recipe.domain)) throw fail('foundry.recipe.unsupported_domain', `Unsupported Foundry domain: ${recipe.domain}`);
  const commands = Array.isArray(recipe.commands) ? recipe.commands : [];
  if (commands.length > MAX_COMMANDS) throw fail('foundry.limit.commands', `Recipe exceeds ${MAX_COMMANDS} commands.`);
  const supported = {
    hard_surface: ['mechanical_specimen'],
    character_setup: ['add_weapon_bone', 'attach_rigid_prop'],
    animation: ['trim_clip', 'retime_clip', 'set_rotation_key'],
    inspect: ['inspect'],
  }[recipe.domain];
  for (const command of commands) if (!supported.includes(command.op)) throw fail('foundry.recipe.unsupported_operation', `Unsupported ${recipe.domain} operation: ${command.op}`, {supported});
  return recipe;
}

export async function sourceDocument(sourceBytes, fixtureId) {
  if (sourceBytes) return io().readBinary(new Uint8Array(sourceBytes));
  if (fixtureId === 'foundry-character-v1') return buildCharacterFixtureDocument();
  throw fail('foundry.source.required', 'This recipe requires a GLB source or supported fixture reference.', {fixtures: FIXTURES});
}

export async function runFoundryKernel({recipe, parameters = {}, sourceBytes = null, fixtureId = '', reviewPreset = 'fixed-four-view'}) {
  validateRecipe(recipe);
  let doc, mutationEvidence = null;
  if (recipe.domain === 'hard_surface') doc = buildMechanicalDocument(parameters);
  else {
    doc = await sourceDocument(sourceBytes, fixtureId);
    if (recipe.domain === 'character_setup') mutationEvidence = applyCharacterSetup(doc, parameters);
    if (recipe.domain === 'animation') mutationEvidence = applyAnimationEdit(doc, parameters);
  }
  const report = inspectDocument(doc);
  const glb = Buffer.from(await io().writeBinary(doc));
  const contactSheet = renderContactSheet(doc);
  const skeletalOverlay = ['character_setup', 'animation'].includes(recipe.domain) ? renderSkeletonOverlay(doc) : null;
  return {
    glb,
    contactSheet,
    skeletalOverlay,
    report: {...report, recipeVersion: recipe.version, domain: recipe.domain, reviewPreset, preservation: mutationEvidence?.preserved || null},
    evidence: mutationEvidence,
    hashes: {glb: hashBytes(glb), contactSheet: hashBytes(contactSheet), skeletalOverlay: skeletalOverlay ? hashBytes(skeletalOverlay) : null},
  };
}

export async function inspectGlbBytes(bytes) {
  const doc = await io().readBinary(new Uint8Array(bytes));
  return {report: inspectDocument(doc), preservation: preservationEvidence(doc)};
}
