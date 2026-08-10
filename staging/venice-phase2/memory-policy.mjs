import { makeMemoryRecord } from './schema.mjs';

const ALLOWED_TYPES = new Set([
  'stable_fact', 'preference', 'decision', 'commitment', 'correction',
  'open_loop', 'relationship_fact', 'project_fact', 'episodic_note',
]);

function clean(value, label) {
  const text = String(value ?? '').trim();
  if (!text) throw new TypeError(`${label} is required.`);
  return text;
}

function inferType(scopeKind, requested) {
  const type = String(requested || '').trim();
  if (type) {
    if (!ALLOWED_TYPES.has(type)) throw new TypeError(`Unsupported durable memory type: ${type}`);
    return type;
  }
  return scopeKind === 'project' ? 'project_fact' : 'stable_fact';
}

export function promoteMemoryInput(input = {}, context = {}) {
  const scopeKind = input.scope === 'project' ? 'project' : 'global';
  const scope = { kind: scopeKind };
  if (scopeKind === 'project') scope.id = clean(input.scopeId || context.projectId, 'project memory scope id');
  const source = String(input.source || context.source || 'user').toLowerCase();
  const userAuthored = source === 'user' || source === 'drew' || context.promotedBy === 'drew';
  const promotedBy = userAuthored ? 'drew' : 'venice_rule';
  const key = clean(input.key, 'memory key').slice(0, 160);
  const value = typeof input.value === 'string' ? clean(input.value, 'memory value').slice(0, 8000) : input.value;
  const sourceRefs = [...new Set([
    ...(Array.isArray(context.sourceRefs) ? context.sourceRefs : []),
    context.jobId ? `job:${context.jobId}` : '',
    context.threadId ? `thread:${context.threadId}` : '',
    context.projectId ? `project:${context.projectId}` : '',
    userAuthored ? 'workstation:manual-memory' : 'workstation:venice-remember',
  ].filter(Boolean))];

  return makeMemoryRecord({
    type: inferType(scopeKind, input.type),
    scope,
    key,
    value,
    promotedBy,
    sourceRefs,
    confidence: userAuthored ? 1 : 0.75,
    authorityRank: userAuthored ? 100 : 40,
    status: 'active',
  });
}

export function memoryRecordView(record) {
  if (!record) return null;
  return {
    id: record.memoryId,
    memoryId: record.memoryId,
    scope: record.scope?.kind || 'global',
    scopeId: record.scope?.id || null,
    key: record.key || record.type,
    value: typeof record.value === 'string' ? record.value : JSON.stringify(record.value),
    source: record.promotedBy,
    type: record.type,
    status: record.status,
    confidence: record.confidence,
    authorityRank: record.authorityRank,
    promotedAt: record.promotedAt,
    sourceRefs: record.sourceRefs || [],
  };
}

export function memoryRecordText(record) {
  const view = memoryRecordView(record);
  if (!view) return '';
  const scope = view.scope === 'project' ? `project:${view.scopeId}` : 'global';
  return `[${view.type}; ${scope}; authority=${view.authorityRank}] ${view.key}: ${view.value}`;
}
