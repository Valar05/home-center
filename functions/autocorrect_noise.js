'use strict';

const {createHash} = require('node:crypto');

const USER_COLLECTION = 'autocorrectNoiseUsers';
const AUDIT_COLLECTION = 'autocorrectNoiseAudit';
const MAX_TEXT_CHARS = 12000;
const MAX_LEXEME_CHARS = 160;
const MAX_CANDIDATES = 16;
const MAX_CONTEXTS = 12;
const MAX_LOOKUPS = 96;
const MAX_WORDS = 4;
const TIER_RANK = {rejected: -1, candidate: 0, good: 1, gold: 2};

function sha(value) {
  return createHash('sha256').update(String(value || ''), 'utf8').digest('hex');
}

function fail(message, status = 400, code = 'autocorrect_noise_invalid_argument') {
  return Object.assign(new Error(message), {status, code});
}

function required(value, max, name) {
  const text = String(value === undefined || value === null ? '' : value).normalize('NFKC').trim();
  if (!text) throw fail(name + ' is required.');
  if (text.length > max) throw fail(name + ' exceeds ' + max + ' characters.');
  return text;
}

function normalizeLexeme(value) {
  return String(value || '').normalize('NFKC').trim().replace(/\s+/gu, ' ').toLowerCase();
}

function wordCount(value) {
  const words = String(value || '').match(/[\p{L}\p{M}\p{N}]+/gu);
  return words ? words.length : 0;
}

function lexeme(value, name) {
  const text = required(value, MAX_LEXEME_CHARS, name);
  const words = wordCount(text);
  if (!words || words > MAX_WORDS) throw fail(name + ' must contain one to four lexical words.');
  if (/[\r\n]/u.test(text)) throw fail(name + ' must not contain line breaks.');
  return text;
}

function authenticatedUserScope(user) {
  const identity = user && (user.uid || user.email);
  if (!identity) throw fail('An authenticated Home Center user is required.', 401, 'autocorrect_noise_auth_required');
  return sha('home-center-autocorrect-noise-v1\n' + String(identity).toLowerCase());
}

function patternId(noisy) {
  return sha('pattern\n' + normalizeLexeme(noisy));
}

function candidateId(intended) {
  return sha('candidate\n' + normalizeLexeme(intended)).slice(0, 32);
}

function auditId(scope, requestId) {
  return sha('audit\n' + scope + '\n' + requestId);
}

function systemShapedToken(value) {
  const text = String(value || '');
  if (/(?:https?:\/\/|www\.|[\/\\@#:]|\.[\p{L}\p{N}]|_[\p{L}\p{N}])/iu.test(text)) return true;
  return /^[A-Z][A-Za-z0-9]*[A-Z][A-Za-z0-9]*$/u.test(text);
}

function tierForCandidate(candidate, total) {
  const observations = Math.max(0, Number(candidate.observations || 0));
  const confirmations = Math.max(0, Number(candidate.explicitConfirmations || 0));
  const rejections = Math.max(0, Number(candidate.rejections || 0));
  const contexts = Array.isArray(candidate.contexts) ? candidate.contexts.length : 0;
  const dominance = total ? observations / total : 0;
  if (rejections > confirmations) return 'rejected';
  if (confirmations > rejections) return 'gold';
  if (observations >= 3 && contexts >= 2 && dominance >= 0.85) return 'gold';
  if (observations >= 2 && dominance >= 0.67) return 'good';
  return 'candidate';
}

function confidence(candidate, total) {
  const positive = Number(candidate.observations || 0) + 2 * Number(candidate.explicitConfirmations || 0);
  const negative = Math.max(0, total - Number(candidate.observations || 0)) + 2 * Number(candidate.rejections || 0);
  return Number((positive / Math.max(1, positive + negative + 1)).toFixed(4));
}

function evidence(candidate) {
  return Number(candidate.observations || 0) + 2 * Number(candidate.explicitConfirmations || 0) - 2 * Number(candidate.rejections || 0);
}

function refreshPattern(pattern) {
  const source = pattern && pattern.candidates && typeof pattern.candidates === 'object' ? pattern.candidates : {};
  const total = Object.values(source).reduce((sum, item) => sum + Math.max(0, Number(item.observations || 0)), 0);
  const candidates = Object.entries(source).map(([id, item]) => {
    const next = {...item, id};
    next.contexts = [...new Set(Array.isArray(next.contexts) ? next.contexts : [])].slice(-MAX_CONTEXTS);
    next.tier = tierForCandidate(next, total);
    next.confidence = confidence(next, total);
    next.dominance = Number((total ? Number(next.observations || 0) / total : 0).toFixed(4));
    return next;
  }).sort((a, b) => {
    const tier = (TIER_RANK[b.tier] || 0) - (TIER_RANK[a.tier] || 0);
    return tier || evidence(b) - evidence(a) || String(a.intendedNormalized).localeCompare(String(b.intendedNormalized));
  }).slice(0, MAX_CANDIDATES);
  const first = candidates[0] || null;
  const second = candidates[1] || null;
  const ambiguous = Boolean(first && second && first.tier !== 'rejected' && second.tier !== 'rejected' && first.tier === second.tier && Math.abs(evidence(first) - evidence(second)) <= 1);
  return {
    ...pattern,
    candidates: Object.fromEntries(candidates.map((item) => {
      const copy = {...item};
      delete copy.id;
      return [item.id, copy];
    })),
    totalObservations: total,
    winner: first && first.tier !== 'rejected' ? {
      candidateId: first.id,
      intended: first.intended,
      intendedNormalized: first.intendedNormalized,
      tier: first.tier,
      confidence: first.confidence,
      dominance: first.dominance,
      observations: Number(first.observations || 0),
      explicitConfirmations: Number(first.explicitConfirmations || 0),
      rejections: Number(first.rejections || 0),
      contextCount: first.contexts.length,
    } : null,
    ambiguous,
  };
}

function publicPattern(pattern) {
  const current = refreshPattern(pattern || {});
  return {
    noisy: current.noisy,
    noisyNormalized: current.noisyNormalized,
    protected: current.protected === true,
    protectedOverride: current.protectedOverride === true,
    intrinsicSystemRisk: current.intrinsicSystemRisk === true,
    totalObservations: current.totalObservations,
    ambiguous: current.ambiguous,
    winner: current.winner,
    candidates: Object.values(current.candidates || {}).map((item) => ({
      intended: item.intended,
      intendedNormalized: item.intendedNormalized,
      tier: item.tier,
      confidence: item.confidence,
      dominance: item.dominance,
      observations: Number(item.observations || 0),
      explicitConfirmations: Number(item.explicitConfirmations || 0),
      rejections: Number(item.rejections || 0),
      contextCount: Array.isArray(item.contexts) ? item.contexts.length : 0,
    })),
    createdAt: current.createdAt || '',
    updatedAt: current.updatedAt || '',
  };
}

function dbFor(admin) {
  if (!admin || typeof admin.firestore !== 'function') throw fail('Firestore is unavailable.', 503, 'autocorrect_noise_firestore_unavailable');
  return admin.firestore();
}

function patternRef(db, scope, noisy) {
  return db.collection(USER_COLLECTION).doc(scope).collection('patterns').doc(patternId(noisy));
}

function auditRef(db, scope, requestId) {
  return db.collection(AUDIT_COLLECTION).doc(auditId(scope, requestId));
}

function requestId(args) {
  return required(args && args.requestId, 180, 'requestId');
}

function contextHash(args) {
  return sha('context\n' + String(args.contextId || args.contextKind || 'unspecified').slice(0, 500));
}

async function observeOperation({admin, user, args = {}}) {
  const rid = requestId(args);
  const noisy = lexeme(args.noisy, 'noisy');
  const intended = lexeme(args.intended, 'intended');
  const noisyNormalized = normalizeLexeme(noisy);
  const intendedNormalized = normalizeLexeme(intended);
  if (noisyNormalized === intendedNormalized) throw fail('noisy and intended normalize to the same value.');
  const scope = authenticatedUserScope(user);
  const db = dbFor(admin);
  const pRef = patternRef(db, scope, noisyNormalized);
  const aRef = auditRef(db, scope, rid);
  const ctx = contextHash(args);
  const now = new Date().toISOString();
  return db.runTransaction(async (tx) => {
    const priorAudit = await tx.get(aRef);
    if (priorAudit.exists) return {...priorAudit.data().result, idempotent: true};
    const snap = await tx.get(pRef);
    const prior = snap.exists ? snap.data() : {
      schema: 'home-center.autocorrect-noise.pattern.v1',
      noisy,
      noisyNormalized,
      candidates: {},
      protected: false,
      protectedOverride: false,
      intrinsicSystemRisk: systemShapedToken(noisy),
      createdAt: now,
    };
    const id = candidateId(intendedNormalized);
    const old = prior.candidates && prior.candidates[id] || {
      intended,
      intendedNormalized,
      observations: 0,
      explicitConfirmations: 0,
      rejections: 0,
      contexts: [],
      firstObservedAt: now,
    };
    const updated = refreshPattern({
      ...prior,
      noisy,
      noisyNormalized,
      candidates: {
        ...(prior.candidates || {}),
        [id]: {
          ...old,
          intended,
          intendedNormalized,
          observations: Number(old.observations || 0) + 1,
          explicitConfirmations: Number(old.explicitConfirmations || 0) + (args.explicit === true ? 1 : 0),
          contexts: [...new Set([...(old.contexts || []), ctx])].slice(-MAX_CONTEXTS),
          lastObservedAt: now,
        },
      },
      updatedAt: now,
    });
    const result = {schema: 'home-center.autocorrect-noise.observation.v1', requestId: rid, userScoped: true, rawContextStored: false, pattern: publicPattern(updated), idempotent: false};
    tx.set(pRef, updated);
    tx.set(aRef, {schema: 'home-center.autocorrect-noise.audit.v1', requestId: rid, scopeHash: scope, operation: 'autocorrect_noise.observe', patternHash: patternId(noisyNormalized), contextFingerprint: ctx, createdAt: now, result});
    return result;
  });
}

async function feedbackOperation({admin, user, args = {}}) {
  const rid = requestId(args);
  const noisy = lexeme(args.noisy, 'noisy');
  const normalized = normalizeLexeme(noisy);
  const verdict = required(args.verdict, 40, 'verdict').toLowerCase();
  if (!new Set(['confirm', 'reject', 'protect', 'unprotect', 'allow_auto', 'forget']).has(verdict)) throw fail('Unsupported feedback verdict.');
  const intended = ['confirm', 'reject'].includes(verdict) ? lexeme(args.intended, 'intended') : '';
  const scope = authenticatedUserScope(user);
  const db = dbFor(admin);
  const pRef = patternRef(db, scope, normalized);
  const aRef = auditRef(db, scope, rid);
  const now = new Date().toISOString();
  return db.runTransaction(async (tx) => {
    const priorAudit = await tx.get(aRef);
    if (priorAudit.exists) return {...priorAudit.data().result, idempotent: true};
    const snap = await tx.get(pRef);
    if (!snap.exists) throw fail('No user-scoped pattern exists for noisy.', 404, 'autocorrect_noise_pattern_not_found');
    const prior = snap.data();
    let result;
    if (verdict === 'forget') {
      tx.delete(pRef);
      result = {schema: 'home-center.autocorrect-noise.feedback.v1', requestId: rid, verdict, userScoped: true, forgotten: true, patternHash: patternId(normalized), idempotent: false};
    } else {
      const next = {...prior, updatedAt: now};
      if (verdict === 'protect') next.protected = true;
      if (verdict === 'unprotect') next.protected = false;
      if (verdict === 'allow_auto') {
        next.protected = false;
        next.protectedOverride = true;
      }
      if (verdict === 'confirm' || verdict === 'reject') {
        const id = candidateId(intended);
        const old = prior.candidates && prior.candidates[id];
        if (!old) throw fail('The intended candidate does not exist.', 404, 'autocorrect_noise_candidate_not_found');
        next.candidates = {...prior.candidates, [id]: {...old,
          explicitConfirmations: Number(old.explicitConfirmations || 0) + (verdict === 'confirm' ? 1 : 0),
          rejections: Number(old.rejections || 0) + (verdict === 'reject' ? 1 : 0),
          lastFeedbackAt: now,
        }};
      }
      const updated = refreshPattern(next);
      tx.set(pRef, updated);
      result = {schema: 'home-center.autocorrect-noise.feedback.v1', requestId: rid, verdict, userScoped: true, forgotten: false, pattern: publicPattern(updated), idempotent: false};
    }
    tx.set(aRef, {schema: 'home-center.autocorrect-noise.audit.v1', requestId: rid, scopeHash: scope, operation: 'autocorrect_noise.feedback', verdict, patternHash: patternId(normalized), createdAt: now, result});
    return result;
  });
}

function segmentText(text) {
  const parts = String(text || '').match(/[\p{L}\p{M}\p{N}'’_-]+|\s+|[^\p{L}\p{M}\p{N}'’_\-\s]+/gu) || [];
  return parts.map((raw) => ({raw, kind: /^\s+$/u.test(raw) ? 'space' : (/^[\p{L}\p{M}\p{N}'’_-]+$/u.test(raw) ? 'word' : 'punct')}));
}

function candidateSpans(text, segments) {
  const spans = [];
  let offset = 0;
  const offsets = segments.map((part) => {
    const start = offset;
    offset += part.raw.length;
    return {start, end: offset};
  });
  for (let start = 0; start < segments.length; start += 1) {
    if (segments[start].kind !== 'word') continue;
    let words = 0;
    for (let end = start; end < segments.length && words < MAX_WORDS; end += 1) {
      if (segments[end].kind === 'punct') break;
      if (segments[end].kind === 'word') words += 1;
      if (segments[end].kind !== 'word') continue;
      const raw = segments.slice(start, end + 1).map((item) => item.raw).join('');
      const before = offsets[start].start > 0 ? text[offsets[start].start - 1] : '';
      const after = offsets[end].end < text.length ? text[offsets[end].end] : '';
      spans.push({start, end, words, raw, normalized: normalizeLexeme(raw), systemAdjacent: /[.\/\\@#:_]/u.test(before) || /[.\/\\@#:_]/u.test(after)});
      if (spans.length >= MAX_LOOKUPS) return spans;
    }
  }
  return spans;
}

function copyCase(source, intended) {
  if (source && source === source.toUpperCase()) return intended.toUpperCase();
  if (/^\p{Lu}/u.test(source)) return intended.charAt(0).toUpperCase() + intended.slice(1);
  return intended;
}

function decision(span, record) {
  const pattern = refreshPattern(record || {});
  const winner = pattern.winner;
  const blockedReason = pattern.protected === true ? 'protected_by_user'
    : ((pattern.intrinsicSystemRisk === true || span.systemAdjacent || systemShapedToken(span.raw)) && pattern.protectedOverride !== true ? 'system_shaped_token'
      : (pattern.ambiguous === true ? 'conflicting_patterns' : ''));
  return {...span, winner, tier: winner ? winner.tier : 'candidate', blockedReason, actionable: Boolean(winner && !blockedReason && ['gold', 'good'].includes(winner.tier))};
}

function apply(segments, decisions, includeGood) {
  const candidates = decisions.filter((item) => item.actionable && (item.tier === 'gold' || includeGood)).sort((a, b) => b.words - a.words || a.start - b.start);
  const occupied = new Set();
  const chosen = new Map();
  for (const item of candidates) {
    let overlap = false;
    for (let index = item.start; index <= item.end; index += 1) if (occupied.has(index)) overlap = true;
    if (overlap) continue;
    for (let index = item.start; index <= item.end; index += 1) occupied.add(index);
    chosen.set(item.start, item);
  }
  let output = '';
  for (let index = 0; index < segments.length; index += 1) {
    const item = chosen.get(index);
    if (item) {
      output += copyCase(item.raw, item.winner.intended);
      index = item.end;
    } else if (!occupied.has(index)) output += segments[index].raw;
  }
  return output;
}

function planResolution(text, records = {}, applyGold = false) {
  const originalText = String(text || '');
  const segments = segmentText(originalText);
  const decisions = candidateSpans(originalText, segments).filter((span) => records[span.normalized]).map((span) => decision(span, records[span.normalized]));
  return {
    originalText,
    goldAppliedText: applyGold ? apply(segments, decisions, false) : originalText,
    reviewText: apply(segments, decisions, true),
    decisions: decisions.map((item) => ({
      source: item.raw,
      sourceNormalized: item.normalized,
      intended: item.winner && item.winner.intended || '',
      tier: item.tier,
      confidence: item.winner && item.winner.confidence || 0,
      observations: item.winner && item.winner.observations || 0,
      explicitConfirmations: item.winner && item.winner.explicitConfirmations || 0,
      contextCount: item.winner && item.winner.contextCount || 0,
      blockedReason: item.blockedReason,
      action: item.blockedReason ? 'preserve' : (item.tier === 'gold' ? (applyGold ? 'apply_gold' : 'offer_gold') : (item.tier === 'good' ? 'suggest_good' : 'preserve')),
    })),
  };
}

async function resolveOperation({admin, user, args = {}}) {
  const text = String(args.text === undefined || args.text === null ? '' : args.text);
  if (!text) throw fail('text is required.');
  if (text.length > MAX_TEXT_CHARS) throw fail('text exceeds ' + MAX_TEXT_CHARS + ' characters.');
  const scope = authenticatedUserScope(user);
  const db = dbFor(admin);
  const normalized = [...new Set(candidateSpans(text, segmentText(text)).map((item) => item.normalized))].slice(0, MAX_LOOKUPS);
  const refs = normalized.map((item) => patternRef(db, scope, item));
  const snapshots = refs.length ? (typeof db.getAll === 'function' ? await db.getAll(...refs) : await Promise.all(refs.map((ref) => ref.get()))) : [];
  const records = {};
  snapshots.forEach((snap, index) => {
    if (snap.exists) records[normalized[index]] = snap.data();
  });
  return {schema: 'home-center.autocorrect-noise.resolution.v1', userScoped: true, applyGoldRequested: args.applyGold === true, goodIsAdvisoryOnly: true, rawContextStored: false, ...planResolution(text, records, args.applyGold === true)};
}

async function profileOperation({admin, user, args = {}}) {
  const scope = authenticatedUserScope(user);
  const db = dbFor(admin);
  const limit = Math.max(1, Math.min(100, Number(args.limit || 50)));
  const wanted = args.tier ? required(args.tier, 20, 'tier').toLowerCase() : '';
  if (wanted && !new Set(['candidate', 'good', 'gold', 'rejected']).has(wanted)) throw fail('Unsupported tier.');
  const snapshot = await db.collection(USER_COLLECTION).doc(scope).collection('patterns').orderBy('updatedAt', 'desc').limit(limit).get();
  const patterns = snapshot.docs.map((doc) => publicPattern(doc.data())).filter((item) => !wanted || item.winner && item.winner.tier === wanted);
  return {schema: 'home-center.autocorrect-noise.profile.v1', userScoped: true, rawContextStored: false, count: patterns.length, patterns};
}

function autocorrectNoiseOperationEntries() {
  return {
    'autocorrect_noise.observe': {summary: 'Record one authenticated-user correction observation and update candidate/good/gold evidence without storing raw message context.', write: true, requiresRequestId: true, input: {noisy: 'one to four lexical words', intended: 'one to four lexical words', explicit: 'optional boolean', contextId: 'optional value hashed before storage', requestId: 'string'}},
    'autocorrect_noise.resolve': {summary: 'Resolve text against only the authenticated user profile; preserve original text, auto-apply only eligible gold when explicitly requested, and keep good advisory.', write: false, input: {text: 'string', applyGold: 'optional boolean default false'}},
    'autocorrect_noise.feedback': {summary: 'Confirm, reject, protect, unprotect, explicitly allow automatic use, or forget one authenticated-user correction pattern.', write: true, requiresRequestId: true, input: {noisy: 'one to four lexical words', intended: 'required for confirm/reject', verdict: 'confirm|reject|protect|unprotect|allow_auto|forget', requestId: 'string'}},
    'autocorrect_noise.profile': {summary: 'Inspect the authenticated user autocorrect-noise profile and its candidate/good/gold evidence.', write: false, input: {tier: 'optional candidate|good|gold|rejected', limit: 'optional 1-100'}},
  };
}

async function autocorrectNoiseOperationRunOperation({admin, user, operation, args = {}}) {
  if (operation === 'autocorrect_noise.observe') return observeOperation({admin, user, args});
  if (operation === 'autocorrect_noise.resolve') return resolveOperation({admin, user, args});
  if (operation === 'autocorrect_noise.feedback') return feedbackOperation({admin, user, args});
  if (operation === 'autocorrect_noise.profile') return profileOperation({admin, user, args});
  throw fail('Unsupported autocorrect-noise operation: ' + operation, 400, 'autocorrect_noise_unsupported_operation');
}

module.exports = {
  USER_COLLECTION,
  AUDIT_COLLECTION,
  autocorrectNoiseOperationEntries,
  autocorrectNoiseOperationRunOperation,
  authenticatedUserScope,
  normalizeLexeme,
  systemShapedToken,
  tierForCandidate,
  refreshPattern,
  segmentText,
  candidateSpans,
  copyCase,
  planResolution,
};
