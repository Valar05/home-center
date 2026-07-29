import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import {createRequire} from 'node:module';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(path.join(root, 'functions/package.json'));
const {FOUNDRY_MODEL_SHEET_VERSION, resolveModelSheet, modelSheetRecordFields, modelSheetFromRecord} = require('../functions/foundry_capability.js');
const {executeFoundryScript} = await import('../functions/foundry_script_runtime.mjs');
const {runFoundryKernel} = await import('../functions/foundry_kernel.mjs');
const {createSubdivisionCage, subdivideCage} = await import('../functions/foundry_model_sheet.mjs');
const {evaluateRegisteredFit, evaluateApertureFit, REVIEW_WIDTH, REVIEW_HEIGHT} = await import('../functions/foundry_review_renderer.mjs');

function digest(bytes) {
  return crypto.createHash('sha256').update(bytes).digest('hex');
}

function topologySpec(base, {purpose = 'silhouette', rationale = 'The output vertices preserve the commissioned visible form.', maxVertices = 4096, maxTriangles = 8192, maxGrowthRatio = 20} = {}) {
  return {...base, topology: {coverage: 'all_output_vertices', purpose, rationale, maxOutputVertices: maxVertices, maxOutputTriangles: maxTriangles, maxGrowthRatio, simplification: {method: 'remove_or_merge', status: 'pending_review', maxVisibleErrorPx: 0.75}}};
}
function productionBudget(component, maxVertices = 4096, maxTriangles = 8192) {
  return {asset: {maxVertices, maxTriangles}, components: {[component]: {maxVertices, maxTriangles}}, scene: {instances: 1, maxExpandedVertices: maxVertices, maxExpandedTriangles: maxTriangles}};
}

class FakeStorage {
  constructor() {
    this.objects = new Map();
  }
  bucket(name) {
    const store = this.objects;
    return {
      file(objectName) {
        return {
          async download(options = {}) {
            const bytes = store.get(name + '/' + objectName);
            if (!bytes) throw new Error('missing object ' + name + '/' + objectName);
            if (options.destination) {
              const fs = await import('node:fs/promises');
              await fs.writeFile(options.destination, bytes);
              return;
            }
            return [Buffer.from(bytes)];
          },
        };
      },
    };
  }
}

function artifact(storage, owner, id, mediaType = 'image/png') {
  const bytes = Buffer.from('registered-' + id);
  const objectName = 'canonical/' + id + '.png';
  const identity = {kind: 'home_center_artifact', artifactId: id, sha256: digest(bytes), byteLength: bytes.length};
  storage.objects.set('home-center-generated/' + objectName, bytes);
  storage.objects.set(
    'home-center-generated/indexes/artifacts/v1/by-id/' + owner + '/' + id + '.json',
    Buffer.from(JSON.stringify({
      source: {name: id + '.png', mimeType: mediaType},
      destination: {bucket: 'home-center-generated', objectName, byteCount: bytes.length, sha256: identity.sha256},
    })),
  );
  return identity;
}

function view(image, name) {
  const frames = {
    front: {direction: [1, 0, 0], up: [0, 1, 0], horizontal: [0, 0, -1]},
    side: {direction: [0, 0, 1], up: [0, 1, 0], horizontal: [1, 0, 0]},
    top: {direction: [0, 1, 0], up: [1, 0, 0], horizontal: [0, 0, 1]},
  };
  return {
    image,
    width: 640,
    height: 640,
    camera: frames[name],
    originPx: [320, 360],
    originWorld: [0, 0, 0],
    pixelsPerMeter: 200,
    contourPx: [[100, 100], [540, 100], [540, 540], [100, 540]],
    landmarks: [
      {name: 'a', pixel: [100, 100], cagePointId: 'x0:y0:z0'},
      {name: 'b', pixel: [540, 100], cagePointId: 'x4:y0:z0'},
      {name: 'c', pixel: [540, 540], cagePointId: 'x4:y3:z4'},
    ],
  };
}

const cage = createSubdivisionCage({
  base: 'box',
  segments: [4, 3, 4],
  size: [2.3, 1, 2.1],
  symmetry: {axis: 'z'},
  controlPoints: [{id: 'x4:y3:z0', position: [1.25, 0.72, -0.91]}],
});
assert.equal(cage.positions.length, 82);
assert.equal(cage.faces.length, 80);
assert.equal(cage.edges.length, 160);
const mirrored = cage.positions[cage.ids.indexOf('x4:y3:z4')];
assert.deepEqual(mirrored, [1.25, 0.72, 0.91]);
const subdividedA = subdivideCage(cage, 2);
const subdividedB = subdivideCage(cage, 2);
assert.equal(subdividedA.triangleCount, 2560);
assert.deepEqual(subdividedA, subdividedB);
assert.throws(() => createSubdivisionCage({segments: [8, 8, 8]}), (error) => error.code === 'foundry.limit.cage_vertices');
assert.throws(() => subdivideCage(cage, 4), (error) => error.code === 'foundry.cage.invalid_levels');

const script = [
  "foundry.validation.productionBudget(" + JSON.stringify(productionBudget('d78461-casting', 1600, 3000)) + ');',
  "foundry.scene.createSubdivisionCage('d78461-cage',{base:'box',segments:[4,3,4],size:[2.3,1,2.1]});",
  "foundry.mesh.subdivide('d78461-cage'," + JSON.stringify(topologySpec({levels: 2, output: 'd78461-casting'}, {maxVertices: 1600, maxTriangles: 3000, maxGrowthRatio: 20})) + ');',
  "foundry.review.modelSheet({cage:'d78461-cage',target:'d78461-casting',views:['front','side','top']});",
  "foundry.validation.assert('model_sheet_fit',{minIou:0.92,maxP95BoundaryErrorRingFraction:0.02,maxLandmarkErrorRingFraction:0.01});",
].join('\n');
const plan = await executeFoundryScript({version: 'foundry-js.v1', text: script, seed: 78461});
await assert.rejects(() => runFoundryKernel({plan, domain: 'hard_surface'}), (error) => error.code === 'foundry.model_sheet.required');
const kernel = await runFoundryKernel({plan, domain: 'hard_surface', modelSheet: {contractVersion: FOUNDRY_MODEL_SHEET_VERSION}});
assert.equal(kernel.report.triangleCount, 2560);
assert.equal(kernel.evidence.cageEvidence['d78461-cage'].positions.length, 82);
assert.equal(kernel.report.hierarchy.some((node) => node.name === 'd78461-cage'), false, 'control cage leaked into the result GLB');
assert.equal(kernel.report.hierarchy.some((node) => node.name === 'd78461-casting'), true);
assert.deepEqual(kernel.evidence.modelSheetReview.views, ['front', 'side', 'top']);

const booleanPlan = await executeFoundryScript({
  version: 'foundry-js.v1',
  text: "foundry.validation.productionBudget(" + JSON.stringify(productionBudget('boolean-result', 512, 512)) + '); foundry.scene.createBox(\'target\',' + JSON.stringify(topologySpec({size: [2, 2, 2]}, {maxVertices: 128, maxTriangles: 32})) + '); foundry.scene.createBox(\'tool\',' + JSON.stringify(topologySpec({size: [1, 1, 3]}, {maxVertices: 128, maxTriangles: 32, purpose: 'mechanical_interface', rationale: 'The tool volume defines the required subtraction interface.'})) + '); foundry.mesh.boolean(\'target\',\'tool\',\'subtract\',\'boolean-result\',' + JSON.stringify(topologySpec({}, {purpose: 'mechanical_interface', rationale: 'The Boolean boundary creates the required test interface.', maxVertices: 512, maxTriangles: 512})) + ');',
});
const booleanResult = await runFoundryKernel({plan: booleanPlan, domain: 'hard_surface'});
assert.equal(booleanResult.report.validation.manifoldClosedComponents, 1, 'basic Foundry boolean is not closed');
assert.equal(booleanResult.report.validation.nonManifoldComponents, 0, 'basic Foundry boolean is non-manifold');

const proofScript = fs.readFileSync(path.join(root, 'docs/evidence/d78461-model-sheet-v2/d78461-bare-casting.foundry.js'), 'utf8');
const proofPlan = await executeFoundryScript({version: 'foundry-js.v1', text: proofScript, seed: 78461});
const proof = await runFoundryKernel({plan: proofPlan, domain: 'hard_surface', modelSheet: {contractVersion: FOUNDRY_MODEL_SHEET_VERSION}});
assert.equal(proof.report.componentCount, 1);
assert.equal(proof.report.validation.manifoldClosedComponents, 1);
assert.equal(proof.report.validation.nonManifoldComponents, 0);
assert.equal(proof.report.validation.degenerateTriangles, 0);
assert.ok(proof.report.triangleCount <= 6000, 'D78461 casting exceeded the proof triangle ceiling');
assert.equal(proof.report.hierarchy[0].name, 'D78461_Bare_Casting');
assert.equal(proof.evidence.cageEvidence['d78461-cage'].positions.length, 96, 'revised D78461 proof must exercise the 96-control cage');

const storage = new FakeStorage();
const owner = 'owner@example.com';
const images = Object.fromEntries(['front', 'side', 'top'].map((name) => [name, artifact(storage, owner, 'd78461-' + name)]));
const sheet = {
  contractVersion: FOUNDRY_MODEL_SHEET_VERSION,
  id: 'd78461-casting-v1',
  units: 'm',
  axisFrame: {forward: [1, 0, 0], up: [0, 1, 0], left: [0, 0, 1]},
  scaleAnchor: {name: 'turret-ring-inside-diameter', meters: 1.7526},
  provenance: [{
    title: 'War Department Technical Manual TM 9-759',
    url: 'https://www.ibiblio.org/hyperwar/USA/ref/TM/pdfs/TM9-759.pdf',
    license: 'public-domain-us-government',
    publisher: 'United States War Department',
    publishedAt: '1944-09',
    processing: 'Curated and traced into calibrated orthographic reference planes.',
  }],
  views: {
    front: view(images.front, 'front'),
    side: view(images.side, 'side'),
    top: view(images.top, 'top'),
  },
};
const resolved = await resolveModelSheet({storage, user: {email: owner}, modelSheet: sheet});
assert.equal(resolved.contractVersion, FOUNDRY_MODEL_SHEET_VERSION);
assert.deepEqual(Object.keys(resolved.views), ['front', 'side', 'top']);
assert.equal(resolved.views.front.image.sha256, images.front.sha256);
const recordFields = modelSheetRecordFields(resolved);
assert.deepEqual(recordFields.modelSheet, {contractVersion: FOUNDRY_MODEL_SHEET_VERSION, id: resolved.id, units: 'm', scaleAnchor: resolved.scaleAnchor});
assert.equal(typeof recordFields.modelSheetJson, 'string');
assert.deepEqual(modelSheetFromRecord(recordFields), resolved);
const rejectDirectNestedArrays = (value, path = 'record') => {
  if (Array.isArray(value)) {
    assert.equal(value.some(Array.isArray), false, path + ' contains a Firestore-invalid directly nested array');
    value.forEach((entry, index) => rejectDirectNestedArrays(entry, path + '[' + index + ']'));
  } else if (value && typeof value === 'object') for (const [key, entry] of Object.entries(value)) rejectDirectNestedArrays(entry, path + '.' + key);
};
rejectDirectNestedArrays(recordFields);
await assert.rejects(
  () => resolveModelSheet({storage, user: {email: owner}, modelSheet: {...sheet, provenance: []}}),
  (error) => error.code === 'foundry.model_sheet.provenance_required',
);
await assert.rejects(
  () => resolveModelSheet({storage, user: {email: owner}, modelSheet: {...sheet, views: {...sheet.views, top: undefined}}}),
  (error) => error.code === 'foundry.model_sheet.view_required',
);
await assert.rejects(
  () => resolveModelSheet({storage, user: {email: owner}, modelSheet: {...sheet, axisFrame: {...sheet.axisFrame, forward: [2, 0, 0]}}}),
  (error) => error.code === 'foundry.model_sheet.invalid_axis',
);
await assert.rejects(
  () => resolveModelSheet({storage, user: {email: owner}, modelSheet: {...sheet, axisFrame: {...sheet.axisFrame, left: [0, 0, -1]}}}),
  (error) => error.code === 'foundry.model_sheet.axis_handedness',
);
const badMediaImage = artifact(storage, owner, 'd78461-bad-media', 'image/jpeg');
await assert.rejects(
  () => resolveModelSheet({storage, user: {email: owner}, modelSheet: {...sheet, views: {...sheet.views, top: view(badMediaImage, 'top')}}}),
  (error) => error.code === 'foundry.reference.invalid_media_type',
);

function rectangleMask(left, top, right, bottom) {
  const mask = new Uint8Array(REVIEW_WIDTH * REVIEW_HEIGHT);
  for (let y = top; y < bottom; y++) for (let x = left; x < right; x++) mask[y * REVIEW_WIDTH + x] = 1;
  return mask;
}
const contour = [[100, 100], [539, 100], [539, 539], [100, 539]];
const targetMask = rectangleMask(100, 100, 540, 540);
const thresholds = {minIou: 0.92, maxP95BoundaryErrorRingFraction: 0.02, maxLandmarkErrorRingFraction: 0.01};
const exact = evaluateRegisteredFit({targetMask, surfaceMask: targetMask, contourPx: contour, ringPixels: 350.52, landmarkErrorsPx: [0, 0, 0], thresholds});
assert.equal(exact.pass, true);
assert.equal(exact.silhouetteIou, 1);
const aperture = [[200, 200], [220, 200], [220, 220], [200, 220]];
const apertureExact = evaluateApertureFit({aperturesPx: [aperture], edgePixels: aperture, ringPixels: 350.52, maxBoundaryErrorRingFraction: 0.02});
assert.equal(apertureExact.aperturePass, true);
const apertureShifted = evaluateApertureFit({aperturesPx: [aperture], edgePixels: aperture.map(([x, y]) => [x + 40, y]), ringPixels: 350.52, maxBoundaryErrorRingFraction: 0.02});
assert.equal(apertureShifted.aperturePass, false);

const perView = {};
for (const name of ['front', 'side', 'top']) {
  const perturbed = evaluateRegisteredFit({targetMask, surfaceMask: rectangleMask(180, 100, 620, 540), contourPx: contour, ringPixels: 350.52, landmarkErrorsPx: [0, 0, 0], thresholds});
  assert.equal(perturbed.pass, false, name + ' perturbation incorrectly passed');
  perView[name] = perturbed.silhouetteIou;
}

console.log(JSON.stringify({
  ok: true,
  cage: {controlVertices: cage.positions.length, quads: cage.faces.length, edges: cage.edges.length, triangles: subdividedA.triangleCount},
  d78461: {triangles: proof.report.triangleCount, components: proof.report.componentCount, manifoldClosedComponents: proof.report.validation.manifoldClosedComponents},
  registeredViews: Object.keys(resolved.views),
  exactIou: exact.silhouetteIou,
  perturbedIouByView: perView,
}, null, 2));
