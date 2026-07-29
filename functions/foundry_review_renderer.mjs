import fs from 'node:fs/promises';
import http from 'node:http';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import puppeteer from 'puppeteer-core';
import chromium from '@sparticuz/chromium';
import pngjs from 'pngjs';
import {subdivisionCageDigest} from './foundry_model_sheet.mjs';

const {PNG} = pngjs;
export const REVIEW_WIDTH = 640;
export const REVIEW_HEIGHT = 640;
export const REVIEW_VIEWS = Object.freeze(['front', 'back', 'left', 'right', 'top', 'perspective']);
const here = path.dirname(fileURLToPath(import.meta.url));
const threeRoot = path.join(here, 'node_modules', 'three');

function fail(code, message, details = {}) {
  const error = new Error(message);
  error.code = code;
  error.status = 500;
  error.details = details;
  return error;
}
function contentType(filePath) {
  if (filePath.endsWith('.js')) return 'text/javascript; charset=utf-8';
  if (filePath.endsWith('.glb')) return 'model/gltf-binary';
  if (filePath.endsWith('.html')) return 'text/html; charset=utf-8';
  return 'application/octet-stream';
}
function html() {
  return `<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;background:#171a18;overflow:hidden}canvas{display:block;width:${REVIEW_WIDTH}px;height:${REVIEW_HEIGHT}px}</style><script type="importmap">{"imports":{"three":"/three/build/three.module.js"}}</script></head><body><script type="module">
import * as THREE from 'three';
import {GLTFLoader} from '/three/examples/jsm/loaders/GLTFLoader.js';
const renderer = new THREE.WebGLRenderer({antialias:true,alpha:false,preserveDrawingBuffer:true,powerPreference:'high-performance'});
renderer.setPixelRatio(1); renderer.setSize(${REVIEW_WIDTH}, ${REVIEW_HEIGHT}, false); renderer.outputColorSpace = THREE.SRGBColorSpace; renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05; document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene(); scene.background = new THREE.Color(0x171a18);
scene.add(new THREE.HemisphereLight(0xf6f3e8, 0x3d4745, 2.0));
const key = new THREE.DirectionalLight(0xffffff, 3.2); key.position.set(4,7,6); scene.add(key);
const fill = new THREE.DirectionalLight(0x9fd3ff, 1.1); fill.position.set(-5,3,-4); scene.add(fill);
const gltf = await new GLTFLoader().loadAsync('/model.glb'); const model = gltf.scene; scene.add(model);
const box = new THREE.Box3().setFromObject(model); const center = box.getCenter(new THREE.Vector3()); const size = box.getSize(new THREE.Vector3()); const radius = Math.max(size.x,size.y,size.z,0.1); const camera = new THREE.PerspectiveCamera(36,1,Math.max(radius/1000,0.001),radius*100);
const skeleton = new THREE.SkeletonHelper(model); skeleton.visible = false; skeleton.material.depthTest = false; skeleton.material.transparent = true; skeleton.material.opacity = 0.95; skeleton.material.color.setHex(0x65d9ff); scene.add(skeleton);
const offsets = {front:[0,0.18,1],back:[0,0.18,-1],left:[-1,0.18,0],right:[1,0.18,0],top:[0.001,1,0.001],perspective:[0.9,0.6,1.05]};
window.renderFoundryView = (name, overlay=false) => { const direction = new THREE.Vector3(...(offsets[name]||offsets.perspective)).normalize(); camera.position.copy(center).addScaledVector(direction, radius*2.8); camera.up.set(0,1,0); if(name==='top') camera.up.set(0,0,-1); camera.lookAt(center); camera.updateProjectionMatrix(); skeleton.visible=overlay; renderer.render(scene,camera); return {name,overlay,bones:skeleton.bones.length,bounds:{min:box.min.toArray(),max:box.max.toArray()}}; };
let registeredCage = null;
window.renderFoundryRegistered = (config, mode, cage) => {
  if (registeredCage) { scene.remove(registeredCage); registeredCage.traverse((object) => { if (object.geometry) object.geometry.dispose(); if (object.material) object.material.dispose(); }); registeredCage = null; }
  skeleton.visible = false;
  scene.background = new THREE.Color(0x000000);
  model.traverse((object) => { if (object.isMesh) object.visible = mode === 'surface'; });
  if (mode === 'surface' && config.target) {
    const target = model.getObjectByName(config.target);
    if (!target) throw new Error('foundry.review.target_not_found:' + config.target);
    model.traverse((object) => {
      if (!object.isMesh) return;
      let cursor = object, belongs = false;
      while (cursor) { if (cursor === target) belongs = true; cursor = cursor.parent; }
      object.visible = belongs;
    });
  }
  if (mode === 'cage') {
    const values = [];
    for (const edge of cage.edges) for (const index of edge) values.push(...cage.positions[index]);
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(values, 3));
    registeredCage = new THREE.LineSegments(geometry, new THREE.LineBasicMaterial({color: 0x00ffff}));
    scene.add(registeredCage);
  } else if (mode === 'edges') {
    const target = model.getObjectByName(config.target);
    if (!target) throw new Error('foundry.review.target_not_found:' + config.target);
    registeredCage = new THREE.Group();
    target.updateWorldMatrix(true, true);
    target.traverse((object) => {
      if (!object.isMesh) return;
      const line = new THREE.LineSegments(new THREE.EdgesGeometry(object.geometry, 12), new THREE.LineBasicMaterial({color: 0xffffff}));
      line.matrix.copy(object.matrixWorld); line.matrixAutoUpdate = false; registeredCage.add(line);
    });
    scene.add(registeredCage);
  }
  const ppm = Number(config.pixelsPerMeter);
  const registeredCamera = new THREE.OrthographicCamera(
    -Number(config.originPx[0]) / ppm,
    (640 - Number(config.originPx[0])) / ppm,
    Number(config.originPx[1]) / ppm,
    -(640 - Number(config.originPx[1])) / ppm,
    0.01,
    100,
  );
  const origin = new THREE.Vector3(...config.originWorld);
  const direction = new THREE.Vector3(...config.camera.direction);
  registeredCamera.position.copy(origin).addScaledVector(direction, 10);
  registeredCamera.up.set(...config.camera.up);
  registeredCamera.lookAt(origin);
  registeredCamera.updateProjectionMatrix();
  renderer.toneMapping = THREE.NoToneMapping;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  scene.overrideMaterial = mode === 'surface' ? new THREE.MeshBasicMaterial({color: 0xffffff, side: THREE.FrontSide}) : null;
  renderer.render(scene, registeredCamera);
  if (scene.overrideMaterial) { scene.overrideMaterial.dispose(); scene.overrideMaterial = null; }
  return {mode, target: config.target || null, camera: {left: registeredCamera.left, right: registeredCamera.right, top: registeredCamera.top, bottom: registeredCamera.bottom, position: registeredCamera.position.toArray(), up: registeredCamera.up.toArray()}};
};
window.renderFoundryView('perspective', false); window.__FOUNDRY_REVIEW_READY = true;
</script></body></html>`;
}

async function createLoopbackServer(glbPath) {
  const server = http.createServer(async (req, res) => {
    try {
      const pathname = new URL(req.url || '/', 'http://127.0.0.1').pathname;
      let target = '';
      if (pathname === '/' || pathname === '/index.html') {
        const body = Buffer.from(html());
        res.writeHead(200, {'Content-Type': 'text/html; charset=utf-8', 'Content-Length': body.length, 'Cache-Control': 'no-store'});
        res.end(body);
        return;
      }
      if (pathname === '/model.glb') target = glbPath;
      else if (pathname.startsWith('/three/')) {
        target = path.join(threeRoot, pathname.slice('/three/'.length));
        if (!target.startsWith(threeRoot + path.sep)) throw fail('foundry.review.path_escape', 'Review module path escaped package root.');
      } else {
        res.writeHead(404);
        res.end();
        return;
      }
      const bytes = await fs.readFile(target);
      res.writeHead(200, {'Content-Type': contentType(target), 'Content-Length': bytes.length, 'Cache-Control': 'no-store', 'Access-Control-Allow-Origin': '*'});
      res.end(bytes);
    } catch (error) {
      res.writeHead(500, {'Content-Type':'text/plain'});
      res.end(String(error.message || error).slice(0,500));
    }
  });
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
  return {server, url: 'http://127.0.0.1:' + server.address().port + '/index.html'};
}

export function assertReviewImageNonBlank(bytes, label = 'review image') {
  const image = PNG.sync.read(bytes);
  if (image.width !== REVIEW_WIDTH || image.height !== REVIEW_HEIGHT) throw fail('foundry.review.image_dimensions', label + ' has unexpected dimensions.', {width: image.width, height: image.height});
  const background = [23, 26, 24];
  let changed = 0;
  const colors = new Set();
  for (let offset = 0; offset < image.data.length; offset += 16) {
    const r = image.data[offset], g = image.data[offset + 1], b = image.data[offset + 2], a = image.data[offset + 3];
    colors.add((r >> 3) + ':' + (g >> 3) + ':' + (b >> 3));
    if (a > 0 && Math.abs(r - background[0]) + Math.abs(g - background[1]) + Math.abs(b - background[2]) > 24) changed += 1;
  }
  if (changed < 1000 || colors.size < 8) throw fail('foundry.review.blank_canvas', label + ' is blank or lacks visible model pixels.', {changedSamples: changed, colorBuckets: colors.size});
  return {changedSamples: changed, colorBuckets: colors.size};
}

export function buildContactSheet(viewBuffers, viewOrder) {
  const columns = 3;
  const rows = Math.ceil(viewOrder.length / columns);
  const sheet = new PNG({width: REVIEW_WIDTH * columns, height: REVIEW_HEIGHT * rows});
  for (let index = 0; index < viewOrder.length; index++) {
    const source = PNG.sync.read(viewBuffers[viewOrder[index]]);
    const x = (index % columns) * REVIEW_WIDTH;
    const y = Math.floor(index / columns) * REVIEW_HEIGHT;
    PNG.bitblt(source, sheet, 0, 0, source.width, source.height, x, y);
  }
  return PNG.sync.write(sheet, {colorType: 6});
}

export async function renderFixedViews({glbPath, views = REVIEW_VIEWS, timeoutMs = 120000}) {
  const requested = [...new Set(views.map(String))];
  if (!requested.length || requested.some((view) => !REVIEW_VIEWS.includes(view))) throw fail('foundry.review.invalid_views', 'Unsupported fixed-view request.', {views: requested, supported: REVIEW_VIEWS});
  const {server, url} = await createLoopbackServer(glbPath);
  let browser = null;
  try {
    browser = await puppeteer.launch({args: [...chromium.args, '--disable-dev-shm-usage', '--disable-background-networking'], defaultViewport: {width: REVIEW_WIDTH, height: REVIEW_HEIGHT, deviceScaleFactor: 1}, executablePath: await chromium.executablePath(), headless: chromium.headless});
    const page = await browser.newPage();
    await page.setRequestInterception(true);
    page.on('request', (request) => {
      const target = new URL(request.url());
      if (target.hostname === '127.0.0.1') request.continue();
      else request.abort('blockedbyclient');
    });
    await page.goto(url, {waitUntil: 'networkidle0', timeout: timeoutMs});
    await page.waitForFunction(() => window.__FOUNDRY_REVIEW_READY === true, {timeout: timeoutMs});
    const canvas = await page.$('canvas');
    if (!canvas) throw fail('foundry.review.canvas_missing', 'Three.js review canvas was not created.');
    const outputs = {};
    const diagnostics = {};
    for (const view of requested) {
      diagnostics[view] = await page.evaluate((name) => window.renderFoundryView(name, false), view);
      outputs[view] = Buffer.from(await canvas.screenshot({type: 'png'}));
      diagnostics[view].pixels = assertReviewImageNonBlank(outputs[view], 'fixed-' + view + '.png');
    }
    const boneCount = Number(diagnostics[requested[0]]?.bones || 0);
    let skeletalOverlay = null;
    if (boneCount > 0) {
      await page.evaluate(() => window.renderFoundryView('perspective', true));
      skeletalOverlay = Buffer.from(await canvas.screenshot({type: 'png'}));
      assertReviewImageNonBlank(skeletalOverlay, 'skeletal-overlay.png');
    }
    return {views: outputs, contactSheet: buildContactSheet(outputs, requested), skeletalOverlay, diagnostics};
  } catch (error) {
    if (error.code) throw error;
    throw fail('foundry.review.render_failed', 'Three.js fixed-view rendering failed: ' + String(error.message || error).slice(0, 1000));
  } finally {
    if (browser) await browser.close().catch(() => {});
    await new Promise((resolve) => server.close(resolve));
  }
}


function dot3(a, b) {
  return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
}
function polygonMask(points) {
  const mask = new Uint8Array(REVIEW_WIDTH * REVIEW_HEIGHT);
  for (let y = 0; y < REVIEW_HEIGHT; y++) {
    for (let x = 0; x < REVIEW_WIDTH; x++) {
      let inside = false;
      for (let i = 0, j = points.length - 1; i < points.length; j = i++) {
        const xi = points[i][0], yi = points[i][1], xj = points[j][0], yj = points[j][1];
        if (((yi > y + 0.5) !== (yj > y + 0.5)) && (x + 0.5 < (xj - xi) * (y + 0.5 - yi) / ((yj - yi) || 1e-9) + xi)) inside = !inside;
      }
      if (inside) mask[y * REVIEW_WIDTH + x] = 1;
    }
  }
  return mask;
}
function imageMask(bytes, predicate) {
  const image = PNG.sync.read(bytes);
  if (image.width !== REVIEW_WIDTH || image.height !== REVIEW_HEIGHT) throw fail('foundry.review.image_dimensions', 'Registered render has unexpected dimensions.', {width: image.width, height: image.height});
  const mask = new Uint8Array(REVIEW_WIDTH * REVIEW_HEIGHT);
  let count = 0;
  for (let index = 0; index < mask.length; index++) {
    const offset = index * 4;
    if (predicate(image.data[offset], image.data[offset + 1], image.data[offset + 2], image.data[offset + 3])) {
      mask[index] = 1;
      count++;
    }
  }
  return {mask, count};
}
function boundaryPixels(mask) {
  const points = [];
  for (let y = 1; y < REVIEW_HEIGHT - 1; y++) for (let x = 1; x < REVIEW_WIDTH - 1; x++) {
    const index = y * REVIEW_WIDTH + x;
    if (!mask[index]) continue;
    if (!mask[index - 1] || !mask[index + 1] || !mask[index - REVIEW_WIDTH] || !mask[index + REVIEW_WIDTH]) points.push([x, y]);
  }
  return points;
}
function percentile(values, fraction) {
  if (!values.length) return Infinity;
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.min(sorted.length - 1, Math.max(0, Math.ceil(sorted.length * fraction) - 1))];
}
function nearestDistance(point, candidates) {
  let best = Infinity;
  for (const candidate of candidates) {
    const dx = point[0] - candidate[0], dy = point[1] - candidate[1];
    best = Math.min(best, Math.hypot(dx, dy));
  }
  return best;
}
function maskFit(target, surface, contour) {
  let intersection = 0, union = 0;
  for (let index = 0; index < target.length; index++) {
    if (target[index] && surface[index]) intersection++;
    if (target[index] || surface[index]) union++;
  }
  const boundary = boundaryPixels(surface), contourBoundaryErrorsPx = contour.map((point) => nearestDistance(point, boundary));
  return {
    silhouetteIou: union ? intersection / union : 0,
    p95BoundaryErrorPx: percentile(contourBoundaryErrorsPx, 0.95),
    contourBoundaryErrorsPx,
    targetPixels: target.reduce((sum, value) => sum + value, 0),
    surfacePixels: surface.reduce((sum, value) => sum + value, 0),
    intersectionPixels: intersection,
    unionPixels: union,
  };
}
function blendMask(reference, mask, color, alpha = 0.72) {
  const source = PNG.sync.read(reference);
  const output = new PNG({width: source.width, height: source.height});
  source.data.copy(output.data);
  for (let index = 0; index < mask.length; index++) {
    if (!mask[index]) continue;
    const offset = index * 4;
    output.data[offset] = Math.round(output.data[offset] * (1 - alpha) + color[0] * alpha);
    output.data[offset + 1] = Math.round(output.data[offset + 1] * (1 - alpha) + color[1] * alpha);
    output.data[offset + 2] = Math.round(output.data[offset + 2] * (1 - alpha) + color[2] * alpha);
    output.data[offset + 3] = 255;
  }
  return output;
}
function drawLine(image, a, b, color) {
  let x0 = Math.round(a[0]), y0 = Math.round(a[1]), x1 = Math.round(b[0]), y1 = Math.round(b[1]);
  const dx = Math.abs(x1 - x0), sx = x0 < x1 ? 1 : -1, dy = -Math.abs(y1 - y0), sy = y0 < y1 ? 1 : -1;
  let error = dx + dy;
  for (;;) {
    if (x0 >= 0 && x0 < image.width && y0 >= 0 && y0 < image.height) {
      for (let oy = -1; oy <= 1; oy++) for (let ox = -1; ox <= 1; ox++) {
        const x = x0 + ox, y = y0 + oy;
        if (x < 0 || x >= image.width || y < 0 || y >= image.height) continue;
        const offset = (y * image.width + x) * 4;
        image.data[offset] = color[0]; image.data[offset + 1] = color[1]; image.data[offset + 2] = color[2]; image.data[offset + 3] = 255;
      }
    }
    if (x0 === x1 && y0 === y1) break;
    const twice = 2 * error;
    if (twice >= dy) { error += dy; x0 += sx; }
    if (twice <= dx) { error += dx; y0 += sy; }
  }
}
function contourOverlay(reference, mask, edgeMask, contour, apertures, color) {
  let output = blendMask(reference, mask, color, 0.48);
  output = blendMask(PNG.sync.write(output, {colorType: 6}), edgeMask, [255, 112, 48], 0.86);
  for (let index = 0; index < contour.length; index++) drawLine(output, contour[index], contour[(index + 1) % contour.length], [255, 213, 64]);
  for (const aperture of apertures) for (let index = 0; index < aperture.length; index++) drawLine(output, aperture[index], aperture[(index + 1) % aperture.length], [255, 132, 48]);
  return PNG.sync.write(output, {colorType: 6});
}
function differenceImage(reference, target, surface) {
  const source = PNG.sync.read(reference);
  const output = new PNG({width: source.width, height: source.height});
  for (let index = 0; index < target.length; index++) {
    const offset = index * 4;
    const base = Math.round((source.data[offset] + source.data[offset + 1] + source.data[offset + 2]) / 9);
    let color = [base, base, base];
    if (target[index] && surface[index]) color = [65, 200, 110];
    else if (target[index]) color = [255, 174, 45];
    else if (surface[index]) color = [218, 70, 205];
    output.data[offset] = color[0]; output.data[offset + 1] = color[1]; output.data[offset + 2] = color[2]; output.data[offset + 3] = 255;
  }
  return PNG.sync.write(output, {colorType: 6});
}
function projectCagePoint(point, view) {
  const relative = point.map((value, index) => value - view.originWorld[index]);
  return [
    view.originPx[0] + dot3(relative, view.camera.horizontal) * view.pixelsPerMeter,
    view.originPx[1] - dot3(relative, view.camera.up) * view.pixelsPerMeter,
  ];
}
function registeredMatrix(view) {
  const h = view.camera.horizontal, v = view.camera.up, o = view.originWorld, ppm = view.pixelsPerMeter;
  return [
    [h[0] * ppm, h[1] * ppm, h[2] * ppm, view.originPx[0] - dot3(o, h) * ppm],
    [-v[0] * ppm, -v[1] * ppm, -v[2] * ppm, view.originPx[1] + dot3(o, v) * ppm],
    [0, 0, 0, 1],
  ];
}

export function evaluateRegisteredFit({targetMask, surfaceMask, contourPx, ringPixels, landmarkErrorsPx, thresholds}) {
  if (!(targetMask instanceof Uint8Array) || !(surfaceMask instanceof Uint8Array) || targetMask.length !== REVIEW_WIDTH * REVIEW_HEIGHT || surfaceMask.length !== targetMask.length) {
    throw fail('foundry.review.invalid_registered_mask', 'Registered fit masks must be 640x640 binary arrays.');
  }
  const metrics = maskFit(targetMask, surfaceMask, contourPx);
  const p95BoundaryErrorRingFraction = metrics.p95BoundaryErrorPx / ringPixels;
  const maxLandmarkErrorRingFraction = Math.max(0, ...landmarkErrorsPx.map((value) => Number(value) / ringPixels));
  const pass = metrics.silhouetteIou >= thresholds.minIou
    && p95BoundaryErrorRingFraction <= thresholds.maxP95BoundaryErrorRingFraction
    && maxLandmarkErrorRingFraction <= thresholds.maxLandmarkErrorRingFraction;
  return {...metrics, ringPixels, p95BoundaryErrorRingFraction, maxLandmarkErrorRingFraction, pass};
}

export function evaluateApertureFit({aperturesPx = [], edgePixels = [], ringPixels, maxBoundaryErrorRingFraction}) {
  const apertureBoundaryErrorsPx = aperturesPx.flatMap((aperture) => aperture.map((point) => nearestDistance(point, edgePixels)));
  const apertureP95BoundaryErrorPx = apertureBoundaryErrorsPx.length ? percentile(apertureBoundaryErrorsPx, 0.95) : 0;
  const apertureP95BoundaryErrorRingFraction = apertureP95BoundaryErrorPx / ringPixels;
  return {
    apertureBoundaryErrorsPx,
    apertureP95BoundaryErrorPx,
    apertureP95BoundaryErrorRingFraction,
    aperturePass: apertureP95BoundaryErrorRingFraction <= maxBoundaryErrorRingFraction,
  };
}

export async function renderModelSheetEvidence({glbPath, modelSheet, review, cage, thresholds, timeoutMs = 120000}) {
  if (!modelSheet || !review || !cage) throw fail('foundry.review.model_sheet_missing', 'Registered model-sheet rendering requires the sheet, cage, and review target.');
  const viewNames = Array.isArray(review.views) ? [...review.views] : Object.keys(modelSheet.views || {});
  if (viewNames.length < 2 || !viewNames.includes('front') || !viewNames.includes('side')) throw fail('foundry.review.invalid_model_sheet_views', 'Registered evidence requires declared front and side views.', {views: viewNames});
  const sharedCageSha256 = subdivisionCageDigest(cage);
  const references = {};
  for (const viewName of viewNames) {
    const bytes = await fs.readFile(modelSheet.views[viewName].imagePath);
    const image = PNG.sync.read(bytes);
    if (image.width !== REVIEW_WIDTH || image.height !== REVIEW_HEIGHT) throw fail('foundry.model_sheet.image_dimensions', viewName + ' reference must decode to 640x640.', {width: image.width, height: image.height});
    references[viewName] = bytes;
  }
  const {server, url} = await createLoopbackServer(glbPath);
  let browser = null;
  try {
    browser = await puppeteer.launch({args: [...chromium.args, '--disable-dev-shm-usage', '--disable-background-networking'], defaultViewport: {width: REVIEW_WIDTH, height: REVIEW_HEIGHT, deviceScaleFactor: 1}, executablePath: await chromium.executablePath(), headless: chromium.headless});
    const page = await browser.newPage();
    await page.setRequestInterception(true);
    page.on('request', (request) => {
      const target = new URL(request.url());
      if (target.hostname === '127.0.0.1') request.continue();
      else request.abort('blockedbyclient');
    });
    await page.goto(url, {waitUntil: 'networkidle0', timeout: timeoutMs});
    await page.waitForFunction(() => window.__FOUNDRY_REVIEW_READY === true, {timeout: timeoutMs});
    const canvas = await page.$('canvas');
    if (!canvas) throw fail('foundry.review.canvas_missing', 'Three.js registered-review canvas was not created.');
    const artifacts = {}, viewReports = {}, registrations = {};
    for (const viewName of viewNames) {
      const view = modelSheet.views[viewName];
      const config = {originPx: view.originPx, originWorld: view.originWorld, pixelsPerMeter: view.pixelsPerMeter, camera: view.camera, target: review.target};
      const cageCamera = await page.evaluate((payload) => window.renderFoundryRegistered(payload.config, 'cage', payload.cage), {config, cage});
      const cageBytes = Buffer.from(await canvas.screenshot({type: 'png'}));
      const cageMask = imageMask(cageBytes, (r, g, b, a) => a > 0 && g + b > 120 && b > r * 1.2);
      if (cageMask.count < 100) throw fail('foundry.review.blank_cage_overlay', viewName + ' cage overlay has too few registered pixels.', {pixels: cageMask.count});
      const surfaceCamera = await page.evaluate((payload) => window.renderFoundryRegistered(payload.config, 'surface', payload.cage), {config, cage});
      const surfaceBytes = Buffer.from(await canvas.screenshot({type: 'png'}));
      const surfaceMask = imageMask(surfaceBytes, (r, g, b, a) => a > 0 && r + g + b > 180);
      if (surfaceMask.count < 1000) throw fail('foundry.review.blank_surface_overlay', viewName + ' surface overlay has too few registered pixels.', {pixels: surfaceMask.count});
      const edgeCamera = await page.evaluate((payload) => window.renderFoundryRegistered(payload.config, 'edges', payload.cage), {config, cage});
      const edgeBytes = Buffer.from(await canvas.screenshot({type: 'png'}));
      const edgeMask = imageMask(edgeBytes, (r, g, b, a) => a > 0 && r + g + b > 180);
      if (edgeMask.count < 100) throw fail('foundry.review.blank_edge_overlay', viewName + ' surface-edge overlay has too few registered pixels.', {pixels: edgeMask.count});
      const targetMask = polygonMask(view.contourPx);
      const ringPixels = view.pixelsPerMeter * modelSheet.scaleAnchor.meters;
      const cageById = new Map(cage.ids.map((id, index) => [id, cage.positions[index]]));
      const landmarkErrors = view.landmarks.map((landmark) => {
        const point = cageById.get(landmark.cagePointId);
        if (!point) throw fail('foundry.review.landmark_cage_point_missing', 'Registered landmark references an absent cage point.', {view: viewName, cagePointId: landmark.cagePointId});
        const projected = projectCagePoint(point, view);
        const errorPx = Math.hypot(projected[0] - landmark.pixel[0], projected[1] - landmark.pixel[1]);
        return {name: landmark.name, cagePointId: landmark.cagePointId, expectedPixel: landmark.pixel, projectedPixel: projected, errorPx, errorRingFraction: errorPx / ringPixels};
      });
      const evaluated = evaluateRegisteredFit({targetMask, surfaceMask: surfaceMask.mask, contourPx: view.contourPx, ringPixels, landmarkErrorsPx: landmarkErrors.map((entry) => entry.errorPx), thresholds});
      const apertureFit = evaluateApertureFit({aperturesPx: view.aperturesPx || [], edgePixels: boundaryPixels(edgeMask.mask), ringPixels, maxBoundaryErrorRingFraction: thresholds.maxP95BoundaryErrorRingFraction});
      viewReports[viewName] = {...evaluated, landmarkErrors, ...apertureFit, pass: evaluated.pass && apertureFit.aperturePass, thresholds};
      registrations[viewName] = {image: {artifactId: view.image.artifactId, sha256: view.image.sha256, byteLength: view.image.byteLength, mediaType: view.image.mediaType, filename: view.image.filename}, width: view.width, height: view.height, originPx: view.originPx, originWorld: view.originWorld, pixelsPerMeter: view.pixelsPerMeter, camera: view.camera, worldToPixel: registeredMatrix(view), cageCamera, surfaceCamera, edgeCamera};
      artifacts['reference-' + viewName + '.png'] = references[viewName];
      artifacts['overlay-' + viewName + '-cage.png'] = PNG.sync.write(blendMask(references[viewName], cageMask.mask, [0, 235, 255], 0.82), {colorType: 6});
      artifacts['overlay-' + viewName + '-surface.png'] = contourOverlay(references[viewName], surfaceMask.mask, edgeMask.mask, view.contourPx, view.aperturesPx || [], [65, 225, 120]);
      artifacts['difference-' + viewName + '.png'] = differenceImage(references[viewName], targetMask, surfaceMask.mask);
    }
    const contactViews = Object.fromEntries(viewNames.map((viewName) => [viewName, artifacts['overlay-' + viewName + '-surface.png']]));
    artifacts['model-sheet-contact-sheet.png'] = buildContactSheet(contactViews, viewNames);
    const overallPass = viewNames.every((viewName) => viewReports[viewName].pass);
    const passRule = viewNames.join('_and_');
    const fitReport = {contractVersion: 'home-center.foundry-model-sheet-fit.v1', modelSheetId: modelSheet.id, viewOrder: viewNames, sharedCageSha256, scaleAnchor: modelSheet.scaleAnchor, thresholds, views: viewReports, overallPass, passRule};
    const registration = {contractVersion: 'home-center.foundry-model-sheet-registration.v1', modelSheetId: modelSheet.id, viewOrder: viewNames, sharedCageSha256, axisFrame: modelSheet.axisFrame, authority: modelSheet.authority || null, provenance: modelSheet.provenance, views: registrations};
    return {artifacts, fitReport, registration};
  } catch (error) {
    if (error.code) throw error;
    throw fail('foundry.review.registered_render_failed', 'Three.js registered model-sheet rendering failed: ' + String(error.message || error).slice(0, 1000));
  } finally {
    if (browser) await browser.close().catch(() => {});
    await new Promise((resolve) => server.close(resolve));
  }
}
