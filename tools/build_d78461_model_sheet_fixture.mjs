import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import {createSubdivisionCage, subdivideCage} from '../functions/foundry_model_sheet.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(path.join(root, 'functions/package.json'));
const {PNG} = require('pngjs');
const outputDir = path.join(root, 'docs', 'evidence', 'd78461-model-sheet-v7');
fs.mkdirSync(outputDir, {recursive: true});

const width = 640;
const height = 640;
const pixelsPerMeter = 220;
const originPx = [320, 330];
const scaleAnchor = {name: 'turret-ring-inside-diameter', meters: 1.7526};
const provenance = [
  {
    title: 'TM 9-752, Tank, Medium M4A3, 15 September 1944',
    url: 'https://www.ibiblio.org/hyperwar/USA/ref/TM/pdfs/TM9-752.pdf',
    license: 'public-domain-us-government',
    publisher: 'United States War Department',
    publishedAt: '1944-09-15',
    pages: ['6 (Figure 3)', '348-349 (Turret description)'],
    processing: 'Figure 3 and the one-piece armor-steel casting description were used as public-domain shape and feature evidence. The scanned page is not republished here; this sheet is a clean schematic normalization.',
  },
  {
    title: 'Development of Armored Vehicles, Volume 1',
    url: 'https://apps.dtic.mil/sti/pdfs/AD1116719.pdf',
    license: 'public-domain-us-government',
    publisher: 'United States Army, Army Ground Forces Board',
    publishedAt: '1947',
    processing: 'Used as public-domain historical corroboration for the M4-series development context. No source plate is republished.',
  },
];

const frames = {
  front: {direction: [1, 0, 0], up: [0, 1, 0], horizontal: [0, 0, -1]},
  side: {direction: [0, 0, 1], up: [0, 1, 0], horizontal: [1, 0, 0]},
  top: {direction: [0, 1, 0], up: [1, 0, 0], horizontal: [0, 0, 1]},
};

const desiredWorld = {
  front: [
    [-0.67, -0.47], [-0.78, -0.43], [-0.96, -0.25], [-1.06, 0], [-1.10, 0.30], [-1.05, 0.48], [-0.98, 0.60], [-0.885, 0.70], [-0.67, 0.81],
    [0, 0.83], [0.68, 0.81], [0.92, 0.71], [1.05, 0.60], [1.14, 0.46], [1.18, 0.25], [1.17, 0.08], [1.12, 0], [1.04, -0.25], [0.82, -0.43], [0.68, -0.47],
  ],
  side: [
    [-1.30, -0.10], [-1.34, 0.06], [-1.34, 0.55], [-1.28, 0.72], [-1.16, 0.82], [-0.90, 0.86], [-0.48, 0.86], [-0.12, 0.82],
    [0.30, 0.73], [0.64, 0.59], [0.86, 0.48], [1.04, 0.36], [1.14, 0.21], [1.17, 0.02], [1.16, -0.20], [1.06, -0.31], [0.80, -0.40], [0.40, -0.47], [0, -0.50], [-0.40, -0.47], [-0.76, -0.40], [-1.06, -0.28], [-1.22, -0.18],
  ],
  top: [
    [-0.72, -1.34], [-0.96, -1.20], [-1.08, -0.82], [-1.10, -0.30], [-1.08, 0.12], [-1.10, 0.55], [-1.00, 0.82], [-0.80, 1.06], [-0.62, 1.16],
    [0.52, 1.16], [0.82, 0.82], [0.98, 0.55], [1.08, 0.12], [1.10, -0.30], [1.08, -0.82], [0.96, -1.20], [0.72, -1.34],
  ],
};

function densify(points, steps = 8) {
  const dense = [];
  for (let index = 0; index < points.length; index++) {
    const a = points[index], b = points[(index + 1) % points.length];
    for (let step = 0; step < steps; step++) dense.push([a[0] + (b[0] - a[0]) * step / steps, a[1] + (b[1] - a[1]) * step / steps]);
  }
  return dense;
}
function toPixel([horizontal, vertical]) {
  return [
    Math.round((originPx[0] + horizontal * pixelsPerMeter) * 1000) / 1000,
    Math.round((originPx[1] - vertical * pixelsPerMeter) * 1000) / 1000,
  ];
}
function ellipsePixels(center, radii, segments = 32) {
  const out = [];
  for (let index = 0; index < segments; index++) {
    const angle = index * Math.PI * 2 / segments;
    out.push(toPixel([center[0] + Math.cos(angle) * radii[0], center[1] + Math.sin(angle) * radii[1]]));
  }
  return out;
}
const apertures = {
  front: [ellipsePixels([0.08, 0.10], [0.34, 0.27])],
  side: [ellipsePixels([-0.45, 0.15], [0.16, 0.16])],
  top: [ellipsePixels([0.34, -0.43], [0.27, 0.27]), ellipsePixels([-0.38, 0.21], [0.23, 0.23]), ellipsePixels([-0.20, -0.72], [0.10, 0.10])],
};

const xValues = [-1.34, -1.18, -0.72, 0.05, 0.88, 1.16];
const bottoms = [-0.10, -0.27, -0.47, -0.51, -0.38, -0.20];
const roofs = [0.68, 0.84, 0.86, 0.82, 0.52, 0.28];
let widths = [0.74, 1.02, 1.10, 1.08, 0.78, 0.54];
const yFractions = [0, 0.34, 0.72, 1];
const widthByLevel = [0.78, 1.0, 1.04, 0.72];
let rightCheekByStation = [0, 0, 0.015, 0.055, 0.16, 0.045];
const rightCheekByLevel = [0.40, 1, 1, 0.65];
function buildControlPoints(widthSet, cheekSet) {
  const points = [];
  for (let i = 0; i <= 5; i++) for (let j = 0; j <= 3; j++) for (let k = 0; k <= 4; k++) {
    if (!(i === 0 || i === 5 || j === 0 || j === 3 || k === 0 || k === 4)) continue;
    const y = bottoms[i] + (roofs[i] - bottoms[i]) * yFractions[j];
    const signedWidth = (k / 4 - 0.5) * 2;
    const cheek = signedWidth < 0 ? cheekSet[i] * rightCheekByLevel[j] * Math.abs(signedWidth) : 0;
    const z = signedWidth * widthSet[i] * widthByLevel[j] - cheek;
    points.push({id: 'x' + i + ':y' + j + ':z' + k, position: [xValues[i], y, z]});
  }
  return points;
}
function cross2(o, a, b) { return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]); }
function convexHull(points) {
  const sorted = [...new Map(points.map((p) => [p[0].toFixed(7) + ':' + p[1].toFixed(7), p])).values()].sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const lower = [], upper = [];
  for (const p of sorted) { while (lower.length >= 2 && cross2(lower.at(-2), lower.at(-1), p) <= 0) lower.pop(); lower.push(p); }
  for (let i = sorted.length - 1; i >= 0; i--) { const p = sorted[i]; while (upper.length >= 2 && cross2(upper.at(-2), upper.at(-1), p) <= 0) upper.pop(); upper.push(p); }
  lower.pop(); upper.pop(); return lower.concat(upper);
}
function samplePolygon(points, spacing = 0.025) {
  const out = [];
  for (let i = 0; i < points.length; i++) {
    const a = points[i], b = points[(i + 1) % points.length], length = Math.hypot(b[0] - a[0], b[1] - a[1]);
    const count = Math.max(1, Math.ceil(length / spacing));
    for (let n = 0; n < count; n++) out.push([a[0] + (b[0] - a[0]) * n / count, a[1] + (b[1] - a[1]) * n / count]);
  }
  return out;
}
function pointSegmentDistance(p, a, b) {
  const dx = b[0] - a[0], dy = b[1] - a[1], denom = dx * dx + dy * dy;
  const t = denom ? Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / denom)) : 0;
  return Math.hypot(p[0] - (a[0] + dx * t), p[1] - (a[1] + dy * t));
}
function nearestBoundary(point, polygon) {
  let best = Infinity;
  for (let i = 0; i < polygon.length; i++) best = Math.min(best, pointSegmentDistance(point, polygon[i], polygon[(i + 1) % polygon.length]));
  return best;
}
function percentile(values, fraction) { const sorted = [...values].sort((a, b) => a - b); return sorted[Math.min(sorted.length - 1, Math.floor((sorted.length - 1) * fraction))] || 0; }
function fitDiagnostics(widthSet, cheekSet) {
  const cage = createSubdivisionCage({base: 'box', segments: [5, 3, 4], size: [2.7, 1.4, 2.2], controlPoints: buildControlPoints(widthSet, cheekSet)});
  const surface = subdivideCage(cage, 2);
  const views = {};
  for (const viewName of ['front', 'top']) {
    const projected = surface.positions.map((point) => viewName === 'front' ? [-point[2], point[1]] : [point[2], point[0]]);
    const actual = convexHull(projected), target = desiredWorld[viewName];
    const targetSamples = samplePolygon(target), actualSamples = samplePolygon(actual);
    const forward = targetSamples.map((point) => nearestBoundary(point, actual));
    const reverse = actualSamples.map((point) => nearestBoundary(point, target));
    const p95 = percentile(forward, 0.95), reverseP95 = percentile(reverse, 0.95);
    views[viewName] = {p95Meters: p95, p95RingFraction: p95 / scaleAnchor.meters, reverseP95Meters: reverseP95, maxMeters: Math.max(...forward)};
  }
  return {score: views.front.p95Meters + views.top.p95Meters + 0.05 * (views.front.maxMeters + views.top.maxMeters), views};
}
function fitCage(seedWidths, seedCheeks) {
  let widthSet = [...seedWidths], cheekSet = [...seedCheeks], best = fitDiagnostics(widthSet, cheekSet), evaluations = 1;
  for (const step of [0.16, 0.08, 0.04, 0.02, 0.01, 0.005, 0.0025]) {
    let changed = true, sweeps = 0;
    while (changed && sweeps++ < 5) {
      changed = false;
      for (const family of ['width', 'cheek']) for (let index = 0; index < 6; index++) {
        for (const direction of [-1, 1]) {
          const nextWidths = [...widthSet], nextCheeks = [...cheekSet];
          if (family === 'width') nextWidths[index] = Math.max(0.35, Math.min(1.5, nextWidths[index] + direction * step));
          else nextCheeks[index] = Math.max(0, Math.min(1.0, nextCheeks[index] + direction * step));
          const candidate = fitDiagnostics(nextWidths, nextCheeks); evaluations++;
          if (candidate.score + 1e-8 < best.score) { widthSet = nextWidths; cheekSet = nextCheeks; best = candidate; changed = true; }
        }
      }
    }
  }
  return {widths: widthSet, cheeks: cheekSet, evaluations, ...best};
}
const fitted = fitCage(widths, rightCheekByStation);
widths = fitted.widths;
rightCheekByStation = fitted.cheeks;
const controlPoints = buildControlPoints(widths, rightCheekByStation);

function projectPoint(point, viewName) {
  const frame = frames[viewName];
  const horizontal = point[0] * frame.horizontal[0] + point[1] * frame.horizontal[1] + point[2] * frame.horizontal[2];
  const vertical = point[0] * frame.up[0] + point[1] * frame.up[1] + point[2] * frame.up[2];
  return toPixel([horizontal, vertical]);
}
const cageById = new Map(controlPoints.map((entry) => [entry.id, entry.position]));
function mirroredPoint(id) {
  if (cageById.has(id)) return cageById.get(id);
  const match = /^x(\d+):y(\d+):z(\d+)$/.exec(id);
  const mirror = 'x' + match[1] + ':y' + match[2] + ':z' + (4 - Number(match[3]));
  const point = cageById.get(mirror);
  return [point[0], point[1], -point[2]];
}
const landmarkIds = {
  front: ['x1:y0:z0', 'x1:y0:z4', 'x1:y3:z0', 'x1:y3:z4'],
  side: ['x0:y0:z0', 'x5:y0:z0', 'x0:y3:z0', 'x5:y3:z0'],
  top: ['x0:y1:z0', 'x0:y1:z4', 'x5:y1:z0', 'x5:y1:z4'],
};

function pointInPolygon(x, y, polygon) {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const xi = polygon[i][0], yi = polygon[i][1], xj = polygon[j][0], yj = polygon[j][1];
    if (((yi > y) !== (yj > y)) && x < (xj - xi) * (y - yi) / ((yj - yi) || 1e-9) + xi) inside = !inside;
  }
  return inside;
}
function drawLine(png, a, b, color, radius = 1) {
  let x0 = Math.round(a[0]), y0 = Math.round(a[1]), x1 = Math.round(b[0]), y1 = Math.round(b[1]);
  const dx = Math.abs(x1 - x0), sx = x0 < x1 ? 1 : -1, dy = -Math.abs(y1 - y0), sy = y0 < y1 ? 1 : -1;
  let error = dx + dy;
  for (;;) {
    for (let oy = -radius; oy <= radius; oy++) for (let ox = -radius; ox <= radius; ox++) {
      const x = x0 + ox, y = y0 + oy;
      if (x < 0 || x >= width || y < 0 || y >= height) continue;
      const offset = (y * width + x) * 4;
      png.data[offset] = color[0]; png.data[offset + 1] = color[1]; png.data[offset + 2] = color[2]; png.data[offset + 3] = 255;
    }
    if (x0 === x1 && y0 === y1) break;
    const twice = error * 2;
    if (twice >= dy) { error += dy; x0 += sx; }
    if (twice <= dx) { error += dx; y0 += sy; }
  }
}
function renderReference(viewName, contourPx, aperturePolygons) {
  const png = new PNG({width, height});
  for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
    const offset = (y * width + x) * 4;
    const grid = x % 44 === 0 || y % 44 === 0;
    const axis = x === originPx[0] || y === originPx[1];
    const inside = pointInPolygon(x + 0.5, y + 0.5, contourPx) && !aperturePolygons.some((polygon) => pointInPolygon(x + 0.5, y + 0.5, polygon));
    const color = axis ? [62, 84, 93] : grid ? [44, 51, 54] : inside ? [116, 126, 122] : [27, 31, 32];
    png.data[offset] = color[0]; png.data[offset + 1] = color[1]; png.data[offset + 2] = color[2]; png.data[offset + 3] = 255;
  }
  for (let index = 0; index < contourPx.length; index++) drawLine(png, contourPx[index], contourPx[(index + 1) % contourPx.length], [241, 211, 111], 1);
  for (const polygon of aperturePolygons) for (let index = 0; index < polygon.length; index++) drawLine(png, polygon[index], polygon[(index + 1) % polygon.length], [242, 124, 77], 1);
  const ringPixels = scaleAnchor.meters * pixelsPerMeter;
  drawLine(png, [originPx[0] - ringPixels / 2, 600], [originPx[0] + ringPixels / 2, 600], [95, 220, 233], 2);
  drawLine(png, [originPx[0] - ringPixels / 2, 590], [originPx[0] - ringPixels / 2, 610], [95, 220, 233], 2);
  drawLine(png, [originPx[0] + ringPixels / 2, 590], [originPx[0] + ringPixels / 2, 610], [95, 220, 233], 2);
  return PNG.sync.write(png, {colorType: 6});
}

const views = {};
for (const viewName of ['front', 'side', 'top']) {
  const contourPx = densify(desiredWorld[viewName]).map(toPixel);
  const bytes = renderReference(viewName, contourPx, apertures[viewName]);
  const filename = 'd78461-' + viewName + '.png';
  fs.writeFileSync(path.join(outputDir, filename), bytes);
  views[viewName] = {
    imageLocal: {path: filename, sha256: createHash('sha256').update(bytes).digest('hex'), byteLength: bytes.length, mediaType: 'image/png'},
    width,
    height,
    camera: frames[viewName],
    originPx,
    originWorld: [0, 0, 0],
    pixelsPerMeter,
    contourPx,
    aperturesPx: apertures[viewName],
    landmarks: landmarkIds[viewName].map((id) => ({name: id, pixel: projectPoint(mirroredPoint(id), viewName), cagePointId: id})),
  };
}

const modelSheet = {
  contractVersion: 'home-center.foundry-model-sheet.v1',
  id: 'd78461-bare-casting-v7',
  units: 'm',
  axisFrame: {forward: [1, 0, 0], up: [0, 1, 0], left: [0, 0, 1]},
  scaleAnchor,
  authority: {
    scope: 'manufacturing_casting',
    exactIdentity: 'D78461 high-bustle 75-mm wet-stowage turret casting',
    included: ['one connected cast shell', '69-inch ring opening', 'wide gun-mount aperture', 'commander opening', 'loader opening', 'left pistol-port opening', 'smoke-ejector opening'],
    excluded: ['mantlet', 'barrel', 'cupola', 'hatch covers', 'lifting eyes', 'fittings', 'textures', 'tank hull'],
    confidence: 'reference-constrained reconstruction; not a ballistic-thickness claim',
    revisionBasis: 'Supersedes v6 after the exaggerated cheek lobe was rejected as a reference-authority error; normalizes the D78461 cheek as a continuous asymmetric casting transition, retains the high bustle and casting apertures, and fits the bounded cage with the production Catmull-Clark kernel.',
  },
  provenance,
  views,
};
fs.writeFileSync(path.join(outputDir, 'model-sheet.local.json'), JSON.stringify(modelSheet, null, 2) + '\n');

function topologySpec(base, {purpose = 'silhouette', rationale, maxOutputVertices, maxOutputTriangles, maxGrowthRatio = 20, segmentCount = 0}) {
  const topology = {
    coverage: 'all_output_vertices',
    purpose,
    rationale,
    maxOutputVertices,
    maxOutputTriangles,
    maxGrowthRatio,
    simplification: {method: 'remove_or_merge', status: 'pending_review', maxVisibleErrorPx: 0.75},
  };
  if (segmentCount) topology.sampling = {basis: 'projected_error', segmentCount, projectedRadiusPx: 220, maxErrorPx: 0.75};
  return {...base, topology};
}
const productionBudget = {
  asset: {maxVertices: 6000, maxTriangles: 6000},
  components: {D78461_Bare_Casting: {maxVertices: 6000, maxTriangles: 6000}},
  scene: {instances: 1, maxExpandedVertices: 6000, maxExpandedTriangles: 6000},
};
const subdivisionSpec = topologySpec(
  {scheme: 'catmull-clark', levels: 2, output: 'd78461-casting-shell', material: 'cast-steel'},
  {rationale: 'The fitted cage vertices carry the registered front, side, and top casting silhouette.', maxOutputVertices: 1600, maxOutputTriangles: 3200},
);
const cylinder = (base, segments, rationale) => topologySpec(base, {
  purpose: 'mechanical_interface', rationale, segmentCount: segments, maxOutputVertices: 1024, maxOutputTriangles: 320, maxGrowthRatio: 4,
});
const booleanSpec = (rationale) => topologySpec({}, {
  purpose: 'mechanical_interface', rationale, maxOutputVertices: 6000, maxOutputTriangles: 6000, maxGrowthRatio: 20,
});
const ringCylinder = cylinder({radius: 0.8763, depth: 0.72, segments: 64, translation: [0, -0.25, 0], rotation: [0, 0, 0.7071067811865476, 0.7071067811865476]}, 64, 'The 64-sample ring tool establishes the calibrated 69-inch turret-ring interface.');
const gunCylinder = cylinder({radius: 0.22, depth: 0.72, segments: 48, translation: [1.08, 0.10, -0.08], scale: [1, 1.23, 1.55]}, 48, 'The gun opening sampling preserves its registered front-view mechanical rim.');
const commanderCylinder = cylinder({radius: 0.27, depth: 0.38, segments: 48, translation: [-0.43, 0.67, 0.34], rotation: [0, 0, 0.7071067811865476, 0.7071067811865476]}, 48, 'The commander opening sampling preserves its registered top-view mechanical rim.');
const loaderCylinder = cylinder({radius: 0.23, depth: 0.38, segments: 48, translation: [0.21, 0.64, -0.38], rotation: [0, 0, 0.7071067811865476, 0.7071067811865476]}, 48, 'The loader opening sampling preserves its registered top-view mechanical rim.');
const pistolCylinder = cylinder({radius: 0.16, depth: 0.80, segments: 40, translation: [-0.45, 0.15, 0.96], rotation: [0, 0.7071067811865476, 0, 0.7071067811865476]}, 40, 'The pistol-port sampling preserves its registered left-side mechanical rim.');
const smokeCylinder = cylinder({radius: 0.10, depth: 0.34, segments: 32, translation: [-0.72, 0.76, -0.20], rotation: [0, 0, 0.7071067811865476, 0.7071067811865476]}, 32, 'The smoke-ejector opening is an identifying D78461 roof interface.');
const ringBoolean = booleanSpec('The subtraction boundary creates the required 69-inch ring interface.');
const gunBoolean = booleanSpec('The subtraction boundary creates the required gun opening.');
const commanderBoolean = booleanSpec('The subtraction boundary creates the required commander opening.');
const loaderBoolean = booleanSpec('The subtraction boundary creates the required loader opening.');
const pistolBoolean = booleanSpec('The subtraction boundary creates the required left pistol-port opening.');
const smokeBoolean = booleanSpec('The subtraction boundary creates the D78461 smoke-ejector opening.');

const script = [
  "foundry.note('D78461 manufacturing casting only',{excluded:['mantlet','barrel','cupola','hatch covers','lifting eyes','fittings','textures','tank hull']});",
  "foundry.validation.productionBudget(" + JSON.stringify(productionBudget) + ");",
  "foundry.material.create('cast-steel',{baseColor:[0.12,0.15,0.13,1],metallic:0.05,roughness:0.90});",
  "const controlPoints = " + JSON.stringify(controlPoints) + ";",
  "foundry.scene.createSubdivisionCage('d78461-cage',{base:'box',segments:[5,3,4],size:[2.7,1.4,2.2],controlPoints});",
  "foundry.mesh.subdivide('d78461-cage'," + JSON.stringify(subdivisionSpec) + ");",
  "foundry.scene.createCylinder('ring-cavity'," + JSON.stringify(ringCylinder) + ");",
  "foundry.mesh.boolean('d78461-casting-shell','ring-cavity','subtract','d78461-ring-open'," + JSON.stringify(ringBoolean) + ");",
  "foundry.scene.createCylinder('gun-aperture'," + JSON.stringify(gunCylinder) + ");",
  "foundry.mesh.boolean('d78461-ring-open','gun-aperture','subtract','d78461-gun-open'," + JSON.stringify(gunBoolean) + ");",
  "foundry.scene.createCylinder('commander-opening'," + JSON.stringify(commanderCylinder) + ");",
  "foundry.mesh.boolean('d78461-gun-open','commander-opening','subtract','d78461-commander-open'," + JSON.stringify(commanderBoolean) + ");",
  "foundry.scene.createCylinder('loader-opening'," + JSON.stringify(loaderCylinder) + ");",
  "foundry.mesh.boolean('d78461-commander-open','loader-opening','subtract','d78461-loader-open'," + JSON.stringify(loaderBoolean) + ");",
  "foundry.scene.createCylinder('pistol-port-opening'," + JSON.stringify(pistolCylinder) + ");",
  "foundry.mesh.boolean('d78461-loader-open','pistol-port-opening','subtract','d78461-pistol-open'," + JSON.stringify(pistolBoolean) + ");",
  "foundry.scene.createCylinder('smoke-ejector-opening'," + JSON.stringify(smokeCylinder) + ");",
  "foundry.mesh.boolean('d78461-pistol-open','smoke-ejector-opening','subtract','D78461_Bare_Casting'," + JSON.stringify(smokeBoolean) + ");",
  "foundry.validation.assert('node_exists','D78461_Bare_Casting');",
  "foundry.review.modelSheet({cage:'d78461-cage',target:'D78461_Bare_Casting',views:['front','side','top']});",
  "foundry.validation.assert('model_sheet_fit',{minIou:0.92,maxP95BoundaryErrorRingFraction:0.02,maxLandmarkErrorRingFraction:0.01});",
  "foundry.review.fixedViews(['front','back','left','right','top','perspective']);",
].join('\n');
fs.writeFileSync(path.join(outputDir, 'd78461-bare-casting.foundry.js'), script + '\n');

const packet = {
  schemaVersion: 'home-center.foundry-proof-source.v1',
  createdAt: '2026-07-29',
  currentUserCommand: 'Repair Foundry with a first-class model-sheet workflow and prove it on the bare D78461 turret casting before generating another candidate.',
  forbiddenStalePremise: ['Blender generation', 'ring or section loft as acceptance', 'generic perspective views as model-sheet proof', 'full tank or accessorized turret candidate'],
  predecessorProof: {jobId: '3756ac92095ca1b8abcbdecdac630d6a1207cbec', publicationId: 'c2f2e97ef5f99b8890701ffe3efa5f5bcd5c1b43', resultHash: '776c457a8277472d4db020f28eced51a3dc8366f3af53866f26356d760356f8c', verdict: 'revision_requested', promotionAllowed: false},
  sourceAssets: Object.fromEntries(Object.entries(views).map(([name, view]) => [name, view.imageLocal])),
  script: {
    path: 'd78461-bare-casting.foundry.js',
    sha256: createHash('sha256').update(Buffer.from(script + '\n')).digest('hex'),
    byteLength: Buffer.byteLength(script + '\n'),
    version: 'foundry-js.v1',
  },
  cage: {base: 'box', segments: [5, 3, 4], authoredControlPoints: controlPoints.length, totalControlVertices: 96, subdivisionLevels: 2, expectedTrianglesBeforeBooleans: 3008, fitting: 'reproducible coordinate-descent using the production Foundry Catmull-Clark kernel against locked front and top contours while preserving the passing side fit; no plane averaging', fitDiagnostics: fitted},
  acceptance: {
    requiredRegisteredViews: ['front', 'side', 'top'],
    thresholds: {minIou: 0.92, maxP95BoundaryErrorRingFraction: 0.02, maxLandmarkErrorRingFraction: 0.01},
    passRule: 'front_and_side_and_top',
    successorCandidateGate: 'blocked_until_registered_fit_and_cloud_sense_and_human_artifact_review_are_accepted',
  },
  provenance,
};
fs.writeFileSync(path.join(outputDir, 'proof-source.json'), JSON.stringify(packet, null, 2) + '\n');
console.log(JSON.stringify({outputDir, images: packet.sourceAssets, script: packet.script, cage: packet.cage}, null, 2));
