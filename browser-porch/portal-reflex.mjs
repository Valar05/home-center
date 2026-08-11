import {createHash} from 'node:crypto';

export const REFLEX_VERSION = 'home-center.portal-reflex.v1';

const RECEIPT_SAFE_ACTIONS = new Set([
  'observe',
  'screenshot',
  'click',
  'set_value',
  'select',
  'scroll',
  'route_native',
  'ask',
  'noop',
]);

function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`;
  }
  return JSON.stringify(value);
}

export function sha256(value) {
  return createHash('sha256').update(String(value), 'utf8').digest('hex');
}

function clean(value, max = 300) {
  return String(value ?? '').replace(/\s+/g, ' ').trim().slice(0, max);
}

function quoted(text) {
  return [...text.matchAll(/["“]([^"”]+)["”]/g)].map((match) => clean(match[1]));
}

export function parsePrompt(input) {
  const source = clean(input, 2000);
  const lower = source.toLowerCase();
  const parts = quoted(source);

  if (!source) return {intent: 'ask', reason: 'Prompt is empty.'};
  if (/^(look|observe|status|where am i|what page|read page|refresh dom)\b/.test(lower)) return {intent: 'observe'};
  if (/^(screenshot|take (a )?screenshot|show (me )?(the )?page)\b/.test(lower)) return {intent: 'screenshot', forced: true};
  if (/^(upload|attach|choose file|add file)\b/.test(lower)) return {intent: 'route_native', route: 'computer_hands', reason: 'Native file pickers belong to Computer Hands.'};
  if (/^(submit|send|file (it|appeal)|finish submission)\b/.test(lower)) return {intent: 'ask', reason: 'Submission requires a separately approved exact action.'};
  if (/^(scroll down|down)\b/.test(lower)) return {intent: 'scroll', direction: 'down'};
  if (/^(scroll up|up)\b/.test(lower)) return {intent: 'scroll', direction: 'up'};

  const click = source.match(/^(?:click|press|open)\s+(?:["“]([^"”]+)["”]|(.+))$/i);
  if (click) return {intent: 'click', target: clean(click[1] || click[2])};

  const type = source.match(/^(?:type|enter|put)\s+["“]([^"”]+)["”]\s+(?:in|into)\s+["“]([^"”]+)["”]$/i);
  if (type) return {intent: 'set_value', value: type[1], target: clean(type[2])};

  const choose = source.match(/^(?:choose|select)\s+["“]([^"”]+)["”]\s+(?:in|from)\s+["“]([^"”]+)["”]$/i);
  if (choose) return {intent: 'select', value: clean(choose[1]), target: clean(choose[2])};

  if (parts.length === 1 && /^(click|press|open)\b/.test(lower)) return {intent: 'click', target: parts[0]};
  return {intent: 'ask', reason: 'Prompt does not match the fixed Portal Reflex grammar.'};
}

export function normalizeObservation(input = {}) {
  const elements = Array.isArray(input.semanticElements) ? input.semanticElements.slice(0, 500).map((element, index) => ({
    ref: clean(element?.ref || `element-${index + 1}`, 180),
    role: clean(element?.role || 'unknown', 80).toLowerCase(),
    name: clean(element?.name || element?.text || '', 300),
    disabled: Boolean(element?.disabled),
    visible: element?.visible !== false,
  })) : [];
  const normalized = {
    url: clean(input.url, 2000),
    title: clean(input.title, 500),
    documentId: clean(input.documentId, 180),
    bodyTextLength: Math.max(0, Number(input.bodyTextLength) || 0),
    semanticElements: elements,
    visualSurface: Boolean(input.visualSurface),
    unexpectedDocumentChange: Boolean(input.unexpectedDocumentChange),
    postconditionMismatch: Boolean(input.postconditionMismatch),
  };
  normalized.documentFingerprint = sha256(canonical({
    url: normalized.url,
    title: normalized.title,
    documentId: normalized.documentId,
    elements: elements.map(({role, name, visible, disabled}) => ({role, name, visible, disabled})),
  }));
  return normalized;
}

export function createReflexState() {
  return {
    targetFailures: new Map(),
    screenshotByDocument: new Map(),
    lastDocumentFingerprint: '',
    sequence: 0,
  };
}

function targetKey(intent) {
  return `${intent.intent}:${clean(intent.target).toLowerCase()}`;
}

function resolveTarget(target, elements) {
  const wanted = clean(target).toLowerCase();
  const live = elements.filter((element) => element.visible && !element.disabled && element.name);
  const exact = live.filter((element) => element.name.toLowerCase() === wanted);
  if (exact.length === 1) return {status: 'resolved', element: exact[0], strategy: 'accessible_name_exact'};
  if (exact.length > 1) return {status: 'ambiguous', matches: exact};
  const contains = live.filter((element) => element.name.toLowerCase().includes(wanted));
  if (contains.length === 1) return {status: 'resolved', element: contains[0], strategy: 'accessible_name_contains'};
  if (contains.length > 1) return {status: 'ambiguous', matches: contains};
  return {status: 'missing', matches: []};
}

export function screenshotReason({intent, observation, state, nowMs = Date.now()}) {
  if (intent.intent === 'screenshot' && intent.forced) return 'explicit_request';
  if (observation.unexpectedDocumentChange) return 'unexpected_document_change';
  if (observation.postconditionMismatch) return 'postcondition_mismatch';
  if (observation.visualSurface) return 'visual_surface';
  if (observation.semanticElements.length === 0 && observation.bodyTextLength < 80) return 'dom_sparse';
  if (intent.target && (state.targetFailures.get(targetKey(intent)) || 0) >= 2) return 'target_failed_twice';
  return '';
}

function mayCapture(reason, observation, state, nowMs) {
  if (!reason) return false;
  if (reason === 'explicit_request') return true;
  const last = state.screenshotByDocument.get(observation.documentFingerprint) || 0;
  return nowMs - last >= 10_000;
}

function receipt(plan, intent, observation, state) {
  const material = {
    schema: 'home-center.portal-reflex.receipt.v1',
    reflexVersion: REFLEX_VERSION,
    sequence: ++state.sequence,
    documentFingerprint: observation.documentFingerprint,
    promptIntent: intent.intent,
    action: plan.action,
    targetRef: plan.target?.ref || '',
    targetRole: plan.target?.role || '',
    targetName: plan.target?.name || '',
    valueHash: intent.value == null ? '' : sha256(intent.value),
    screenshotReason: plan.screenshotReason || '',
    requiresApproval: Boolean(plan.requiresApproval),
    expectedPostcondition: plan.expectedPostcondition || '',
    reason: plan.reason || '',
    modelUsed: false,
    networkInferenceUsed: false,
  };
  if (!RECEIPT_SAFE_ACTIONS.has(material.action)) throw new Error(`Unsupported receipt action: ${material.action}`);
  return {...material, receiptSha256: sha256(canonical(material))};
}

export function planPrompt(prompt, observationInput, state = createReflexState(), nowMs = Date.now()) {
  const intent = parsePrompt(prompt);
  const observation = normalizeObservation(observationInput);
  const reason = screenshotReason({intent, observation, state, nowMs});
  let plan;

  if (mayCapture(reason, observation, state, nowMs)) {
    state.screenshotByDocument.set(observation.documentFingerprint, nowMs);
    plan = {action: 'screenshot', screenshotReason: reason, expectedPostcondition: 'Screenshot returned for external visual reorientation; no page mutation.'};
  } else if (intent.intent === 'observe') {
    plan = {action: 'observe', expectedPostcondition: 'Fresh DOM and semantic inventory returned.'};
  } else if (intent.intent === 'route_native') {
    plan = {action: 'route_native', route: intent.route, reason: intent.reason, expectedPostcondition: 'Native lane returns its own verified receipt.'};
  } else if (intent.intent === 'ask') {
    plan = {action: 'ask', reason: intent.reason, requiresApproval: /separately approved/.test(intent.reason), expectedPostcondition: 'No mutation occurs.'};
  } else if (intent.intent === 'scroll') {
    plan = {action: 'scroll', direction: intent.direction, expectedPostcondition: 'Scroll position changes and DOM is re-observed.'};
  } else if (['click', 'set_value', 'select'].includes(intent.intent)) {
    const resolution = resolveTarget(intent.target, observation.semanticElements);
    if (resolution.status === 'resolved') {
      state.targetFailures.delete(targetKey(intent));
      plan = {
        action: intent.intent,
        target: resolution.element,
        locatorStrategy: resolution.strategy,
        value: intent.value,
        expectedPostcondition: intent.intent === 'set_value'
          ? 'Field value hash matches without returning the value.'
          : intent.intent === 'select'
            ? 'Selected option is read back.'
            : 'Target state, URL, title, or semantic fingerprint changes.',
      };
    } else if (resolution.status === 'ambiguous') {
      plan = {action: 'ask', reason: `Target “${intent.target}” matched ${resolution.matches.length} visible controls.`, expectedPostcondition: 'No mutation occurs.'};
    } else {
      const key = targetKey(intent);
      state.targetFailures.set(key, (state.targetFailures.get(key) || 0) + 1);
      plan = {action: 'observe', reason: `Target “${intent.target}” was not found; refresh DOM before visual fallback.`, expectedPostcondition: 'Fresh DOM and semantic inventory returned.'};
    }
  } else {
    plan = {action: 'noop', reason: 'No fixed rule matched.', expectedPostcondition: 'No mutation occurs.'};
  }

  state.lastDocumentFingerprint = observation.documentFingerprint;
  return {...plan, intent, observation, receipt: receipt(plan, intent, observation, state)};
}

