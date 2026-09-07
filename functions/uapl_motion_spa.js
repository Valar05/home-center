const {createHash} = require('node:crypto');
const {
  parseUapl,
  canonicalUapl,
  uaplHash,
  parseUat,
  renderAsciiPose,
  renderAsciiContactSheet,
} = require('./uapl_pose_language');

function fail(code, message) {
  const error = new Error(message);
  error.code = code;
  throw error;
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function canonicalUat(uat) {
  const lines = ['UAT 1', `SOURCE ${uat.source}`, `FPS ${uat.fps}`];
  for (const step of uat.steps) lines.push(`STEP ${step.pose} ${step.ticks}`);
  lines.push('ENDUAT');
  return `${lines.join('\n')}\n`;
}

function assertGifDataUri(value) {
  const match = /^data:image\/gif;base64,([A-Za-z0-9+/=]+)$/.exec(String(value || ''));
  if (!match) fail('UAPL_SPA_GIF', 'gifDataUri must be an inline data:image/gif;base64 URI');
  let bytes;
  try {
    bytes = Buffer.from(match[1], 'base64');
  } catch (_) {
    fail('UAPL_SPA_GIF', 'gifDataUri is not valid base64');
  }
  if (bytes.length < 10) fail('UAPL_SPA_GIF', 'gifDataUri is too small to be a GIF');
  const header = bytes.subarray(0, 6).toString('ascii');
  if (header !== 'GIF87a' && header !== 'GIF89a') fail('UAPL_SPA_GIF', 'gifDataUri does not contain GIF bytes');
  return {
    byteLength: bytes.length,
    sha256: createHash('sha256').update(bytes).digest('hex'),
  };
}

function buildMotionSpa({uaplText, uatText, gifDataUri, title = ''}) {
  const program = parseUapl(uaplText);
  const sourceText = canonicalUapl(program);
  const sourceSha256 = uaplHash(program);
  const uat = parseUat(uatText, program);
  const timingText = canonicalUat(uat);
  const gif = assertGifDataUri(gifDataUri);
  const displayTitle = title || program.name.replace(/[_-]+/g, ' ');
  const contactSheet = renderAsciiContactSheet(program);
  const poseCards = program.poses.map((pose) => ({
    name: pose.name,
    ascii: renderAsciiPose(program, pose),
  }));
  const timingRows = uat.steps.map((step, index) => ({
    index: index + 1,
    pose: step.pose,
    ticks: step.ticks,
    milliseconds: Math.round((step.ticks * 100000) / uat.fps) / 100,
  }));

  const poseHtml = poseCards.map((pose) => `
        <article class="pose-card" data-pose="${escapeHtml(pose.name)}">
          <h2>${escapeHtml(pose.name)}</h2>
          <pre class="ascii pose-ascii" tabindex="0">${escapeHtml(pose.ascii)}</pre>
        </article>`).join('');

  const timingHtml = timingRows.map((row) => `
              <tr><td>${row.index}</td><th scope="row">${escapeHtml(row.pose)}</th><td>${row.ticks}</td><td>${row.milliseconds}</td></tr>`).join('');

  const runtimeJson = JSON.stringify({
    version: 'uapl.motion-spa.v1',
    motion: program.name,
    sourceSha256,
    fps: uat.fps,
    poses: poseCards,
    steps: uat.steps,
    gifSha256: gif.sha256,
    gifBytes: gif.byteLength,
  }).replace(/</g, '\\u003c');

  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover,user-scalable=no">
<meta name="color-scheme" content="dark">
<title>${escapeHtml(displayTitle)} — UAPL Motion Sheet</title>
<style>
:root{color-scheme:dark;--bg:#0b0b0c;--panel:#171719;--panel2:#101012;--line:#393b40;--text:#f4f4f4;--muted:#b9bac0;--ascii-size:16px}
*{box-sizing:border-box}
html,body{margin:0;width:100%;height:100%;overflow:hidden;background:var(--bg);color:var(--text);font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;overscroll-behavior:none}
#app{height:100dvh;display:grid;grid-template-rows:auto auto minmax(0,1fr);gap:8px;padding:max(8px,env(safe-area-inset-top)) 8px max(8px,env(safe-area-inset-bottom));padding-left:max(8px,env(safe-area-inset-left));padding-right:max(8px,env(safe-area-inset-right))}
.row{display:flex;gap:8px;align-items:center;overflow-x:auto;scrollbar-width:none}.row::-webkit-scrollbar{display:none}
button{appearance:none;min-height:44px;padding:8px 12px;border-radius:13px;border:1px solid var(--line);background:var(--panel);color:var(--text);font-size:16px;font-weight:750;white-space:nowrap}
button[aria-pressed="true"]{background:#f3f3f3;color:#111;border-color:#f3f3f3}button:focus-visible{outline:3px solid #fff;outline-offset:2px}
.title{font-size:15px;font-weight:800;white-space:nowrap}.status{margin-left:auto;min-width:0;color:var(--muted);font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.workspace{min-height:0;position:relative;overflow:hidden;background:var(--panel2);border:1px solid var(--line);border-radius:18px}
.panel{display:none;height:100%;overflow:auto;padding:12px;overscroll-behavior:contain}.panel.active{display:block}
.pose-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,260px),1fr));gap:10px;align-items:start}.pose-card{min-width:0;border:1px solid var(--line);border-radius:14px;background:#0d0d0f;overflow:hidden}.pose-card h2{margin:0;padding:8px 10px;border-bottom:1px solid var(--line);font-size:14px;text-transform:uppercase;letter-spacing:.08em}
.ascii{margin:0;padding:12px;font:var(--ascii-size)/1.05 ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono","Courier New",monospace;font-variant-ligatures:none;white-space:pre;word-break:normal;overflow:auto;touch-action:pan-x pan-y;tab-size:2;color:#f7fbff;background:#0a0b0c;user-select:text;-webkit-user-select:text}
.pose-ascii{min-height:240px}.canonical-strip{margin-top:12px;border:1px solid var(--line);border-radius:14px}.canonical-strip summary{min-height:44px;display:flex;align-items:center;padding:0 12px;cursor:pointer;font-weight:750}
.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:14px}table{width:100%;border-collapse:collapse;min-width:420px}th,td{padding:10px 12px;border-bottom:1px solid var(--line);text-align:left}thead th{position:sticky;top:0;background:#171719}tbody tr:last-child th,tbody tr:last-child td{border-bottom:0}
.gif-stage{height:100%;display:grid;place-items:center}.gif-stage img{display:block;max-width:100%;max-height:100%;object-fit:contain;border:1px solid var(--line);border-radius:14px;background:#000}
.source-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));gap:10px}.source-card{min-width:0;border:1px solid var(--line);border-radius:14px;overflow:hidden}.source-card h2{margin:0;padding:8px 10px;border-bottom:1px solid var(--line);font-size:14px}
.meta{margin:0 0 12px;color:var(--muted);font-size:13px;line-height:1.4}
@media(max-width:520px){:root{--ascii-size:15px}.panel{padding:8px}.pose-grid{grid-template-columns:1fr}.pose-ascii{min-height:220px}}
@media print{html,body{overflow:visible;background:#fff;color:#000}#app{height:auto;display:block;padding:0}.row{display:none}.workspace{border:0;background:#fff;overflow:visible}.panel{display:block!important;height:auto;overflow:visible;break-after:page}.ascii{color:#000;background:#fff;border:1px solid #aaa;white-space:pre}.pose-grid{grid-template-columns:repeat(2,1fr)}.gif-stage{height:auto}.gif-stage img{max-height:none}}
</style>
</head>
<body>
<main id="app" data-uapl-motion-spa="1" data-uapl-sha256="${sourceSha256}" data-gif-sha256="${gif.sha256}">
  <div class="row">
    <span class="title">${escapeHtml(displayTitle)}</span>
    <span id="status" class="status" aria-live="polite">UAPL ${sourceSha256.slice(0, 12)} · GIF ${gif.sha256.slice(0, 12)}</span>
  </div>
  <nav class="row" aria-label="Motion artifact views">
    <button type="button" data-view="contact" aria-pressed="true">Poses</button>
    <button type="button" data-view="timing" aria-pressed="false">Timing</button>
    <button type="button" data-view="gif" aria-pressed="false">GIF</button>
    <button type="button" data-view="source" aria-pressed="false">Source</button>
    <button type="button" id="smaller" aria-label="Decrease ASCII size">A−</button>
    <button type="button" id="resetSize" aria-label="Reset ASCII size">1:1</button>
    <button type="button" id="larger" aria-label="Increase ASCII size">A+</button>
  </nav>
  <section class="workspace">
    <section class="panel active" data-panel="contact" aria-label="ASCII pose contact sheet">
      <p class="meta">Literal characters. Responsive layout may reflow pose cards, but characters inside a pose never wrap or reorder.</p>
      <div class="pose-grid">${poseHtml}
      </div>
      <details class="canonical-strip">
        <summary>Canonical horizontal contact sheet</summary>
        <pre class="ascii" tabindex="0">${escapeHtml(contactSheet)}</pre>
      </details>
    </section>
    <section class="panel" data-panel="timing" aria-label="Timing sheet">
      <p class="meta">UAT timing opinion pinned to UAPL source <code>${sourceSha256}</code> at ${uat.fps} fps.</p>
      <div class="table-wrap">
        <table>
          <thead><tr><th>#</th><th>Pose</th><th>Ticks</th><th>Milliseconds</th></tr></thead>
          <tbody>${timingHtml}
          </tbody>
        </table>
      </div>
    </section>
    <section class="panel" data-panel="gif" aria-label="Compiled GIF playback">
      <div class="gif-stage"><img src="${gifDataUri}" alt="Animated GIF compiled from the UAPL pose source using the UAT timing profile"></div>
    </section>
    <section class="panel" data-panel="source" aria-label="Machine source">
      <div class="source-grid">
        <article class="source-card"><h2>UAPL source · ${sourceSha256}</h2><pre id="uaplSource" class="ascii" tabindex="0">${escapeHtml(sourceText)}</pre></article>
        <article class="source-card"><h2>UAT timing</h2><pre id="uatSource" class="ascii" tabindex="0">${escapeHtml(timingText)}</pre></article>
      </div>
    </section>
  </section>
</main>
<script>
(()=>{
  const runtime=${runtimeJson};
  const root=document.documentElement;
  const status=document.getElementById('status');
  let asciiSize=16;
  function setSize(next){asciiSize=Math.max(10,Math.min(30,next));root.style.setProperty('--ascii-size',asciiSize+'px');status.textContent='ASCII '+asciiSize+'px · UAPL '+runtime.sourceSha256.slice(0,12)}
  function show(name){document.querySelectorAll('[data-panel]').forEach(p=>p.classList.toggle('active',p.dataset.panel===name));document.querySelectorAll('[data-view]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.view===name)));status.textContent=name.toUpperCase()+' · UAPL '+runtime.sourceSha256.slice(0,12)}
  document.querySelectorAll('[data-view]').forEach(button=>button.addEventListener('click',()=>show(button.dataset.view)));
  document.getElementById('smaller').addEventListener('click',()=>setSize(asciiSize-1));
  document.getElementById('resetSize').addEventListener('click',()=>setSize(16));
  document.getElementById('larger').addEventListener('click',()=>setSize(asciiSize+1));
  window.__UAPL_MOTION_SPA__=Object.freeze({...runtime,show,setAsciiSize:setSize});
  window.__UAPL_MOTION_SPA_READY__=true;
})();
</script>
</body>
</html>`;
}

module.exports = {
  canonicalUat,
  assertGifDataUri,
  buildMotionSpa,
};
