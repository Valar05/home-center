import fs from 'node:fs/promises';
import http from 'node:http';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import puppeteer from 'puppeteer-core';
import chromium from '@sparticuz/chromium';
import pngjs from 'pngjs';

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
