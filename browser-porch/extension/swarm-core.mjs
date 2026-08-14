export const MAX_SWARM_SLICES = 12;
export const MAX_PARALLEL_WORKERS = 1;
export const WORKER_REASONING_MODE = 'Pro reasoning';
// Stable compatibility wire ID. Primary semantics: direct ChatGPT Judgment-Jar Venice.
export const VENICE_REVIEW_MODE = 'judgment_jar_emulation';
export const HANDOFF_FIELDS = Object.freeze([
  'DURABLE CONTEXT',
  'COMPLETED EVIDENCE',
  'CURRENT SLICE',
  'UNMET ACCEPTANCE',
  'ACTIVE CONSTRAINTS',
  'EXACT NEXT ACTION',
]);

export const WORKER_DOCTRINE = Object.freeze({
  reasoningMode: WORKER_REASONING_MODE,
  singlePersistentProWorker: true,
  veniceReviewMode: VENICE_REVIEW_MODE,
  veniceReviewSemantics: 'primary-judgment-jar',
  planGate: 'PLAN_ALLOWED',
  stopGate: 'STOP_ALLOWED',
  continueDirective: 'CONTINUE_REQUIRED',
  haltDirective: 'HALT_REQUIRED',
  localVeniceRequired: false,
  responseBoundaryIsStop: false,
  phoneSovereign: true,
  phoneControlFromProWorker: false,
  harrowayConsultationRequired: true,
  sheRawMotivationRequired: true,
  narratedContinuationForbidden: true,
  competenceInvocationIndependent: true,
  mvpBeforeEmpire: true,
  oneActiveCriticalPath: true,
  contextBudgetIsOperationalResource: true,
  promiseInflationForbidden: true,
});

export function newJob(text, campaignContext, fresh = false, source = 'manual', id = '') {
  const commission = String(text || '').trim();
  if (!commission) throw new Error('commission_required');
  const explicitRecovery = source === 'explicit-recovery';
  return {
    id: id || globalThis.crypto?.randomUUID?.() || `job-${Date.now()}`,
    commission,
    context: String(campaignContext || '').trim(),
    newWorker: explicitRecovery && fresh === true,
    source,
    state: 'queued',
    queuedAt: new Date().toISOString(),
    workerDoctrine: WORKER_DOCTRINE,
  };
}

export function parallelBatch(queue, limit = MAX_PARALLEL_WORKERS) {
  const bounded = Math.max(1, Math.min(MAX_PARALLEL_WORKERS, Number(limit) || MAX_PARALLEL_WORKERS));
  return (queue || []).filter((job) => job?.state === 'queued').slice(0, bounded);
}

export function parseHandoff(text) {
  const source = String(text || '');
  const values = {};
  let cursor = 0;
  for (const field of HANDOFF_FIELDS) {
    const tail = source.slice(cursor);
    const pattern = new RegExp(`(?:^|\\n)\\s*(?:#{1,6}\\s*)?${escapeRegex(field)}\\s*:?\\s*\\n?`, 'i');
    const match = pattern.exec(tail);
    if (!match) return null;
    const bodyStart = cursor + match.index + match[0].length;
    const nextIndex = HANDOFF_FIELDS.indexOf(field) + 1;
    let bodyEnd = source.length;
    if (nextIndex < HANDOFF_FIELDS.length) {
      const nextField = HANDOFF_FIELDS[nextIndex];
      const nextTail = source.slice(bodyStart);
      const nextPattern = new RegExp(`(?:^|\\n)\\s*(?:#{1,6}\\s*)?${escapeRegex(nextField)}\\s*:?\\s*\\n?`, 'i');
      const next = nextPattern.exec(nextTail);
      if (!next) return null;
      bodyEnd = bodyStart + next.index;
    }
    const value = source.slice(bodyStart, bodyEnd).trim();
    if (!value) return null;
    values[field] = value;
    cursor = bodyEnd;
  }
  return Object.keys(values).length === HANDOFF_FIELDS.length ? Object.freeze(values) : null;
}

export function mergeHandoffContext(base, handoff, maxChars = 24000) {
  if (!handoff || !HANDOFF_FIELDS.every((field) => String(handoff[field] || '').trim())) throw new Error('complete_handoff_required');
  const packet = HANDOFF_FIELDS.slice(0, 5).map((field) => `${field}: ${handoff[field]}`).join('\n');
  const combined = `${String(base || '').trim()}\n\nLATEST WORKER HANDOFF:\n${packet}`.trim();
  return tailBound(combined, maxChars);
}

export function planHandoffContinuation(baseContext, handoffText, id = '') {
  const handoff = parseHandoff(handoffText);
  if (!handoff) return null;
  const context = mergeHandoffContext(baseContext, handoff);
  const job = newJob(handoff['EXACT NEXT ACTION'], context, false, 'handoff', id);
  return Object.freeze({handoff, context, job});
}

export function parseVeniceDirective(text) {
  const source = String(text || '');
  const matches = [...source.matchAll(/(?:^|\n)\s*DIRECTIVE\s*:\s*(STOP_ALLOWED|CONTINUE_REQUIRED|HALT_REQUIRED)\b/gi)];
  return matches.length ? String(matches.at(-1)[1]).toUpperCase() : null;
}

export function mergeCheckpointContext(baseContext, checkpointText, maxChars = 24000) {
  const checkpoint = String(checkpointText || '').trim();
  const combined = `${String(baseContext || '').trim()}\n\nLATEST WORKER CHECKPOINT:\n${checkpoint}`.trim();
  return tailBound(combined, maxChars);
}

export function planVeniceContinuation(baseContext, checkpointText, id = '') {
  const directive = parseVeniceDirective(checkpointText);
  if (directive === 'STOP_ALLOWED' || directive === 'HALT_REQUIRED') return Object.freeze({directive, job: null, context: mergeCheckpointContext(baseContext, checkpointText)});

  const context = mergeCheckpointContext(baseContext, checkpointText);
  const commission = directive === 'CONTINUE_REQUIRED'
    ? 'Continue the SAME bounded commissioned slice in this same Pro worker conversation. Apply Venice Judgment-Jar findings from the latest checkpoint, validate the repair, invoke Venice Judgment Jars again, and do not stop unless the fresh directive is STOP_ALLOWED or a true HALT_REQUIRED boundary exists. If you can name the next callable action, take it now instead of narrating it. She-Raw should creatively roast any evasive or brittle reasoning, but the insult must drive a real repair action.'
    : 'The prior worker ended without a valid Venice completion directive. In this same Pro worker conversation, first execute Venice\'s applicable Judgment Jars over the latest checkpoint. If Venice returns CONTINUE_REQUIRED, continue the SAME bounded commissioned slice immediately, validate, and ask Venice again. Only STOP_ALLOWED permits normal stopping; HALT_REQUIRED stops mutation at the exact hard boundary. Do not unlock or puppet the phone; consume phone-local Home Center/tmux receipts. If you merely narrate the next action, She-Raw should roast that failure and force the action through the authorized lane.';
  const job = newJob(commission, context, false, directive === 'CONTINUE_REQUIRED' ? 'venice-continue' : 'venice-missing-review', id);
  return Object.freeze({directive: directive || 'MISSING', context, job});
}

function tailBound(value, maxChars) {
  const text = String(value || '');
  return text.length > maxChars ? text.slice(text.length - maxChars) : text;
}

function escapeRegex(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
