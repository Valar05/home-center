#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {homedir} from 'node:os';

const ROOT = path.resolve(new URL('..', import.meta.url).pathname);
const HELPER = '/storage/emulated/0/Documents/GodotProjects/.codex/skills/android-shizuku-app-operator/scripts/shizuku_app_control.sh';
const CHROME = 'com.android.chrome';
const CHATGPT_URL = 'https://chatgpt.com/?temporary-chat=true';
const COMMAND_CENTER_MCP_URL = process.env.HOME_CENTER_COMMAND_CENTER_MCP_URL || 'https://us-central1-home-center-dclar.cloudfunctions.net/commandCenterMcp/mcp';

function stamp() {
  return new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14);
}

function parseArgs(argv) {
  const args = {
    runId: `chatgpt-home-center-mcp-${stamp()}`,
    waitMs: 3000,
    maxLoops: 20,
    skipBackend: false,
    mode: 'bucket',
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--run-id') args.runId = argv[++i];
    else if (arg === '--wait-ms') args.waitMs = Number(argv[++i]) || args.waitMs;
    else if (arg === '--max-loops') args.maxLoops = Number(argv[++i]) || args.maxLoops;
    else if (arg === '--skip-backend') args.skipBackend = true;
    else if (arg === '--mode') args.mode = argv[++i];
    else if (arg === '--help') {
      console.log('Usage: node tools/shizuku_it_chatgpt_home_center_mcp.mjs [--run-id ID] [--wait-ms N] [--max-loops N] [--skip-backend] [--mode bucket|activation]');
      process.exit(0);
    } else {
      throw new Error(`Unknown arg: ${arg}`);
    }
  }
  args.runId = args.runId.replace(/[^A-Za-z0-9_.-]+/g, '-').slice(0, 140);
  if (!['bucket', 'activation'].includes(args.mode)) throw new Error(`Unsupported --mode: ${args.mode}`);
  return args;
}

function ensureDir(dir) {
  fs.mkdirSync(dir, {recursive: true});
}

function run(command, args, options = {}) {
  const startedAt = new Date().toISOString();
  const proc = spawnSync(command, args, {
    cwd: ROOT,
    encoding: 'utf8',
    timeout: options.timeoutMs || 120000,
    input: options.input,
    env: {...process.env, ...(options.env || {})},
  });
  return {
    command,
    args,
    status: proc.status,
    signal: proc.signal || '',
    error: proc.error ? String(proc.error.message || proc.error) : '',
    stdout: proc.stdout || '',
    stderr: proc.stderr || '',
    startedAt,
    finishedAt: new Date().toISOString(),
  };
}

function parseJson(text, fallback = null) {
  try {
    return JSON.parse(text);
  } catch (_) {
    return fallback;
  }
}

function parseMcpText(text) {
  const dataLines = String(text || '').split(/\r?\n/).filter((line) => line.startsWith('data:')).map((line) => line.slice(5).trim());
  return parseJson(dataLines.length ? dataLines.join('\n') : text, null);
}

function toolJson(payload) {
  const text = payload?.result?.content?.find((item) => item.type === 'text')?.text || '';
  return parseJson(text, null);
}

function readPairingToken() {
  const configPath = process.env.HOME_CENTER_CODEX_CONFIG || path.join(homedir(), '.config', 'home-center', 'codex-hub.json');
  if (!fs.existsSync(configPath)) return {ok: false, configPath, reason: 'missing_config'};
  const config = parseJson(fs.readFileSync(configPath, 'utf8'), {});
  if (config.accessToken) return {ok: true, configPath, token: config.accessToken, refreshed: false};
  if (!config.refreshToken) return {ok: false, configPath, reason: 'missing_access_token'};
  const refresh = run('node', ['tools/home_center_codex_pair.mjs', 'refresh', '--config', configPath], {timeoutMs: 60000});
  const updated = fs.existsSync(configPath) ? parseJson(fs.readFileSync(configPath, 'utf8'), {}) : {};
  return updated.accessToken
    ? {ok: true, configPath, token: updated.accessToken, refreshed: true}
    : {ok: false, configPath, reason: 'refresh_failed', status: refresh.status, stderr: refresh.stderr.slice(0, 1000)};
}

function callMcpTool(mcpUrl, token, name, args = {}) {
  const payload = JSON.stringify({jsonrpc: '2.0', id: 900, method: 'tools/call', params: {name, arguments: args}});
  const proc = run('curl', ['-sS', '-X', 'POST', mcpUrl, '-H', `Authorization: Bearer ${token}`, '-H', 'Content-Type: application/json', '-H', 'Accept: application/json, text/event-stream', '--data-binary', payload], {timeoutMs: 45000});
  return {status: proc.status, stderr: proc.stderr, payload: parseMcpText(proc.stdout)};
}

function readCommandCenterTool(name, args) {
  const token = readPairingToken();
  if (!token.ok) return {ok: false, status: 'blocked_local_setup_token', token: {...token, token: undefined}};
  const call = callMcpTool(COMMAND_CENTER_MCP_URL, token.token, name, args);
  const body = toolJson(call.payload);
  return {token, call, body};
}

function readActivationFromBackend(activationId) {
  const result = readCommandCenterTool('command_center_operation', {
    operation: 'agents.get_resume_packet',
    args: {activationId},
  });
  if (!result.token?.ok) return result;
  const {token, call, body} = result;
  const resumePacket = body?.result?.resumePacket || body?.resumePacket || null;
  const ok = call.status === 0 && resumePacket?.activationId === activationId && resumePacket?.packetVersion === 'command-center-codex-cloud-resume-v1';
  return {ok, status: ok ? 'activation_readback_ok' : 'activation_not_found', activationId, token: {configPath: token.configPath, refreshed: token.refreshed, hasToken: true}, callStatus: call.status, mcpError: call.payload?.error || null, packetVersion: resumePacket?.packetVersion || '', agentId: resumePacket?.agent?.agentId || ''};
}

function readBucketObjectFromBackend(objectId) {
  const result = readCommandCenterTool('command_center.bucket.get_object', {objectId});
  if (!result.token?.ok) return result;
  const {token, call, body} = result;
  const object = body?.object || body?.result?.object || null;
  const ok = call.status === 0 && object?.objectId === objectId && object?.body === 'hello world';
  return {ok, status: ok ? 'bucket_readback_ok' : 'bucket_object_not_found', objectId, token: {configPath: token.configPath, refreshed: token.refreshed, hasToken: true}, callStatus: call.status, mcpError: call.payload?.error || null, found: body?.found === true || body?.result?.found === true, path: object?.path || '', bodyMatches: object?.body === 'hello world'};
}

function writeStep(outDir, name, record) {
  const file = path.join(outDir, `${name}.json`);
  fs.writeFileSync(file, JSON.stringify(record, null, 2) + '\n');
  return file;
}

function findRish() {
  const candidates = [
    process.env.RISH,
    path.join(homedir(), 'bin/rish'),
    path.join(homedir(), 'rish'),
    path.join(homedir(), '.local/bin/rish'),
    '/storage/emulated/0/Android/data/moe.shizuku.privileged.api/files/rish',
    '/storage/emulated/0/Documents/rish',
    '/storage/emulated/0/Download/rish',
    '/sdcard/rish',
  ].filter(Boolean);
  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) return candidate;
  }
  const found = spawnSync('sh', ['-c', 'command -v rish'], {encoding: 'utf8'});
  return found.status === 0 ? found.stdout.trim() : '';
}

function shellQuote(value) {
  return `'${String(value).replace(/'/g, `'\\''`)}'`;
}

function rish(command, timeoutMs = 30000) {
  const bin = findRish();
  if (!bin) return {command: 'rish', args: ['-c', command], status: 127, stdout: '', stderr: 'missing rish', error: '', startedAt: new Date().toISOString(), finishedAt: new Date().toISOString()};
  fs.chmodSync(bin, 0o700);
  return run(bin, ['-c', command], {timeoutMs});
}

function helper(command, args, outDir, options = {}) {
  return run('sh', [HELPER, command, '--package', CHROME, '--out-dir', outDir, ...args], options);
}

function chromeLaunch(url) {
  return rish(`am start -W --windowingMode 1 --activity-clear-top -n com.android.chrome/com.google.android.apps.chrome.Main -a android.intent.action.VIEW -d ${shellQuote(url)}`, 30000);
}

function focusIsChrome(dir) {
  const file = path.join(dir, 'focus.txt');
  const text = fs.existsSync(file) ? fs.readFileSync(file, 'utf8') : '';
  return /com\.android\.chrome\/org\.chromium\.chrome\.browser\.ChromeTabbedActivity|com\.android\.chrome/.test(text);
}

function readXml(dir) {
  const file = path.join(dir, 'window.xml');
  return fs.existsSync(file) ? fs.readFileSync(file, 'utf8') : '';
}

function parseNodes(xml) {
  const nodes = [];
  const nodeRe = /<node\b([^>]*)\/?>/g;
  let match;
  while ((match = nodeRe.exec(xml))) {
    const attrs = {};
    const attrRe = /([A-Za-z0-9_-]+)="([^"]*)"/g;
    let attr;
    while ((attr = attrRe.exec(match[1]))) attrs[attr[1]] = attr[2];
    const bounds = String(attrs.bounds || '').match(/\[(\d+),(\d+)\]\[(\d+),(\d+)\]/);
    if (bounds) {
      attrs.x1 = Number(bounds[1]);
      attrs.y1 = Number(bounds[2]);
      attrs.x2 = Number(bounds[3]);
      attrs.y2 = Number(bounds[4]);
      attrs.cx = Math.round((attrs.x1 + attrs.x2) / 2);
      attrs.cy = Math.round((attrs.y1 + attrs.y2) / 2);
      attrs.area = Math.max(0, attrs.x2 - attrs.x1) * Math.max(0, attrs.y2 - attrs.y1);
    }
    nodes.push(attrs);
  }
  return nodes;
}

function nodeText(node) {
  return [node.text, node['content-desc'], node.hint, node['resource-id'], node.class].filter(Boolean).join(' ');
}

function visibleText(xml) {
  return parseNodes(xml).map(nodeText).filter(Boolean).join('\n').slice(0, 50000);
}

function findComposer(nodes) {
  const candidates = nodes.filter((node) => {
    const text = nodeText(node);
    if (!/EditText|textbox|textarea|Message|Ask anything|prompt/i.test(text)) return false;
    if (/url_bar|Search Google|type URL|address/i.test(text)) return false;
    return Number.isFinite(node.cx) && Number.isFinite(node.cy);
  });
  candidates.sort((a, b) => (b.y1 || 0) - (a.y1 || 0) || (b.area || 0) - (a.area || 0));
  return candidates[0] || null;
}

function findButton(nodes, patterns) {
  const candidates = nodes.filter((node) => {
    if (!Number.isFinite(node.cx) || !Number.isFinite(node.cy)) return false;
    const text = nodeText(node);
    if (!/true/i.test(String(node.clickable || 'true')) && !/Button|ImageButton/i.test(String(node.class || ''))) return false;
    return patterns.some((pattern) => pattern.test(text));
  });
  candidates.sort((a, b) => (b.y1 || 0) - (a.y1 || 0));
  return candidates[0] || null;
}

function tapPointFor(node, fallback = {}) {
  if (Number(node.area || 0) > 0) return {x: node.cx, y: node.cy};
  const x1 = Number(node.x1);
  const y1 = Number(node.y1);
  const x2 = Number(node.x2);
  const y2 = Number(node.y2);
  if (Number.isFinite(x1) && Number.isFinite(y1) && Number.isFinite(x2) && Number.isFinite(y2)) {
    const y = y2 > y1 ? Math.round((y1 + y2) / 2) : Math.max(1, y1 - Number(fallback.yInset || 18));
    return {x: Math.round((x1 + x2) / 2), y};
  }
  if (Number.isFinite(x1) && Number.isFinite(y1)) {
    return {x: Math.max(1, x1 - Number(fallback.edgeInset || 32)), y: Math.max(1, y1 - Number(fallback.yInset || 20))};
  }
  return {x: Number(fallback.x || 960), y: Number(fallback.y || 1460)};
}

function classifyVisible(text) {
  if (/Lock screen|Fingerprint sensor|keyguard|NotificationShade/i.test(text)) return 'blocked_android_keyguard_or_notification_shade';
  if (/com\.google\.android\.apps\.nexuslauncher|NexusLauncher|Messages Messages|Phone Phone|Gmail Gmail/i.test(text)) return 'blocked_wrong_foreground_launcher';
  if (/chatgpt_hello_world_[A-Za-z0-9_-]+/.test(text) && /bodyMatches["':\s]+true|hello world/i.test(text)) return 'chatgpt_mcp_bucket_object_visible';
  if (/bucket\.put_object|bucket\.get_object|command_center\.bucket/i.test(text) && /not available|unavailable|no tool|can't complete|cannot complete/i.test(text)) return 'chatgpt_bucket_tools_unavailable';
  if (/activation_[A-Za-z0-9_-]+/.test(text) && /command-center-codex-cloud-resume-v1|packetVersion|resumePacket/i.test(text)) return 'chatgpt_mcp_agent_activation_visible';
  if (/"agentId"\s*:\s*null[\s\S]*"activationId"\s*:\s*null|agentId null[\s\S]*activationId null/i.test(text)) return 'chatgpt_answered_without_tool_call';
  if (/Cloudflare|Verify you are human|captcha|Turnstile/i.test(text)) return 'blocked_chatgpt_web_auth_or_verification';
  if (/Log in|Sign up|Sign in|Continue with Google/i.test(text)) return 'blocked_chatgpt_login';
  if (/Connect Home Center|Connectors|MCP|Apps and connectors/i.test(text) && /Disconnected|Connect/i.test(text)) return 'blocked_chatgpt_connector_setup';
  if (/Home Center|command_center_operation|agents\.create_activation|agents\.get_resume_packet/i.test(text)) return 'chatgpt_task_in_progress_or_visible';
  return 'chatgpt_visible_state_unclassified';
}

function makeActivationSpec(runId) {
  const safeRun = runId.replace(/[^A-Za-z0-9_-]/g, '-').slice(0, 48);
  const agentId = `hc-cgpt-${safeRun}`;
  const activationId = `activation_${safeRun}`;
  return {safeRun, agentId, activationId};
}

function makeBucketSpec(runId) {
  const safeRun = runId.replace(/[^A-Za-z0-9_-]/g, '-').slice(0, 48);
  const objectId = `chatgpt_hello_world_${safeRun}`;
  const path = `notes/cross-repo/chatgpt-hello-world-${safeRun}.md`;
  return {safeRun, objectId, path};
}

function makePrompt(runId) {
  const {safeRun, objectId, path: objectPath} = makeBucketSpec(runId);
  return `Use the attached Home Center or Command Center MCP tools now. Do not answer from memory. If command_center_operation is available, call it with operation=bucket.put_object. If command_center_operation is not available, call the namespaced tool command_center.bucket.put_object directly. Args: {"idempotencyKey":"chatgpt-hello-world-${safeRun}","objectId":"${objectId}","kind":"note.cross_repo","path":"${objectPath}","title":"ChatGPT Home Center hello world","summary":"ChatGPT-to-Home-Center-to-Command-Center mutation proof","body":"hello world","projectId":"home-center","repository":"Valar05/home-center","tags":["chatgpt-acceptance","hello-world","effective-no-op"]}. Then read the same object back using command_center_operation operation=bucket.get_object or namespaced command_center.bucket.get_object with objectId="${objectId}". Reply JSON only: {"objectId":"${objectId}","path":"${objectPath}","bodyMatches":true}.`;
}

function makeActivationPrompt(runId) {
  const {safeRun, agentId, activationId} = makeActivationSpec(runId);
  return `Use Home Center MCP tools now. Do not answer from memory and do not simulate tool output. Use the Home Center tool command_center_operation, not a separate Command Center app namespace. Step 1: call command_center_operation with operation agents.upsert_repo_agent and args {"idempotencyKey":"chatgpt-cloud-codex-upsert-${safeRun}","agentId":"${agentId}","repository":"Valar05/home-center","name":"ChatGPT dispatched real cloud Codex worker","capabilities":["codex-cloud","repo-work","durable-handoff"],"currentSummary":"ChatGPT is proving it can dispatch a real Codex cloud activation through Home Center and Command Center."}. Step 2: call command_center_operation with operation agents.create_activation and args {"idempotencyKey":"chatgpt-cloud-codex-activation-${safeRun}","agentId":"${agentId}","activationId":"${activationId}","task":{"prompt":"I am a real Codex cloud worker activation dispatched by ChatGPT through Home Center command_center_operation. Inspect the resume packet and report readiness only.","acceptanceCriteria":["Activation was created through ChatGPT MCP tool use","Resume packet can be read back","Do not claim simulated worker execution"],"constraints":["Do not mutate files","Do not use simulated worker registry entries"]},"requestedBy":"chatgpt","source":"chatgpt-home-center-mcp"}. Step 3: call command_center_operation with operation agents.get_resume_packet and args {"activationId":"${activationId}"}. Reply only JSON with {"agentId":"${agentId}","activationId":"${activationId}","packetVersion":"command-center-codex-cloud-resume-v1","dispatchedByChatGPT":true} and no prose.`;
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const outDir = path.join(ROOT, 'tools', 'chatgpt_connector_evidence', args.runId);
  ensureDir(outDir);

  const summary = {
    ok: false,
    runId: args.runId,
    command: args.mode === 'activation'
      ? 'shizuku it: ChatGPT web dispatches a real Codex cloud activation through Home Center command_center_operation.'
      : 'shizuku it: ChatGPT web consumes Home Center or Command Center MCP bucket tools.',
    forbiddenStalePremise: args.mode === 'activation'
      ? 'A simulated worker registry entry is not a real Codex cloud dispatch.'
      : 'agents.* is required even when ChatGPT attached only namespaced Command Center tools.',
    intendedMutation: args.mode === 'activation'
      ? 'Create a deterministic Command Center Codex cloud activation and read back its resume packet through ChatGPT web.'
      : 'Create and read a deterministic Command Center bucket object through ChatGPT web.',
    evidenceDir: outDir,
    promptPath: path.join(outDir, 'chatgpt_prompt.txt'),
    steps: [],
    status: 'started',
  };

  const prompt = args.mode === 'activation' ? makeActivationPrompt(args.runId) : makePrompt(args.runId);
  const bucketSpec = makeBucketSpec(args.runId);
  const activationSpec = makeActivationSpec(args.runId);
  summary.bucketSpec = bucketSpec;
  summary.activationSpec = activationSpec;
  fs.writeFileSync(summary.promptPath, prompt + '\n');

  if (!args.skipBackend) {
    const home = run('node', ['tools/command_center_home_bridge_invokability_gate.mjs', '--json', '--run-id', `${args.runId}-home`], {timeoutMs: 180000});
    summary.steps.push({name: 'backend_home_center_bridge', status: home.status, path: writeStep(outDir, 'backend_home_center_bridge', home)});
    const direct = run('node', ['tools/command_center_chatgpt_invokability_gate.mjs', '--json', '--run-id', `${args.runId}-direct`], {timeoutMs: 180000});
    summary.steps.push({name: 'backend_command_center_direct', status: direct.status, path: writeStep(outDir, 'backend_command_center_direct', direct)});
    if (home.status !== 0 || direct.status !== 0) {
      summary.status = 'blocked_home_center_mcp_backend';
      summary.ok = false;
      fs.writeFileSync(path.join(outDir, 'summary.json'), JSON.stringify(summary, null, 2) + '\n');
      console.log(JSON.stringify({ok: false, status: summary.status, evidenceDir: outDir, summaryPath: path.join(outDir, 'summary.json')}, null, 2));
      process.exit(2);
    }
  }

  const launch = chromeLaunch(CHATGPT_URL);
  summary.steps.push({name: 'launch_chatgpt_chrome_direct', status: launch.status, path: writeStep(outDir, 'launch_chatgpt_chrome_direct', launch)});
  const launchDir = path.join(outDir, '01_launch_chatgpt');
  const launchProbe = helper('probe', ['--no-launch', '--sleep', '2', '--xml-timeout', '8'], launchDir, {timeoutMs: 45000});
  summary.steps.push({name: 'launch_chatgpt_probe', status: launchProbe.status, path: writeStep(outDir, 'launch_chatgpt_probe', launchProbe), evidenceDir: launchDir});
  if (!focusIsChrome(launchDir)) {
    summary.status = 'blocked_chrome_not_focused_after_launch';
    summary.visibleTextPath = path.join(outDir, 'visible_text_initial.txt');
    fs.writeFileSync(summary.visibleTextPath, visibleText(readXml(launchDir)) + '\n');
    fs.writeFileSync(path.join(outDir, 'summary.json'), JSON.stringify(summary, null, 2) + '\n');
    console.log(JSON.stringify({ok: false, status: summary.status, evidenceDir: outDir, summaryPath: path.join(outDir, 'summary.json')}, null, 2));
    process.exit(2);
  }
  let xml = readXml(launchDir);
  let text = visibleText(xml);
  let state = classifyVisible(text);
  let nodes = parseNodes(xml);
  if (/blocked_chatgpt/.test(state) && !(state === 'blocked_chatgpt_connector_setup' && findComposer(nodes))) {
    summary.status = state;
    summary.visibleTextPath = path.join(outDir, 'visible_text_initial.txt');
    fs.writeFileSync(summary.visibleTextPath, text + '\n');
    fs.writeFileSync(path.join(outDir, 'summary.json'), JSON.stringify(summary, null, 2) + '\n');
    console.log(JSON.stringify({ok: false, status: summary.status, evidenceDir: outDir, summaryPath: path.join(outDir, 'summary.json')}, null, 2));
    process.exit(2);
  }

  const closeModal = findButton(nodes, [/^Close$/i]);
  if (closeModal && /modal-|General|Plugins|Settings|Notifications|Personalization/i.test(text)) {
    const closeModalDir = path.join(outDir, '01aa_close_modal');
    const point = tapPointFor(closeModal);
    const closeTap = helper('tap', ['--x', String(point.x), '--y', String(point.y), '--sleep', '2', '--xml-timeout', '8'], closeModalDir, {timeoutMs: 45000});
    summary.steps.push({name: 'close_modal', status: closeTap.status, path: writeStep(outDir, 'close_modal', closeTap), evidenceDir: closeModalDir, target: closeModal});
    xml = readXml(closeModalDir);
    text = visibleText(xml);
    nodes = parseNodes(xml);
  }

  const closeSidebar = findButton(nodes, [/Close sidebar/i]);
  if (closeSidebar) {
    const closeDir = path.join(outDir, '01a_close_sidebar');
    const point = tapPointFor(closeSidebar);
    const closeTap = helper('tap', ['--x', String(point.x), '--y', String(point.y), '--sleep', '1', '--xml-timeout', '8'], closeDir, {timeoutMs: 45000});
    summary.steps.push({name: 'close_sidebar', status: closeTap.status, path: writeStep(outDir, 'close_sidebar', closeTap), evidenceDir: closeDir, target: closeSidebar});
    xml = readXml(closeDir);
    text = visibleText(xml);
    nodes = parseNodes(xml);
  }

  const newChat = findButton(nodes, [/New chat/i]);
  if (newChat) {
    const newChatDir = path.join(outDir, '01b_new_chat');
    const point = tapPointFor(newChat);
    const newChatTap = helper('tap', ['--x', String(point.x), '--y', String(point.y), '--sleep', '2', '--xml-timeout', '8'], newChatDir, {timeoutMs: 45000});
    summary.steps.push({name: 'new_chat', status: newChatTap.status, path: writeStep(outDir, 'new_chat', newChatTap), evidenceDir: newChatDir, target: newChat});
    if (!focusIsChrome(newChatDir)) {
      summary.status = 'blocked_chrome_lost_focus_after_new_chat';
      fs.writeFileSync(path.join(outDir, 'summary.json'), JSON.stringify(summary, null, 2) + '\n');
      console.log(JSON.stringify({ok: false, status: summary.status, evidenceDir: outDir, summaryPath: path.join(outDir, 'summary.json')}, null, 2));
      process.exit(2);
    }
    xml = readXml(newChatDir);
    text = visibleText(xml);
    state = classifyVisible(text);
    nodes = parseNodes(xml);
  }

  const composer = findComposer(nodes);
  if (!composer) {
    summary.status = 'blocked_chatgpt_composer_not_found';
    summary.visibleTextPath = path.join(outDir, 'visible_text_initial.txt');
    fs.writeFileSync(summary.visibleTextPath, text + '\n');
    fs.writeFileSync(path.join(outDir, 'summary.json'), JSON.stringify(summary, null, 2) + '\n');
    console.log(JSON.stringify({ok: false, status: summary.status, evidenceDir: outDir, summaryPath: path.join(outDir, 'summary.json')}, null, 2));
    process.exit(2);
  }

  const focusDir = path.join(outDir, '02_focus_composer');
  const tapComposer = helper('tap', ['--x', String(composer.cx), '--y', String(composer.cy), '--sleep', '1', '--xml-timeout', '8'], focusDir, {timeoutMs: 45000});
  summary.steps.push({name: 'focus_composer', status: tapComposer.status, path: writeStep(outDir, 'focus_composer', tapComposer), evidenceDir: focusDir, target: composer});

  const clipboard = run('termux-clipboard-set', [], {input: prompt, timeoutMs: 15000});
  summary.steps.push({name: 'clipboard_set_prompt', status: clipboard.status, path: writeStep(outDir, 'clipboard_set_prompt', {...clipboard, stdout: '', stderr: clipboard.stderr.slice(0, 1000)})});
  const paste = rish('input keyevent 279; sleep 1', 20000);
  summary.steps.push({name: 'paste_prompt', status: paste.status, path: writeStep(outDir, 'paste_prompt', paste)});
  if (clipboard.status !== 0 || paste.status !== 0) {
    summary.status = 'blocked_local_setup_clipboard_or_rish';
    fs.writeFileSync(path.join(outDir, 'summary.json'), JSON.stringify(summary, null, 2) + '\n');
    console.log(JSON.stringify({ok: false, status: summary.status, evidenceDir: outDir, summaryPath: path.join(outDir, 'summary.json')}, null, 2));
    process.exit(2);
  }

  const pastedDir = path.join(outDir, '03_after_paste');
  const pasted = helper('probe', ['--no-launch', '--sleep', '1', '--xml-timeout', '8'], pastedDir, {timeoutMs: 35000});
  summary.steps.push({name: 'after_paste_probe', status: pasted.status, path: writeStep(outDir, 'after_paste_probe', pasted), evidenceDir: pastedDir});
  xml = readXml(pastedDir);
  let send = findButton(parseNodes(xml), [/Send/i, /Submit/i, /Arrow up/i]);
  if (!send) {
    send = findButton(parseNodes(xml), [/message/i]);
  }
  if (!send) {
    summary.status = 'blocked_chatgpt_send_button_not_found';
    summary.visibleTextPath = path.join(outDir, 'visible_text_after_paste.txt');
    fs.writeFileSync(summary.visibleTextPath, visibleText(xml) + '\n');
    fs.writeFileSync(path.join(outDir, 'summary.json'), JSON.stringify(summary, null, 2) + '\n');
    console.log(JSON.stringify({ok: false, status: summary.status, evidenceDir: outDir, summaryPath: path.join(outDir, 'summary.json')}, null, 2));
    process.exit(2);
  }

  const sendDir = path.join(outDir, '04_send_prompt');
  const sendPoint = tapPointFor(send, {edgeInset: 36, yInset: 18, x: 960, y: 1460});
  const sent = helper('tap', ['--x', String(sendPoint.x), '--y', String(sendPoint.y), '--sleep', '3', '--xml-timeout', '8'], sendDir, {timeoutMs: 45000});
  summary.steps.push({name: 'send_prompt', status: sent.status, path: writeStep(outDir, 'send_prompt', sent), evidenceDir: sendDir, target: send});
  const enterSend = rish('input keyevent 66; sleep 2', 15000);
  summary.steps.push({name: 'send_prompt_enter_backup', status: enterSend.status, path: writeStep(outDir, 'send_prompt_enter_backup', enterSend)});

  const approvalPatterns = [/^Allow$/i, /^Continue$/i, /^Run$/i, /Run tool/i, /Use Home Center/i, /^Connect$/i, /^Authorize$/i, /^Approve$/i, /^Yes$/i];
  let finalText = '';
  let finalDir = sendDir;
  let readback = args.mode === 'activation' ? readActivationFromBackend(activationSpec.activationId) : readBucketObjectFromBackend(bucketSpec.objectId);
  for (let i = 0; i < args.maxLoops; i += 1) {
    readback = args.mode === 'activation' ? readActivationFromBackend(activationSpec.activationId) : readBucketObjectFromBackend(bucketSpec.objectId);
    if (readback.ok) {
      state = args.mode === 'activation' ? 'chatgpt_mcp_codex_cloud_activation_backend_readback_ok' : 'chatgpt_mcp_bucket_object_backend_readback_ok';
      break;
    }
    const loopDir = path.join(outDir, `05_wait_${String(i + 1).padStart(2, '0')}`);
    const probe = helper('probe', ['--no-launch', '--sleep', String(Math.max(1, Math.round(args.waitMs / 1000))), '--xml-timeout', '8'], loopDir, {timeoutMs: args.waitMs + 35000});
    summary.steps.push({name: `wait_probe_${i + 1}`, status: probe.status, path: writeStep(outDir, `wait_probe_${i + 1}`, probe), evidenceDir: loopDir});
    finalDir = loopDir;
    xml = readXml(loopDir);
    finalText = visibleText(xml);
    fs.writeFileSync(path.join(loopDir, 'visible_text.txt'), finalText + '\n');
    readback = args.mode === 'activation' ? readActivationFromBackend(activationSpec.activationId) : readBucketObjectFromBackend(bucketSpec.objectId);
    if (readback.ok) {
      state = args.mode === 'activation' ? 'chatgpt_mcp_codex_cloud_activation_backend_readback_ok' : 'chatgpt_mcp_bucket_object_backend_readback_ok';
      break;
    }
    state = classifyVisible(finalText);
    if (state === 'chatgpt_mcp_bucket_object_visible' || state === 'chatgpt_bucket_tools_unavailable') break;
    if (/blocked_chatgpt/.test(state)) break;
    const approval = findButton(parseNodes(xml), approvalPatterns);
    if (approval) {
      const approveDir = path.join(outDir, `06_approve_${String(i + 1).padStart(2, '0')}`);
      const clicked = helper('tap', ['--x', String(approval.cx), '--y', String(approval.cy), '--sleep', '2', '--xml-timeout', '8'], approveDir, {timeoutMs: 45000});
      summary.steps.push({name: `approve_connector_control_${i + 1}`, status: clicked.status, path: writeStep(outDir, `approve_connector_control_${i + 1}`, clicked), evidenceDir: approveDir, target: approval});
    }
  }

  summary.finalEvidenceDir = finalDir;
  summary.finalVisibleTextPath = path.join(outDir, 'final_visible_text.txt');
  fs.writeFileSync(summary.finalVisibleTextPath, finalText + '\n');
  summary.backendReadback = readback;
  summary.status = state;
  summary.ok = state === 'chatgpt_mcp_bucket_object_backend_readback_ok' || state === 'chatgpt_mcp_codex_cloud_activation_backend_readback_ok';
  fs.writeFileSync(path.join(outDir, 'summary.json'), JSON.stringify(summary, null, 2) + '\n');
  console.log(JSON.stringify({ok: summary.ok, status: summary.status, mode: args.mode, objectId: bucketSpec.objectId, activationId: activationSpec.activationId, readback, evidenceDir: outDir, summaryPath: path.join(outDir, 'summary.json'), finalEvidenceDir: finalDir}, null, 2));
  process.exit(summary.ok ? 0 : 2);
}

main();
