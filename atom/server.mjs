import http from 'node:http';
import { readFile, mkdir, appendFile, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { homedir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { randomUUID } from 'node:crypto';
import { spawn } from 'node:child_process';
import { createJudgementJarService } from './judgement-jars.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = dirname(here);
const stateDir = process.env.ATOM_STATE_DIR || join(homedir(), '.local', 'state', 'atom');
const port = Number(process.env.ATOM_PORT || 8788);
const host = process.env.ATOM_HOST || '127.0.0.1';
const commandsFile = join(stateDir, 'commands.jsonl');
const receiptsFile = join(stateDir, 'receipts.jsonl');
const missionFile = join(stateDir, 'missions.json');
const tabsFile = join(stateDir, 'throne-tabs.json');
const vladContractPath = join(here, 'vlad-operating-contract.json');
await mkdir(stateDir, { recursive: true });

async function lines(path) {
  if (!existsSync(path)) return [];
  return (await readFile(path, 'utf8'))
    .split('\n')
    .filter(Boolean)
    .map(value => {
      try { return JSON.parse(value); } catch { return null; }
    })
    .filter(Boolean);
}

async function jsonFile(path, fallback) {
  try { return JSON.parse(await readFile(path, 'utf8')); } catch { return fallback; }
}

async function body(req, limit = 128000) {
  const chunks = [];
  let size = 0;
  for await (const chunk of req) {
    size += chunk.length;
    if (size > limit) throw Object.assign(new Error('BODY_TOO_LARGE'), { status: 413 });
    chunks.push(chunk);
  }
  return chunks.length ? JSON.parse(Buffer.concat(chunks).toString('utf8')) : {};
}

function send(res, status, value) {
  const raw = Buffer.from(JSON.stringify(value));
  res.writeHead(status, {
    'content-type': 'application/json; charset=utf-8',
    'content-length': raw.length,
    'cache-control': 'no-store',
  });
  res.end(raw);
}

async function receipt(kind, summary, extra = {}) {
  const value = {
    receiptId: randomUUID(),
    kind,
    summary,
    state: extra.state || 'recorded',
    at: new Date().toISOString(),
    ...extra,
  };
  await appendFile(receiptsFile, `${JSON.stringify(value)}\n`);
  return value;
}

const jarService = await createJudgementJarService({ repoRoot, stateDir, emitReceipt: receipt });

async function saveMission(command) {
  const missions = await jsonFile(missionFile, []);
  const mission = {
    missionId: command.clientCommandId || randomUUID(),
    title: command.text.slice(0, 96),
    summary: 'Queued for Atom routing',
    state: 'QUEUED',
    receiptState: 'queued',
    createdAt: command.createdAt || new Date().toISOString(),
  };
  missions.unshift(mission);
  await writeFile(missionFile, JSON.stringify(missions.slice(0, 200), null, 2));
  return mission;
}

function classifyDiagnostic(text, code) {
  const value = String(text || '');
  if (/\b(HEALTHY|RECOVERED)\b/.test(value) && !/(DEGRADED|HUMAN_REQUIRED|ACTION NEEDED|BLOCKED)/.test(value)) return 'complete';
  if (/HUMAN_REQUIRED|ACTION NEEDED|BLOCKED/.test(value)) return 'blocked';
  if (/DEGRADED/.test(value) || code !== 0) return 'degraded';
  return 'unknown';
}

async function diagnose() {
  const watchdog = join(homedir(), 'bin', 'phone-hands-watchdog');
  if (!existsSync(watchdog)) return receipt('diagnostic', 'Phone Hands watchdog is not installed.', { state: 'blocked', blocker: 'WATCHDOG_MISSING' });
  return await new Promise(resolve => {
    const child = spawn(watchdog, ['diagnose'], { env: process.env });
    let out = '';
    let err = '';
    child.stdout.on('data', data => { out += data; });
    child.stderr.on('data', data => { err += data; });
    child.on('close', async code => {
      const summary = (out || err || `watchdog exit ${code}`).trim().slice(-4000);
      resolve(await receipt('diagnostic', summary, { state: classifyDiagnostic(summary, code), exitCode: code }));
    });
  });
}

async function vladStatus() {
  const contract = await jsonFile(vladContractPath, null);
  if (!contract) return { loaded: false, state: 'blocked', error: 'VLAD_CONTRACT_MISSING', path: vladContractPath };
  return {
    loaded: true,
    state: 'deterministic',
    identity: contract.identity,
    kind: contract.kind,
    wound: contract.wound,
    virtue: contract.virtue,
    role: contract.role,
    defaultMode: contract.defaultMode,
    ollamaDefault: contract.inferencePolicy?.ollamaDefault || 'disabled',
    maxParallelWorkers: Number(contract.swarm?.maxParallelWorkers || 0),
    operatorSurface: contract.swarm?.operatorSurface || '',
    codingOwner: contract.codingOwner || 'Venice',
    finalRelease: contract.finalRelease || 'Tetsuya',
    judgementJars: await jarService.status(),
  };
}

async function contextAccessReceipt(jar, source) {
  const now = new Date().toISOString();
  return jarService.recordUsage({
    schema: 'home-center.judgement-jar-usage-receipt.v1',
    receiptId: randomUUID(),
    createdAt: now,
    createdAtEpochMs: Date.now(),
    captureState: 'CAPTURED',
    homeCenterDeliveryState: 'PENDING',
    jar: {
      id: jar.id,
      order: jar.order,
      title: jar.title,
      path: jar.path,
      filename: jar.filename,
      sha256: jar.sha256,
      bytes: jar.bytes,
    },
    invocation: {
      source,
      requestId: randomUUID(),
      inputSha256: jar.sha256,
      inputBytes: jar.bytes,
    },
    output: {
      kind: 'context_packet',
      status: 'created',
      summary: `Vlad loaded exact Judgment Jar context: ${jar.title}`,
      sha256: jar.sha256,
      bytes: jar.bytes,
      references: [jar.path],
    },
    metadata: { access: 'atom-fast-path' },
  });
}

const staticRoot = join(here, 'addons', 'chromium-throne');
const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url, `http://${req.headers.host || host}`);
    if (req.method === 'GET' && (url.pathname === '/' || url.pathname === '/index.html')) {
      const raw = await readFile(join(staticRoot, 'index.html'));
      res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' });
      return res.end(raw);
    }
    if (req.method === 'GET' && url.pathname === '/addon.mjs') {
      const raw = await readFile(join(staticRoot, 'addon.mjs'));
      res.writeHead(200, { 'content-type': 'text/javascript; charset=utf-8' });
      return res.end(raw);
    }
    if (req.method === 'GET' && url.pathname === '/manifest.webmanifest') {
      const raw = await readFile(join(staticRoot, 'manifest.webmanifest'));
      res.writeHead(200, { 'content-type': 'application/manifest+json' });
      return res.end(raw);
    }
    if (req.method === 'GET' && url.pathname === '/sw.js') {
      const raw = await readFile(join(staticRoot, 'sw.js'));
      res.writeHead(200, { 'content-type': 'text/javascript; charset=utf-8', 'service-worker-allowed': '/' });
      return res.end(raw);
    }
    if (req.method === 'GET' && url.pathname === '/v1/atom/status') {
      const missions = await jsonFile(missionFile, []);
      return send(res, 200, {
        ok: true,
        state: 'online',
        service: 'Atom',
        offlinePrepared: true,
        terminalRequired: false,
        vlad: await vladStatus(),
        missions: missions.filter(value => !['COMPLETE', 'CANCELLED'].includes(value.state)).slice(0, 50),
      });
    }
    if (req.method === 'GET' && url.pathname === '/v1/atom/vlad') {
      return send(res, 200, { ok: true, vlad: await vladStatus(), contract: await jsonFile(vladContractPath, null) });
    }
    if (req.method === 'GET' && url.pathname === '/v1/atom/vlad/jars') {
      return send(res, 200, { ok: true, ...(await jarService.list()) });
    }
    if (req.method === 'GET' && url.pathname.startsWith('/v1/atom/vlad/jars/')) {
      const reference = decodeURIComponent(url.pathname.slice('/v1/atom/vlad/jars/'.length));
      const jar = await jarService.get(reference);
      if (!jar) return send(res, 404, { ok: false, error: 'JAR_NOT_FOUND' });
      const usage = await contextAccessReceipt(jar, 'atom.vlad.jar.get');
      return send(res, 200, { ok: true, jar, usage });
    }
    if (req.method === 'POST' && url.pathname === '/v1/atom/vlad/jars/sync') {
      const result = await jarService.syncRepositoryCatalog(await body(req));
      return send(res, result.status, result);
    }
    if (req.method === 'POST' && url.pathname === '/v1/atom/vlad/jars/receipts') {
      const result = await jarService.recordUsage(await body(req));
      return send(res, result.status, result);
    }
    if (req.method === 'POST' && url.pathname === '/v1/atom/commands') {
      const input = await body(req);
      if (input.humanInitiated !== true || typeof input.text !== 'string' || !input.text.trim()) return send(res, 400, { error: 'INVALID_COMMAND' });
      const command = {
        clientCommandId: input.clientCommandId || randomUUID(),
        text: input.text.trim(),
        createdAt: input.createdAt || new Date().toISOString(),
        source: input.source || 'atom',
        humanInitiated: true,
        state: 'QUEUED',
        orchestrator: 'Vlad',
        mode: 'deterministic',
      };
      await appendFile(commandsFile, `${JSON.stringify(command)}\n`);
      const mission = await saveMission(command);
      const accepted = await receipt('command.accepted', `Atom/Vlad accepted: ${command.text.slice(0, 180)}`, {
        state: 'queued',
        missionId: mission.missionId,
        orchestrator: 'Vlad',
        mode: 'deterministic',
      });
      return send(res, 202, { ok: true, mission, receipt: accepted, vlad: await vladStatus() });
    }
    if (req.method === 'GET' && url.pathname === '/v1/atom/receipts') {
      const values = await lines(receiptsFile);
      return send(res, 200, { receipts: values.reverse().slice(0, 100) });
    }
    if (req.method === 'POST' && url.pathname === '/v1/atom/diagnose') return send(res, 200, await diagnose());
    if (req.method === 'GET' && url.pathname === '/v1/atom/throne/tabs') return send(res, 200, { tabs: await jsonFile(tabsFile, []) });
    return send(res, 404, { error: 'NOT_FOUND' });
  } catch (error) {
    return send(res, error.status || 500, { error: error.message });
  }
});

server.listen(port, host, () => console.log(JSON.stringify({
  ok: true,
  service: 'Atom',
  url: `http://${host}:${port}`,
  stateDir,
  terminalRequired: false,
  vladContract: vladContractPath,
  judgementJars: true,
})));
