export const MAX_SWARM_SLICES = 12;
export const MAX_PARALLEL_WORKERS = 8;
export const HANDOFF_FIELDS = Object.freeze([
  'DURABLE CONTEXT',
  'COMPLETED EVIDENCE',
  'CURRENT SLICE',
  'UNMET ACCEPTANCE',
  'ACTIVE CONSTRAINTS',
  'EXACT NEXT ACTION',
]);

export function newJob(text, campaignContext, fresh = true, source = 'manual', id = '') {
  const commission = String(text || '').trim();
  if (!commission) throw new Error('commission_required');
  return {
    id: id || globalThis.crypto?.randomUUID?.() || `job-${Date.now()}`,
    commission,
    context: String(campaignContext || '').trim(),
    newWorker: fresh !== false,
    source,
    state: 'queued',
    queuedAt: new Date().toISOString(),
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
  return combined.length > maxChars ? combined.slice(combined.length - maxChars) : combined;
}

export function planHandoffContinuation(baseContext, handoffText, id = '') {
  const handoff = parseHandoff(handoffText);
  if (!handoff) return null;
  const context = mergeHandoffContext(baseContext, handoff);
  const job = newJob(handoff['EXACT NEXT ACTION'], context, true, 'handoff', id);
  return Object.freeze({handoff, context, job});
}

function escapeRegex(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
