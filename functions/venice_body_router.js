'use strict';

const {computerHandsOperationRunOperation} = require('./computer_hands_api');
const {runCommandCenterOperation} = require('./command_center_mcp');

const BODY_ROUTER_VERSION = 'home-center.venice-body-router.v1';
const BROWSER_PREFIX = 'browser.';
const COMPUTER_PREFIX = 'computer.';
const BROWSER_VERBS = new Set([
  'browser.open', 'browser.navigate', 'browser.observe', 'browser.status', 'browser.read',
  'browser.find', 'browser.click', 'browser.type', 'browser.set_value', 'browser.select',
  'browser.submit', 'browser.scroll', 'browser.wait_for', 'browser.download',
]);
const DIRECT_COMPUTER_ACTIONS = new Set([
  'system.status', 'screen.capture', 'window.list', 'process.list', 'clipboard.get',
  'window.focus', 'input.type', 'input.key', 'input.mouse', 'process.start',
  'process.stop', 'shell.exec', 'clipboard.set', 'packet.execute',
]);

function safeText(value, max = 2000) {
  const text = value == null ? '' : String(value).trim();
  return text.length > max ? text.slice(0, max) : text;
}

function safeObject(value) {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
}

function stableKey(value, suffix) {
  const base = safeText(value, 130);
  if (!/^[A-Za-z0-9_.:-]{6,130}$/.test(base)) {
    const error = new Error('venice_body.action requires a stable requestId.');
    error.status = 400;
    throw error;
  }
  return `${base}:${suffix}`.slice(0, 160);
}

function classifyLane(args = {}) {
  const explicit = safeText(args.channel || args.lane, 40).toLowerCase();
  if (explicit === 'browser' || explicit === 'computer') return explicit;
  const verb = safeText(args.verb || args.action, 120).toLowerCase();
  if (verb.startsWith(BROWSER_PREFIX) || BROWSER_VERBS.has(verb)) return 'browser';
  return 'computer';
}

function browserActionName(verb) {
  const clean = safeText(verb, 120).toLowerCase();
  if (!clean.startsWith(BROWSER_PREFIX)) return clean;
  const action = clean.slice(BROWSER_PREFIX.length);
  if (action === 'open') return 'navigate';
  if (action === 'set_value') return 'type';
  return action;
}

function quotePowerShellLiteral(value) {
  return `'${String(value || '').replace(/'/g, "''")}'`;
}

function mapComputerAction(args = {}) {
  const verb = safeText(args.verb || args.action, 120).toLowerCase();
  const target = safeObject(args.target);
  const actionArgs = {...safeObject(args.arguments || args.actionArgs)};
  if (DIRECT_COMPUTER_ACTIONS.has(verb)) return {action: verb, arguments: actionArgs};
  if (verb.startsWith(COMPUTER_PREFIX)) {
    const direct = verb.slice(COMPUTER_PREFIX.length);
    if (!DIRECT_COMPUTER_ACTIONS.has(direct)) throw Object.assign(new Error(`Unsupported Computer Hands verb: ${verb}`), {status: 400});
    return {action: direct, arguments: actionArgs};
  }
  if (verb === 'app.open') {
    const command = safeText(target.command || target.executable || actionArgs.command, 4000);
    if (!command) throw Object.assign(new Error('app.open requires target.command or target.executable.'), {status: 400});
    return {action: 'process.start', arguments: {command, arguments: safeText(target.arguments || actionArgs.arguments, 32000), workingDirectory: safeText(target.workingDirectory || actionArgs.workingDirectory, 1000)}};
  }
  if (verb === 'media.play') {
    const player = safeText(target.player || actionArgs.player, 4000);
    const mediaPath = safeText(target.path || target.artifactPath || actionArgs.path, 4000);
    if (player) return {action: 'process.start', arguments: {command: player, arguments: safeText(target.arguments || mediaPath, 32000)}};
    if (!mediaPath) throw Object.assign(new Error('media.play requires target.path or target.player.'), {status: 400});
    return {action: 'process.start', arguments: {command: 'powershell.exe', arguments: `-NoProfile -NonInteractive -Command Start-Process -LiteralPath ${quotePowerShellLiteral(mediaPath)}`}};
  }
  if (verb === 'media.stop') {
    const pid = Number(target.pid || actionArgs.pid || 0);
    if (!Number.isInteger(pid) || pid < 1) throw Object.assign(new Error('media.stop requires target.pid.'), {status: 400});
    return {action: 'process.stop', arguments: {pid}};
  }
  throw Object.assign(new Error(`Unsupported Venice computer-body verb: ${verb}`), {status: 400});
}

function browserEpisodeVerifiesAction(observation, actionId) {
  if (!actionId) return false;
  const episodes = Array.isArray(observation && observation.episodes) ? observation.episodes : [];
  return episodes.some((episode) => {
    const outcome = safeText(episode.outcome, 80).toLowerCase();
    const actions = Array.isArray(episode.actions) ? episode.actions : [];
    const matched = actions.some((action) => safeText(action.actionId || action.id, 180) === actionId);
    return matched && ['completed', 'success', 'succeeded', 'verified'].includes(outcome);
  });
}

function browserFallbackAction(args = {}) {
  const verb = safeText(args.verb || args.action, 120).toLowerCase();
  const target = safeObject(args.target);
  if (verb === 'browser.open' || verb === 'browser.navigate') {
    const url = safeText(target.url || args.url, 4000);
    if (!url) return null;
    return {
      kind: 'equivalent_action',
      action: 'process.start',
      arguments: {command: 'powershell.exe', arguments: `-NoProfile -NonInteractive -Command Start-Process ${quotePowerShellLiteral(url)}`},
    };
  }
  return {kind: 'observation_only', action: 'screen.capture', arguments: {maxWidth: 1280, quality: 55}};
}

async function executeHands({admin, user, args, requestIdSuffix, action, actionArgs}) {
  const requestId = stableKey(args.requestId, requestIdSuffix);
  const created = await computerHandsOperationRunOperation({
    admin,
    user,
    operation: 'computer_hands.request.create',
    args: {
      requestId,
      workerId: safeText(args.workerId, 160) || 'windows-hands-01',
      laneId: safeText(args.laneId, 160) || 'lane-venice-body',
      action,
      arguments: actionArgs,
      approved: args.approved === true,
      highRiskApproved: args.highRiskApproved === true,
    },
  });
  let status = null;
  try {
    status = await computerHandsOperationRunOperation({admin, user, operation: 'computer_hands.request.status', args: {ticketId: created.ticketId}});
  } catch (_) {}
  const completed = status && status.status === 'completed' && status.result && status.result.ok !== false;
  return {
    request: created,
    observation: status,
    verified: !!completed,
    state: completed ? 'completed' : safeText(status && status.status || created.status, 80) || 'queued',
  };
}

async function executeBrowser({admin, extra, args}) {
  const requestId = safeText(args.requestId, 130);
  const verb = safeText(args.verb || args.action, 120).toLowerCase();
  const target = safeObject(args.target);
  const intent = safeText(args.intent, 2000) || `Venice browser action: ${verb}`;
  let sessionId = safeText(args.browserSessionId || args.sessionId, 180);
  let session = null;
  if (!sessionId) {
    const created = await runCommandCenterOperation(admin, extra, 'browser_sessions.create', {
      idempotencyKey: stableKey(requestId, 'browser-create'),
      intent,
      startUrl: safeText(target.url || args.startUrl, 1000) || undefined,
      surface: {runtime: 'playwright', browser: 'chromium', mode: 'desktop'},
    });
    session = created.session || null;
    sessionId = safeText(session && session.sessionId, 180);
  }
  if (!sessionId) throw Object.assign(new Error('Browser Nerve did not return a sessionId.'), {status: 502});
  if (verb === 'browser.observe' || verb === 'browser.status') {
    const observation = await runCommandCenterOperation(admin, extra, 'browser_sessions.observe', {sessionId, limit: 10});
    return {sessionId, session, observation, verified: observation && observation.found === true, state: observation && observation.found ? 'observed' : 'not_found'};
  }
  const action = await runCommandCenterOperation(admin, extra, 'browser_sessions.act', {
    idempotencyKey: stableKey(requestId, 'browser-act'),
    sessionId,
    action: browserActionName(verb),
    target,
    value: args.value === undefined ? undefined : String(args.value),
    reason: intent,
  });
  let observation = null;
  let observeError = '';
  try {
    observation = await runCommandCenterOperation(admin, extra, 'browser_sessions.observe', {sessionId, limit: 20});
  } catch (error) {
    observeError = safeText(error && error.message, 1000);
  }
  const actionRecord = action && action.action || null;
  const actionId = safeText(actionRecord && actionRecord.actionId, 180);
  const verified = browserEpisodeVerifiesAction(observation, actionId);
  return {
    sessionId,
    session,
    action: actionRecord,
    observation,
    observeError,
    verified,
    state: verified ? 'completed' : (safeText(actionRecord && actionRecord.status, 80) || 'requested_unverified'),
  };
}

function veniceBodyOperationEntries() {
  return {
    'venice_body.action': {
      summary: 'Route one structured Venice body action. Browser/DOM work prefers Browser Nerve; OS/native/media work uses Computer Hands. Speech is never parsed as commands. Success requires observed evidence; unverified browser requests may fall back to Computer Hands without replacing either lane.',
      write: true,
      requiresRequestId: true,
      requiredScopes: [],
      input: {
        requestId: 'stable id',
        channel: 'auto|browser|computer',
        verb: 'structured action verb such as browser.navigate, browser.click, system.status, window.focus, app.open, media.play',
        target: 'optional structured target',
        arguments: 'optional action arguments',
        value: 'optional browser input value',
        intent: 'plain-language action intent, separate from Venice speech',
        browserSessionId: 'optional existing Browser Nerve session id',
        laneId: 'optional Computer Hands lane id',
        workerId: 'optional Computer Hands worker id',
        fallbackAllowed: 'boolean default true',
        approved: 'boolean for Computer Hands writes',
        highRiskApproved: 'boolean for Computer Hands high-risk writes',
      },
    },
  };
}

async function veniceBodyOperationRunOperation({admin, user, extra, operation, args = {}}) {
  if (operation !== 'venice_body.action') throw Object.assign(new Error('Unsupported Venice body operation.'), {status: 400});
  const verb = safeText(args.verb || args.action, 120).toLowerCase();
  if (!verb) throw Object.assign(new Error('venice_body.action requires verb.'), {status: 400});
  stableKey(args.requestId, 'body');
  const selectedLane = classifyLane(args);
  if (selectedLane === 'computer') {
    const mapped = mapComputerAction(args);
    const hands = await executeHands({admin, user, args, requestIdSuffix: 'hands', action: mapped.action, actionArgs: mapped.arguments});
    return {
      routerVersion: BODY_ROUTER_VERSION,
      requestedVerb: verb,
      selectedLane: 'computer_hands',
      fallbackUsed: false,
      speechTouched: false,
      completed: hands.verified,
      evidence: hands,
    };
  }

  const browser = await executeBrowser({admin, extra, args});
  if (browser.verified || args.fallbackAllowed === false) {
    return {
      routerVersion: BODY_ROUTER_VERSION,
      requestedVerb: verb,
      selectedLane: 'browser_nerve',
      fallbackUsed: false,
      speechTouched: false,
      completed: browser.verified,
      evidence: {browser},
    };
  }

  const fallback = browserFallbackAction(args);
  if (!fallback) {
    return {
      routerVersion: BODY_ROUTER_VERSION,
      requestedVerb: verb,
      selectedLane: 'browser_nerve',
      fallbackUsed: false,
      speechTouched: false,
      completed: false,
      evidence: {browser, boundary: 'Browser action was not verified and no safe Computer Hands fallback is defined.'},
    };
  }
  let hands = null;
  let fallbackError = '';
  try {
    hands = await executeHands({admin, user, args, requestIdSuffix: 'fallback', action: fallback.action, actionArgs: fallback.arguments});
  } catch (error) {
    fallbackError = safeText(error && error.message, 1000);
  }
  const equivalent = fallback.kind === 'equivalent_action';
  return {
    routerVersion: BODY_ROUTER_VERSION,
    requestedVerb: verb,
    selectedLane: 'browser_nerve',
    fallbackUsed: true,
    fallbackLane: 'computer_hands',
    fallbackKind: fallback.kind,
    speechTouched: false,
    completed: equivalent && !!(hands && hands.verified),
    evidence: {browser, hands, fallbackError},
  };
}

module.exports = {
  BODY_ROUTER_VERSION,
  BROWSER_VERBS,
  classifyLane,
  browserActionName,
  mapComputerAction,
  browserEpisodeVerifiesAction,
  browserFallbackAction,
  veniceBodyOperationEntries,
  veniceBodyOperationRunOperation,
};
