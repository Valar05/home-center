import { createHash, randomUUID } from 'node:crypto';

export const ROUTES = Object.freeze({
  DIAGNOSE_PHONE: 'diagnose.phone-hands',
  STATUS: 'status.atom',
  THRONE: 'chromium-throne.worker',
  PHONE: 'phone-hands.worker',
  COMPUTER: 'computer-hands.worker',
  GENERAL: 'fortress.worker',
});

const safeText = value => String(value ?? '').trim().replace(/\s+/g, ' ');
const hash = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');

export function classifyCommand(command) {
  const text = safeText(command?.text);
  if (!text) return Object.freeze({ outcome: 'PARK', reasonCode: 'EMPTY_COMMAND', route: null });
  const lower = text.toLowerCase();
  let route = ROUTES.GENERAL;
  let capability = 'fortress.task';
  if (/\b(diagnos|repair|recover|fix)\w*\b/.test(lower) && /\b(phone hands|phone|shizuku|rish|watchdog)\b/.test(lower)) {
    route = ROUTES.DIAGNOSE_PHONE; capability = 'diagnostic.repair';
  } else if (/\b(status|state|health|what(?:'s| is) online)\b/.test(lower)) {
    route = ROUTES.STATUS; capability = 'system.status';
  } else if (/\b(chromium throne|browser|tab|chatgpt|web)\b/.test(lower)) {
    route = ROUTES.THRONE; capability = 'browser.task';
  } else if (/\b(phone hands|android|phone)\b/.test(lower)) {
    route = ROUTES.PHONE; capability = 'phone.task';
  } else if (/\b(computer hands|thecauldron|windows|desktop|laptop)\b/.test(lower)) {
    route = ROUTES.COMPUTER; capability = 'computer.task';
  }
  return Object.freeze({
    outcome: 'ROUTE',
    reasonCode: 'DETERMINISTIC_TEXT_ROUTE',
    route,
    capability,
    requestSha256: hash({ text }),
  });
}

export function makeWorkEnvelope(command, decision) {
  if (decision.outcome !== 'ROUTE') throw new Error('ROUTE_REQUIRED');
  return Object.freeze({
    schema: 'atom.work.v1',
    workId: randomUUID(),
    missionId: command.clientCommandId,
    route: decision.route,
    capability: decision.capability,
    requestedOutcome: safeText(command.text),
    authority: Object.freeze({ humanInitiated: command.humanInitiated === true, source: command.source || 'atom' }),
    constraints: Object.freeze({
      noArbitraryShellFromUserText: true,
      noProviderTerminalRequired: true,
      receiptRequired: true,
      preserveCommission: true,
    }),
    createdAt: new Date().toISOString(),
    requestSha256: decision.requestSha256,
  });
}

export function validateWorkerResult(result, work) {
  if (!result || result.workId !== work.workId) return { ok: false, reasonCode: 'WORK_ID_MISMATCH' };
  if (!['COMPLETE','BLOCKED','FAILED'].includes(result.state)) return { ok: false, reasonCode: 'INVALID_STATE' };
  if (typeof result.summary !== 'string' || !result.summary.trim()) return { ok: false, reasonCode: 'SUMMARY_REQUIRED' };
  return { ok: true };
}
