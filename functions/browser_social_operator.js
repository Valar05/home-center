'use strict';

const {createHash} = require('node:crypto');

const SOCIAL_SCHEMA_VERSION = 'home-center.browser-social-job.v1';
const SOCIAL_COLLECTIONS = Object.freeze({
  jobs: 'browserSocialJobs',
  watches: 'browserSocialWatches',
});
const SOCIAL_MAX_STEPS = 32;
const SOCIAL_ALLOWED_ACTIONS = Object.freeze(['navigate', 'observe', 'find', 'read', 'click', 'type', 'select', 'submit', 'scroll', 'wait_for']);
const SOCIAL_READ_ONLY_ACTIONS = new Set(['navigate', 'observe', 'find', 'read', 'click', 'scroll', 'wait_for']);
const SOCIAL_TERMINAL_STATES = new Set([
  'OBSERVED',
  'VERIFIED_PUBLISHED',
  'VERIFIED_REPLIES_RETURNED',
  'VERIFIED_NO_NEW_REPLIES',
  'BLOCKED',
  'BLOCKED_BOUNDARY',
  'UNKNOWN',
]);
const PRIVATE_PATH_PREFIXES = Object.freeze([
  '/messages', '/message', '/messaging', '/inbox', '/direct', '/dm', '/i/chat', '/settings', '/account', '/admin', '/billing', '/payments', '/ads/manager',
]);

function safeText(value, max = 2000) {
  const text = value == null ? '' : String(value).trim();
  return text.length > max ? text.slice(0, max) : text;
}
function safeObject(value) { return value && typeof value === 'object' && !Array.isArray(value) ? value : {}; }
function hash(value) { return createHash('sha256').update(String(value || '')).digest('hex'); }
function safeId(value, label = 'id') {
  const text = safeText(value, 180);
  if (!/^[A-Za-z0-9_.:-]{6,180}$/.test(text)) throw Object.assign(new Error(`${label} must be 6-180 safe identifier characters.`), {status: 400, failureKind: 'browser_social_invalid_id'});
  return text;
}
function normalizeText(value) { return safeText(value, 12000).toLowerCase().replace(/\s+/g, ' ').trim(); }
function socialOwner(user, ownerKey) {
  const email = safeText(user && user.email, 320).toLowerCase();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) throw Object.assign(new Error('Authenticated owner email is required.'), {status: 401, failureKind: 'browser_social_owner_required'});
  return {email, owner: ownerKey(email)};
}
function isPrivateHost(hostname) {
  const host = String(hostname || '').toLowerCase();
  if (!host || host === 'localhost' || host.endsWith('.localhost') || host.endsWith('.local')) return true;
  if (/^(127\.|0\.|10\.|192\.168\.|169\.254\.)/.test(host)) return true;
  const match = host.match(/^172\.(\d+)\./);
  if (match && Number(match[1]) >= 16 && Number(match[1]) <= 31) return true;
  if (host === '::1' || host.startsWith('fc') || host.startsWith('fd') || host.startsWith('fe80:')) return true;
  return false;
}
function cleanSocialUrl(value, label = 'url') {
  let url;
  try { url = new URL(safeText(value, 1000)); } catch { throw Object.assign(new Error(`${label} must be a valid public http/https URL.`), {status: 400, failureKind: 'browser_social_invalid_url'}); }
  if (url.protocol !== 'https:' || isPrivateHost(url.hostname)) throw Object.assign(new Error(`${label} must be a public https URL.`), {status: 400, failureKind: 'browser_social_private_url'});
  return url;
}
function hasPrivatePath(url) {
  const path = url.pathname.toLowerCase().replace(/\/+$/, '') || '/';
  return PRIVATE_PATH_PREFIXES.some((prefix) => path === prefix || path.startsWith(`${prefix}/`));
}
function cleanAllowedOrigins(startUrl, value) {
  const origins = new Set([startUrl.origin]);
  for (const candidate of Array.isArray(value) ? value.slice(0, 4) : []) origins.add(cleanSocialUrl(candidate, 'allowedOrigins entry').origin);
  return [...origins];
}
function assertAllowedUrl(value, allowedOrigins, label = 'url') {
  const url = cleanSocialUrl(value, label);
  if (!allowedOrigins.includes(url.origin)) throw Object.assign(new Error(`${label} crossed outside the explicitly allowed social origins.`), {status: 400, failureKind: 'browser_social_origin_forbidden'});
  if (hasPrivatePath(url)) throw Object.assign(new Error(`${label} entered a private inbox/account surface forbidden to the public social operator.`), {status: 400, failureKind: 'browser_social_private_surface'});
  return url;
}
function cleanTarget(value = {}) {
  const target = safeObject(value);
  if (Array.isArray(target.coordinates) || Array.isArray(target.bounds) || target.selectorPolicy === 'pixel_coordinates') {
    throw Object.assign(new Error('Social workflows require semantic targets; pixel-coordinate targeting is forbidden.'), {status: 400, failureKind: 'browser_social_coordinate_target_forbidden'});
  }
  return target;
}
function cleanCaptureName(value) {
  const name = safeText(value, 80);
  if (!name) return '';
  if (!/^[a-z][a-z0-9_.-]{0,79}$/.test(name)) throw Object.assign(new Error('captureAs must be a lower-case semantic identifier.'), {status: 400, failureKind: 'browser_social_capture_invalid'});
  return name;
}
function cleanSocialStep(value, index, kind, allowedOrigins, startUrl) {
  const raw = safeObject(value);
  const action = safeText(raw.action, 80).toLowerCase();
  if (!SOCIAL_ALLOWED_ACTIONS.includes(action)) throw Object.assign(new Error(`Unsupported social workflow action: ${action || '[missing]'}.`), {status: 400, failureKind: 'browser_social_action_unsupported'});
  if (kind !== 'publish' && !SOCIAL_READ_ONLY_ACTIONS.has(action)) throw Object.assign(new Error(`${kind} workflows cannot type, select, or submit.`), {status: 400, failureKind: 'browser_social_write_forbidden'});
  const stepId = safeId(raw.stepId || `social-step-${String(index + 1).padStart(2, '0')}`, 'stepId');
  const target = cleanTarget(raw.target);
  if (action === 'navigate') {
    const source = safeText(target.urlSource, 40);
    if (source === 'startUrl') target.url = startUrl.toString();
    if (!target.url) throw Object.assign(new Error('navigate requires target.url or target.urlSource=startUrl.'), {status: 400, failureKind: 'browser_social_navigation_target_required'});
    target.url = assertAllowedUrl(target.url, allowedOrigins, 'navigate target').toString();
  }
  const valueSource = safeText(raw.valueSource, 40);
  if (action === 'type') {
    if (kind !== 'publish' || valueSource !== 'content') throw Object.assign(new Error('The only permitted social type action must source the explicitly commissioned public post content.'), {status: 400, failureKind: 'browser_social_type_source_forbidden'});
  } else if (valueSource || raw.value != null) {
    throw Object.assign(new Error('Literal or indirect step values are forbidden outside the commissioned content type step.'), {status: 400, failureKind: 'browser_social_literal_value_forbidden'});
  }
  const mutation = raw.mutation === 'publish';
  if (mutation && kind !== 'publish') throw Object.assign(new Error('Only publish jobs may declare a publish mutation.'), {status: 400, failureKind: 'browser_social_mutation_forbidden'});
  if (mutation && !['click', 'submit'].includes(action)) throw Object.assign(new Error('The publish mutation step must be a semantic click or submit.'), {status: 400, failureKind: 'browser_social_mutation_action_invalid'});
  return {stepId, action, target, valueSource, captureAs: cleanCaptureName(raw.captureAs), mutation};
}
function cleanSocialWorkflow(kind, value, {startUrl, allowedOrigins}) {
  const raw = Array.isArray(value) ? value : [];
  const source = kind === 'recon' && !raw.length ? [
    {stepId: 'social-recon-navigate', action: 'navigate', target: {urlSource: 'startUrl'}},
    {stepId: 'social-recon-observe', action: 'observe', captureAs: 'recon'},
  ] : raw;
  if (!source.length || source.length > SOCIAL_MAX_STEPS) throw Object.assign(new Error(`Social workflow must contain 1-${SOCIAL_MAX_STEPS} steps.`), {status: 400, failureKind: 'browser_social_step_count_invalid'});
  const steps = source.map((step, index) => cleanSocialStep(step, index, kind, allowedOrigins, startUrl));
  const captures = new Map();
  steps.forEach((step, index) => { if (step.captureAs) captures.set(step.captureAs, index); });
  if (kind === 'publish') {
    const typeIndexes = steps.map((step, index) => step.action === 'type' ? index : -1).filter((index) => index >= 0);
    const mutationIndexes = steps.map((step, index) => step.mutation ? index : -1).filter((index) => index >= 0);
    if (typeIndexes.length !== 1) throw Object.assign(new Error('Publish workflow requires exactly one type step sourced from content.'), {status: 400, failureKind: 'browser_social_content_step_invalid'});
    if (mutationIndexes.length !== 1) throw Object.assign(new Error('Publish workflow requires exactly one step marked mutation=publish.'), {status: 400, failureKind: 'browser_social_publish_step_invalid'});
    const mutationIndex = mutationIndexes[0];
    if (typeIndexes[0] >= mutationIndex) throw Object.assign(new Error('Content must be typed before the publish mutation.'), {status: 400, failureKind: 'browser_social_publish_order_invalid'});
    for (const required of ['account', 'post', 'permalink']) {
      if (!captures.has(required)) throw Object.assign(new Error(`Publish workflow requires a ${required} capture.`), {status: 400, failureKind: 'browser_social_publish_capture_missing'});
    }
    if (captures.get('account') >= mutationIndex) throw Object.assign(new Error('Account identity must be captured before publication.'), {status: 400, failureKind: 'browser_social_account_capture_late'});
    if (captures.get('post') <= mutationIndex || captures.get('permalink') <= mutationIndex) throw Object.assign(new Error('Post and permalink evidence must be captured after publication.'), {status: 400, failureKind: 'browser_social_publish_proof_early'});
  }
  if (kind === 'replies' && !captures.has('replies')) throw Object.assign(new Error('Reply workflow requires a replies capture.'), {status: 400, failureKind: 'browser_social_replies_capture_missing'});
  return steps;
}
function jobDocumentId(owner, jobId) { return hash(`${owner}\n${safeId(jobId, 'jobId')}`); }
function watchDocumentId(owner, watchId) { return hash(`${owner}\n${safeId(watchId, 'watchId')}`); }
function jobIdFor(owner, kind, requestId) { return safeId(`social-${kind}-${hash(`${owner}\n${requestId}`).slice(0, 24)}`, 'jobId'); }
function sessionIdFor(jobId) { return safeId(`social-session-${hash(jobId).slice(0, 24)}`, 'sessionId'); }
function actionIdFor(jobId, cursor) { return safeId(`social-${hash(jobId).slice(0, 18)}-${String(cursor + 1).padStart(2, '0')}`, 'actionId'); }
function watchIdFor(jobId) { return safeId(`social-watch-${hash(jobId).slice(0, 24)}`, 'watchId'); }
function ticketRef(admin, dependencies, owner, ticketId) {
  return admin.firestore().collection(dependencies.collections.tickets).doc(dependencies.ticketDocId(owner, ticketId));
}
function publicJob(job) {
  if (!job) return null;
  const copy = {...job};
  delete copy.content;
  return copy;
}
function ticketSummary(ticket) {
  if (!ticket) return null;
  return {
    ticketId: ticket.ticketId,
    actionId: ticket.actionId,
    status: ticket.status,
    progress: ticket.progress || null,
    result: ticket.result || null,
    createdAtMs: ticket.createdAtMs || 0,
    completedAtMs: ticket.completedAtMs || 0,
  };
}
function resultCapture(step, ticket) {
  const result = safeObject(ticket && ticket.result);
  const post = safeObject(result.postcondition);
  return {
    captureAs: step.captureAs,
    stepId: step.stepId,
    action: step.action,
    url: safeText(result.url, 1000),
    title: safeText(result.title, 500),
    text: safeText(post.readText || (step.action === 'observe' ? result.visibleTextSummary : ''), 12000),
    value: safeText(post.readValue, 12000),
    href: safeText(post.readHref, 1000),
    semanticHash: hash(safeText(result.visibleTextSummary, 12000)),
  };
}
function assertResultBoundary(job, ticket) {
  const urlText = safeText(ticket && ticket.result && ticket.result.url, 1000);
  if (!urlText) return;
  assertAllowedUrl(urlText, job.allowedOrigins, 'observed browser result');
}
function splitReplyFragments(value) {
  const text = safeText(value, 12000).replace(/\r/g, '');
  if (!text) return [];
  const blocks = text.split(/\n\s*\n+/).map((block) => block.replace(/\s+/g, ' ').trim()).filter((block) => block.length >= 2);
  return blocks.slice(0, 100).map((block) => ({hash: hash(block), text: block}));
}
async function readJob(admin, dependencies, owner, jobId) {
  const ref = admin.firestore().collection(SOCIAL_COLLECTIONS.jobs).doc(jobDocumentId(owner, jobId));
  const snap = await ref.get();
  if (!snap.exists) throw Object.assign(new Error('Social job was not found for this owner.'), {status: 404, failureKind: 'browser_social_job_not_found'});
  const job = snap.data() || {};
  if (job.ownerKey !== owner) throw Object.assign(new Error('Social job owner mismatch.'), {status: 404, failureKind: 'browser_social_job_not_found'});
  return {ref, job};
}
async function readWatch(admin, owner, watchId) {
  const ref = admin.firestore().collection(SOCIAL_COLLECTIONS.watches).doc(watchDocumentId(owner, watchId));
  const snap = await ref.get();
  if (!snap.exists) throw Object.assign(new Error('Social watch was not found for this owner.'), {status: 404, failureKind: 'browser_social_watch_not_found'});
  const watch = snap.data() || {};
  if (watch.ownerKey !== owner) throw Object.assign(new Error('Social watch owner mismatch.'), {status: 404, failureKind: 'browser_social_watch_not_found'});
  return {ref, watch};
}
async function currentTicket(admin, dependencies, job) {
  if (!job.activeTicketId) return null;
  const snap = await ticketRef(admin, dependencies, job.ownerKey, job.activeTicketId).get();
  return snap.exists ? snap.data() || {} : null;
}
async function enqueueCurrentStep(admin, dependencies, jobRef, job, nowMs = Date.now()) {
  const cursor = Number(job.cursor || 0);
  const step = job.steps[cursor];
  if (!step) return job;
  const actionId = actionIdFor(job.jobId, cursor);
  const target = {...step.target};
  const value = step.valueSource === 'content' ? job.content : '';
  const ticket = await dependencies.enqueueBrowserNerveTicket({
    admin,
    caller: {ownerKey: job.ownerKey, actor: job.ownerEmail},
    args: {
      sessionId: job.sessionId,
      actionId,
      action: step.action,
      target,
      value,
      reason: `Chromium Throne social ${job.kind} job ${job.jobId}, step ${cursor + 1}/${job.steps.length}: ${step.stepId}`,
      workerId: job.workerId,
    },
    nowMs,
  });
  const next = {...job, state: 'RUNNING', activeTicketId: ticket.ticketId, activeActionId: ticket.actionId, updatedAtMs: nowMs};
  await jobRef.set(next, {merge: true});
  return next;
}
async function finalizePublish(admin, jobRef, job, nowMs = Date.now()) {
  const captures = safeObject(job.captures);
  const account = safeObject(captures.account);
  const post = safeObject(captures.post);
  const permalink = safeObject(captures.permalink);
  const failures = [];
  const observedAccount = safeText(account.text || account.value, 500);
  if (!observedAccount) failures.push('account identity was not observed');
  if (job.accountHint && !normalizeText(observedAccount).includes(normalizeText(job.accountHint))) failures.push('observed account did not match accountHint');
  const observedPost = normalizeText(post.text || post.value);
  if (!observedPost || !observedPost.includes(normalizeText(job.verificationText))) failures.push('published text proof did not contain verificationText');
  const permalinkText = safeText(permalink.href || permalink.url || job.lastObservedUrl, 1000);
  let permalinkUrl = null;
  try { permalinkUrl = assertAllowedUrl(permalinkText, job.allowedOrigins, 'permalink'); } catch (error) { failures.push(error.message); }
  if (failures.length) {
    const next = {...job, state: 'UNKNOWN', failureKind: 'browser_social_publish_unverified', failures, updatedAtMs: nowMs};
    await jobRef.set(next, {merge: true});
    return next;
  }
  const watchId = watchIdFor(job.jobId);
  const watch = {
    schemaVersion: SOCIAL_SCHEMA_VERSION,
    watchId,
    ownerKey: job.ownerKey,
    ownerEmail: job.ownerEmail,
    platform: job.platform,
    account: observedAccount,
    permalink: permalinkUrl.toString(),
    origin: permalinkUrl.origin,
    postJobId: job.jobId,
    contentHash: job.contentHash,
    seenReplyHashes: [],
    lastReplySnapshotHash: '',
    createdAtMs: nowMs,
    updatedAtMs: nowMs,
  };
  await admin.firestore().collection(SOCIAL_COLLECTIONS.watches).doc(watchDocumentId(job.ownerKey, watchId)).set(watch, {merge: true});
  const next = {...job, state: 'VERIFIED_PUBLISHED', permalink: watch.permalink, watchId, account: observedAccount, updatedAtMs: nowMs};
  await jobRef.set(next, {merge: true});
  return next;
}
async function finalizeReplies(admin, jobRef, job, nowMs = Date.now()) {
  const captures = safeObject(job.captures);
  const repliesCapture = safeObject(captures.replies);
  const fragments = splitReplyFragments(repliesCapture.text || repliesCapture.value);
  const {ref: watchRef, watch} = await readWatch(admin, job.ownerKey, job.watchId);
  const seen = new Set(Array.isArray(watch.seenReplyHashes) ? watch.seenReplyHashes : []);
  const fresh = [];
  for (const fragment of fragments) {
    if (!seen.has(fragment.hash)) fresh.push(fragment);
    seen.add(fragment.hash);
  }
  const snapshotHash = hash(fragments.map((fragment) => fragment.hash).join('\n'));
  await watchRef.set({
    seenReplyHashes: [...seen].slice(-500),
    lastReplySnapshotHash: snapshotHash,
    lastCheckedAtMs: nowMs,
    updatedAtMs: nowMs,
  }, {merge: true});
  const next = {
    ...job,
    state: fresh.length ? 'VERIFIED_REPLIES_RETURNED' : 'VERIFIED_NO_NEW_REPLIES',
    newReplies: fresh,
    replyCountObserved: fragments.length,
    newReplyCount: fresh.length,
    updatedAtMs: nowMs,
  };
  await jobRef.set(next, {merge: true});
  return next;
}
async function finalizeJob(admin, jobRef, job, nowMs = Date.now()) {
  if (job.kind === 'publish') return finalizePublish(admin, jobRef, job, nowMs);
  if (job.kind === 'replies') return finalizeReplies(admin, jobRef, job, nowMs);
  const recon = safeObject(safeObject(job.captures).recon);
  const next = {...job, state: 'OBSERVED', recon: {url: recon.url || job.lastObservedUrl || '', title: recon.title || '', text: recon.text || ''}, updatedAtMs: nowMs};
  await jobRef.set(next, {merge: true});
  return next;
}
async function advanceJob({admin, user, args = {}, dependencies, nowMs = Date.now()}) {
  const {email, owner} = socialOwner(user, dependencies.ownerKey);
  const jobId = safeId(args.jobId, 'jobId');
  const {ref, job: found} = await readJob(admin, dependencies, owner, jobId);
  let job = found;
  if (SOCIAL_TERMINAL_STATES.has(job.state)) return {job: publicJob(job), ticket: ticketSummary(await currentTicket(admin, dependencies, job))};
  const ticket = await currentTicket(admin, dependencies, job);
  if (!ticket) {
    job = await enqueueCurrentStep(admin, dependencies, ref, job, nowMs);
    return {job: publicJob(job), ticket: ticketSummary(await currentTicket(admin, dependencies, job))};
  }
  if (['queued', 'leased', 'running'].includes(ticket.status)) return {job: publicJob(job), ticket: ticketSummary(ticket)};
  const cursor = Number(job.cursor || 0);
  const step = job.steps[cursor];
  if (!step) return {job: publicJob(await finalizeJob(admin, ref, job, nowMs)), ticket: ticketSummary(ticket)};
  const mutationMayHaveHappened = !!job.mutationReached || !!step.mutation;
  if (ticket.status !== 'completed' || !ticket.result || ticket.result.ok === false) {
    const next = {
      ...job,
      state: mutationMayHaveHappened ? 'UNKNOWN' : 'BLOCKED',
      failureKind: mutationMayHaveHappened ? 'browser_social_mutation_unknown' : 'browser_social_step_failed',
      failures: [safeText(ticket.result && ticket.result.error || ticket.status || 'browser step failed', 1000)],
      activeTicketId: ticket.ticketId,
      updatedAtMs: nowMs,
    };
    await ref.set(next, {merge: true});
    return {job: publicJob(next), ticket: ticketSummary(ticket)};
  }
  try { assertResultBoundary(job, ticket); } catch (error) {
    const next = {...job, state: mutationMayHaveHappened ? 'UNKNOWN' : 'BLOCKED_BOUNDARY', failureKind: error.failureKind || 'browser_social_boundary_failed', failures: [error.message], updatedAtMs: nowMs};
    await ref.set(next, {merge: true});
    return {job: publicJob(next), ticket: ticketSummary(ticket)};
  }
  const captures = {...safeObject(job.captures)};
  if (step.captureAs) captures[step.captureAs] = resultCapture(step, ticket);
  const evidence = Array.isArray(job.evidence) ? [...job.evidence] : [];
  evidence.push({stepId: step.stepId, action: step.action, ticketId: ticket.ticketId, status: ticket.status, url: safeText(ticket.result.url, 1000), postcondition: safeObject(ticket.result.postcondition)});
  job = {
    ...job,
    cursor: cursor + 1,
    activeTicketId: '',
    activeActionId: '',
    mutationReached: mutationMayHaveHappened,
    captures,
    evidence: evidence.slice(-SOCIAL_MAX_STEPS),
    lastObservedUrl: safeText(ticket.result.url, 1000),
    updatedAtMs: nowMs,
  };
  await ref.set(job, {merge: true});
  if (job.cursor >= job.steps.length) job = await finalizeJob(admin, ref, job, nowMs);
  else job = await enqueueCurrentStep(admin, dependencies, ref, job, nowMs);
  return {job: publicJob(job), ticket: ticketSummary(await currentTicket(admin, dependencies, job))};
}
async function createSocialJob({admin, user, args = {}, dependencies, kind, nowMs = Date.now()}) {
  const {email, owner} = socialOwner(user, dependencies.ownerKey);
  const requestId = safeId(args.requestId, 'requestId');
  let watch = null;
  let startUrl;
  if (kind === 'replies') {
    const watchId = safeId(args.watchId, 'watchId');
    watch = (await readWatch(admin, owner, watchId)).watch;
    startUrl = cleanSocialUrl(watch.permalink, 'watch permalink');
  } else {
    startUrl = cleanSocialUrl(args.startUrl, 'startUrl');
  }
  if (hasPrivatePath(startUrl)) throw Object.assign(new Error('The public social operator cannot start on a private inbox/account surface.'), {status: 400, failureKind: 'browser_social_private_surface'});
  const allowedOrigins = cleanAllowedOrigins(startUrl, args.allowedOrigins);
  const content = kind === 'publish' ? safeText(args.content, 12000) : '';
  if (kind === 'publish' && !content) throw Object.assign(new Error('Explicit public post content is required.'), {status: 400, failureKind: 'browser_social_content_required'});
  const steps = cleanSocialWorkflow(kind, args.steps, {startUrl, allowedOrigins});
  const jobId = safeId(args.jobId || jobIdFor(owner, kind, requestId), 'jobId');
  const sessionId = sessionIdFor(jobId);
  const ref = admin.firestore().collection(SOCIAL_COLLECTIONS.jobs).doc(jobDocumentId(owner, jobId));
  const existing = await ref.get();
  const workflowHash = hash(JSON.stringify(steps));
  const contentHash = hash(content);
  if (existing.exists) {
    const prior = existing.data() || {};
    if (prior.ownerKey !== owner || prior.kind !== kind || prior.workflowHash !== workflowHash || prior.contentHash !== contentHash || prior.startUrl !== startUrl.toString()) {
      throw Object.assign(new Error('Social requestId/jobId idempotency conflict.'), {status: 409, failureKind: 'browser_social_idempotency_conflict'});
    }
    return {idempotent: true, job: publicJob(prior), ticket: ticketSummary(await currentTicket(admin, dependencies, prior))};
  }
  const verificationText = kind === 'publish' ? safeText(args.verificationText || content, 240) : '';
  if (kind === 'publish' && !normalizeText(verificationText)) throw Object.assign(new Error('verificationText cannot be empty.'), {status: 400, failureKind: 'browser_social_verification_required'});
  const job = {
    schemaVersion: SOCIAL_SCHEMA_VERSION,
    jobId,
    requestId,
    kind,
    state: 'QUEUED',
    ownerKey: owner,
    ownerEmail: email,
    platform: safeText(args.platform, 80) || startUrl.hostname,
    accountHint: safeText(args.accountHint, 320),
    sourceRef: safeText(args.sourceRef, 1000),
    content,
    contentHash,
    verificationText,
    startUrl: startUrl.toString(),
    allowedOrigins,
    watchId: watch ? watch.watchId : '',
    sessionId,
    workerId: safeId(args.workerId || 'windows-browser-nerve-01', 'workerId'),
    steps,
    workflowHash,
    cursor: 0,
    activeTicketId: '',
    activeActionId: '',
    mutationReached: false,
    captures: {},
    evidence: [],
    createdAtMs: nowMs,
    updatedAtMs: nowMs,
  };
  await ref.set(job, {merge: false});
  await admin.firestore().collection(dependencies.collections.sessions).doc(sessionId).set({
    sessionId,
    ownerKey: owner,
    status: 'created',
    intent: `Chromium Throne social ${kind}: ${safeText(args.sourceRef || args.platform || startUrl.hostname, 500)}`,
    startUrl: startUrl.toString(),
    surface: {runtime: 'browser_nerve', browser: 'chrome', mode: 'desktop', workerId: job.workerId},
    safetyMode: 'public-social-only',
    createdBy: email,
    createdAtMs: nowMs,
    updatedAtMs: nowMs,
  }, {merge: true});
  return advanceJob({admin, user, args: {jobId}, dependencies, nowMs});
}
async function getSocialJob({admin, user, args = {}, dependencies}) {
  const {owner} = socialOwner(user, dependencies.ownerKey);
  const jobId = safeId(args.jobId, 'jobId');
  const {job} = await readJob(admin, dependencies, owner, jobId);
  let watch = null;
  if (job.watchId) {
    try { watch = (await readWatch(admin, owner, job.watchId)).watch; } catch {}
  }
  return {job: publicJob(job), ticket: ticketSummary(await currentTicket(admin, dependencies, job)), watch};
}
function browserSocialOperationEntries() {
  return {
    'browser_nerve.social.recon': {summary: 'Start bounded same-origin semantic reconnaissance of a public social surface through Chromium Throne/Browser Nerve.', write: true, requiresRequestId: true, requiredScopes: [], input: {requestId: 'stable id', startUrl: 'public social URL', allowedOrigins: 'optional explicit public origins', workerId: 'optional Browser Nerve worker'}},
    'browser_nerve.social.publish': {summary: 'Queue an explicitly commissioned public social post through a finite semantic Browser Nerve workflow. Requires account, post, and permalink evidence; never includes DMs.', write: true, requiresRequestId: true, requiredScopes: [], input: {requestId: 'stable id', platform: 'platform label', startUrl: 'public composer URL', content: 'exact approved public text', accountHint: 'optional expected account', verificationText: 'optional bounded proof text', steps: '1-32 semantic actions', allowedOrigins: 'optional explicit public origins', sourceRef: 'optional provenance', workerId: 'optional Browser Nerve worker'}},
    'browser_nerve.social.replies': {summary: 'Queue a bounded public-thread reply read for a previously verified social watch. Private inbox and account surfaces remain forbidden.', write: true, requiresRequestId: true, requiredScopes: [], input: {requestId: 'stable id', watchId: 'verified public post watch', steps: '1-32 semantic read workflow', allowedOrigins: 'optional explicit public origins', workerId: 'optional Browser Nerve worker'}},
    'browser_nerve.social.advance': {summary: 'Advance one durable social job across its next Browser Nerve step, reconciling completed/failed actions and refusing blind mutation retries.', write: true, requiresRequestId: false, requiredScopes: [], input: {jobId: 'social job id'}},
    'browser_nerve.social.get': {summary: 'Read one durable social job, current Browser Nerve ticket, and public-post watch without advancing it.', write: false, requiresRequestId: false, requiredScopes: [], input: {jobId: 'social job id'}},
  };
}
async function browserSocialOperationRunOperation({admin, user, operation, args = {}, dependencies}) {
  if (operation === 'browser_nerve.social.recon') return createSocialJob({admin, user, args, dependencies, kind: 'recon'});
  if (operation === 'browser_nerve.social.publish') return createSocialJob({admin, user, args, dependencies, kind: 'publish'});
  if (operation === 'browser_nerve.social.replies') return createSocialJob({admin, user, args, dependencies, kind: 'replies'});
  if (operation === 'browser_nerve.social.advance') return advanceJob({admin, user, args, dependencies});
  if (operation === 'browser_nerve.social.get') return getSocialJob({admin, user, args, dependencies});
  throw Object.assign(new Error('Unsupported Browser Social operation.'), {status: 400, failureKind: 'browser_social_operation_unsupported'});
}

module.exports = {
  SOCIAL_SCHEMA_VERSION,
  SOCIAL_COLLECTIONS,
  SOCIAL_MAX_STEPS,
  SOCIAL_ALLOWED_ACTIONS,
  PRIVATE_PATH_PREFIXES,
  cleanSocialUrl,
  cleanSocialWorkflow,
  splitReplyFragments,
  browserSocialOperationEntries,
  browserSocialOperationRunOperation,
};
