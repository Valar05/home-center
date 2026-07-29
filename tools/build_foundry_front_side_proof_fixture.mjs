import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import {createSubdivisionCage, fitSubdivisionCageToModelSheet, subdivideCage, subdivisionCageDigest} from '../functions/foundry_model_sheet.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(path.join(root, 'functions/package.json'));
const {PNG} = require('pngjs');
const outputDir = path.join(root, 'docs', 'evidence', 'foundry-front-side-proof-v1');
fs.mkdirSync(outputDir, {recursive: true});

const width = 640, height = 640, pixelsPerMeter = 180, originPx = [320, 330];
const viewOrder = ['front', 'side'];
const frames = {
  front: {direction: [1, 0, 0], up: [0, 1, 0], horizontal: [0, 0, -1]},
  side: {direction: [0, 0, 1], up: [0, 1, 0], horizontal: [1, 0, 0]},
};
const cageSpec = {base: 'box', segments: [3, 2, 2], size: [2.2, 1.2, 1.6]};
const initialCage = createSubdivisionCage(cageSpec);
const targetCage = structuredClone(initialCage);
for (let index = 0; index < targetCage.positions.length; index++) {
  const [x, y, z] = targetCage.positions[index];
  const match = /^x(\d+):y(\d+):z(\d+)$/.exec(targetCage.ids[index]);
  const station = Number(match[1]), level = Number(match[2]);
  targetCage.positions[index] = [
    x + (level === 2 ? 0.10 * (station / 3 - 0.5) : 0),
    y + (level === 2 ? 0.16 * (0.5 - station / 3) : level === 0 ? 0.03 * Math.abs(station / 3 - 0.5) : 0),
    z * (1 - 0.22 * (level / 2)),
  ];
}
const targetSurface = subdivideCage(targetCage, 2);
function project(point, viewName) {
  const frame = frames[viewName];
  return [originPx[0] + (point[0] * frame.horizontal[0] + point[1] * frame.horizontal[1] + point[2] * frame.horizontal[2]) * pixelsPerMeter,
    originPx[1] - (point[0] * frame.up[0] + point[1] * frame.up[1] + point[2] * frame.up[2]) * pixelsPerMeter];
}
function convexHull(points) {
  const unique = [...new Map(points.map((point) => [point[0].toFixed(7) + ':' + point[1].toFixed(7), point])).values()].sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const cross = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
  const lower = [], upper = [];
  for (const point of unique) { while (lower.length >= 2 && cross(lower.at(-2), lower.at(-1), point) <= 0) lower.pop(); lower.push(point); }
  for (let index = unique.length - 1; index >= 0; index--) { const point = unique[index]; while (upper.length >= 2 && cross(upper.at(-2), upper.at(-1), point) <= 0) upper.pop(); upper.push(point); }
  lower.pop(); upper.pop(); return lower.concat(upper);
}
const contours = Object.fromEntries(viewOrder.map((viewName) => [viewName, convexHull(targetSurface.positions.map((point) => project(point, viewName)))]));
const inputSha256 = createHash('sha256').update(JSON.stringify({generator: 'home-center.foundry-front-side-proof', version: '1', cageSpec, contours})).digest('hex');
const fittingSheet = {scaleAnchor: {name: 'synthetic-width-anchor', meters: 2}, views: Object.fromEntries(viewOrder.map((name) => [name, {camera: frames[name], originPx, originWorld: [0, 0, 0], pixelsPerMeter, contourPx: contours[name]}]))};
const fittedCage = fitSubdivisionCageToModelSheet(initialCage, fittingSheet, {views: viewOrder, levels: 2, maxEvaluations: 4096});
const cageById = new Map(fittedCage.ids.map((id, index) => [id, fittedCage.positions[index]]));
const landmarkIds = {
  front: ['x0:y0:z0', 'x0:y0:z2', 'x0:y2:z0', 'x0:y2:z2'],
  side: ['x0:y0:z0', 'x3:y0:z0', 'x0:y2:z0', 'x3:y2:z0'],
};
function pointInPolygon(x, y, polygon) {
  let inside = false;
  for (let index = 0, previous = polygon.length - 1; index < polygon.length; previous = index++) {
    const a = polygon[index], b = polygon[previous];
    if (((a[1] > y) !== (b[1] > y)) && x < (b[0] - a[0]) * (y - a[1]) / ((b[1] - a[1]) || 1e-9) + a[0]) inside = !inside;
  }
  return inside;
}
function drawLine(png, a, b, color) {
  let x0 = Math.round(a[0]), y0 = Math.round(a[1]), x1 = Math.round(b[0]), y1 = Math.round(b[1]);
  const dx = Math.abs(x1 - x0), sx = x0 < x1 ? 1 : -1, dy = -Math.abs(y1 - y0), sy = y0 < y1 ? 1 : -1; let error = dx + dy;
  for (;;) {
    if (x0 >= 0 && x0 < width && y0 >= 0 && y0 < height) { const offset = (y0 * width + x0) * 4; png.data[offset] = color[0]; png.data[offset + 1] = color[1]; png.data[offset + 2] = color[2]; png.data[offset + 3] = 255; }
    if (x0 === x1 && y0 === y1) break;
    const twice = error * 2; if (twice >= dy) { error += dy; x0 += sx; } if (twice <= dx) { error += dx; y0 += sy; }
  }
}
function referencePng(contour) {
  const png = new PNG({width, height});
  for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
    const offset = (y * width + x) * 4, axis = x === originPx[0] || y === originPx[1], grid = x % 36 === 0 || y % 36 === 0, inside = pointInPolygon(x + 0.5, y + 0.5, contour);
    const color = axis ? [62, 84, 93] : grid ? [42, 48, 50] : inside ? [112, 120, 116] : [25, 29, 30];
    png.data[offset] = color[0]; png.data[offset + 1] = color[1]; png.data[offset + 2] = color[2]; png.data[offset + 3] = 255;
  }
  for (let index = 0; index < contour.length; index++) drawLine(png, contour[index], contour[(index + 1) % contour.length], [241, 211, 111]);
  const anchor = 2 * pixelsPerMeter; drawLine(png, [originPx[0] - anchor / 2, 600], [originPx[0] + anchor / 2, 600], [95, 220, 233]);
  return PNG.sync.write(png, {colorType: 6});
}
const views = {};
for (const viewName of viewOrder) {
  const bytes = referencePng(contours[viewName]);
  const filename = 'crude-turret-' + viewName + '.png'; fs.writeFileSync(path.join(outputDir, filename), bytes);
  views[viewName] = {imageLocal: {path: filename, sha256: createHash('sha256').update(bytes).digest('hex'), byteLength: bytes.length, mediaType: 'image/png'}, width, height, camera: frames[viewName], originPx, originWorld: [0, 0, 0], pixelsPerMeter, contourPx: contours[viewName], aperturesPx: [], landmarks: landmarkIds[viewName].map((id) => ({name: id, pixel: project(cageById.get(id), viewName), cagePointId: id}))};
}
const modelSheet = {contractVersion: 'home-center.foundry-model-sheet.v2', id: 'foundry-front-side-crude-turret-v1', units: 'm', viewOrder, axisFrame: {forward: [1, 0, 0], up: [0, 1, 0], left: [0, 0, 1]}, scaleAnchor: {name: 'synthetic-width-anchor', meters: 2}, authority: {scope: 'workflow_fixture', exactIdentity: 'intentionally crude neutral turret-like volume', productionUse: false}, provenance: [{sourceKind: 'synthetic_fixture', title: 'Home Center front-side shared-cage workflow fixture', generator: 'tools/build_foundry_front_side_proof_fixture.mjs', generatorVersion: '1', inputSha256, processing: 'Deterministic synthetic silhouettes for workflow validation only; not a real vehicle reference and not authorized for production modeling.'}], views};
fs.writeFileSync(path.join(outputDir, 'model-sheet.local.json'), JSON.stringify(modelSheet, null, 2) + '\n');
const topology = {coverage: 'all_output_vertices', purpose: 'silhouette', rationale: 'One shared fitted cage carries both declared synthetic silhouettes.', maxOutputVertices: 700, maxOutputTriangles: 1200, maxGrowthRatio: 32, simplification: {method: 'remove_or_merge', status: 'pending_review', maxVisibleErrorPx: 0.75}};
const productionBudget = {asset: {maxVertices: 700, maxTriangles: 1200}, components: {Crude_Turret_Volume: {maxVertices: 700, maxTriangles: 1200}}, scene: {instances: 1, maxExpandedVertices: 700, maxExpandedTriangles: 1200}};
const script = [
  "foundry.note('Front-side shared-cage workflow proof',{workflowFixture:true,views:['front','side']});",
  'foundry.validation.productionBudget(' + JSON.stringify(productionBudget) + ');',
  "foundry.material.create('neutral-proof',{baseColor:[0.46,0.48,0.47,1],metallic:0,roughness:1});",
  "foundry.scene.createSubdivisionCage('shared-proof-cage'," + JSON.stringify(cageSpec) + ');',
  "foundry.mesh.fitSubdivisionCage('shared-proof-cage',{views:['front','side'],levels:2,maxEvaluations:4096});",
  "foundry.mesh.subdivide('shared-proof-cage'," + JSON.stringify({scheme: 'catmull-clark', levels: 2, output: 'Crude_Turret_Volume', material: 'neutral-proof', topology}) + ');',
  "foundry.review.modelSheet({cage:'shared-proof-cage',target:'Crude_Turret_Volume',views:['front','side']});",
  "foundry.validation.assert('model_sheet_fit',{minIou:0.92,maxP95BoundaryErrorRingFraction:0.02,maxLandmarkErrorRingFraction:0.01});",
].join('\n');
fs.writeFileSync(path.join(outputDir, 'crude-turret-proof.foundry.js'), script + '\n');
const source = {schemaVersion: 'home-center.foundry-front-side-proof-source.v1', currentUserCommand: 'Implement the first-class front/side model-sheet workflow and run exactly one deterministic proof on one crude turret volume.', forbiddenStalePremise: ['D78461 or Sherman identity', 'manual cage control points in the Foundry proof script', 'beautification', 'geometry retry', 'candidate iteration'], modelSheet: {id: modelSheet.id, viewOrder, inputSha256}, cage: {spec: cageSpec, initialCageSha256: fittedCage.fit.initialCageSha256, expectedFittedCageSha256: subdivisionCageDigest(fittedCage), solver: fittedCage.fit.solver, evaluations: fittedCage.fit.evaluations, initialMetrics: fittedCage.fit.initial, finalMetrics: fittedCage.fit.final}, script: {path: 'crude-turret-proof.foundry.js', sha256: createHash('sha256').update(script + '\n').digest('hex')}};
fs.writeFileSync(path.join(outputDir, 'proof-source.json'), JSON.stringify(source, null, 2) + '\n');
console.log(JSON.stringify({outputDir, viewOrder, cage: source.cage, images: Object.fromEntries(viewOrder.map((name) => [name, views[name].imageLocal])), script: source.script}, null, 2));
