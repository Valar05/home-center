const {randomUUID, createHash} = require('node:crypto');
const {
  COMMAND_CENTER_COLLECTIONS,
  COMMAND_CENTER_DEFAULT_PROJECTS,
  cleanProjectPacket,
  ownerKeyFromActor,
  assertOwnerAccess,
} = require('./command_center_mcp');

const HOME_CENTER_FORTRESS_COLLECTIONS = Object.freeze({
  projects: 'homeCenterProjects',
  sessions: 'homeCenterSessions',
  workItems: 'homeCenterWorkItems',
});

const WORK_STATES = new Set(['REQUESTED', 'QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'UNKNOWN']);

function safeText(value, max = 12000) {
  const text = typeof value === 'string' ? value.trim() : '';
  return text.length > max ? text.slice(0, max) : text;
}

function safeObject(value) {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
}

function safeList(value, maxItems = 50, maxText = 500) {
  return Array.isArray(value)
    ? value.slice(0, maxItems).map((item) => safeText(item, maxText)).filter(Boolean)
    : [];
}

function safeObjectList(value, maxItems = 20) {
  return Array.isArray(value) ? value.slice(0, maxItems).map((item) => safeObject(item)) : [];
}

function hashText(value, length = 16) {
  return createHash('sha256').update(String(value || '')).digest('hex').slice(0, length);
}

function slug(value, fallback = 'item') {
  const raw = safeText(value, 240).toLowerCase();
  const normalized = raw.replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
  const result = normalized || fallback;
  return result.slice(0, 120).replace(/^-+|-+$/g, '') || fallback;
}

function collection(admin, name) {
  return admin.firestore().collection(name);
}

function nowMs() {
  return Date.now();
}

function firestoreRef(collectionName, id) {
  return `firestore://${collectionName}/${id}`;
}

function parseFirestoreRef(ref) {
  const match = String(ref || '').match(/^firestore:\/\/([^/]+)\/([^/#?]+)$/);
  if (!match) return null;
  return {collection: match[1], id: match[2]};
}

function mergeUniqueStrings(values, additions, maxItems = 20) {
  return Array.from(new Set([...(Array.isArray(values) ? values : []), ...(Array.isArray(additions) ? additions : [])]
    .map((item) => safeText(item, 800))
    .filter(Boolean))).slice(0, maxItems);
}

function normalizeWorkState(value) {
  const state = safeText(value, 40).toUpperCase();
  return WORK_STATES.has(state) ? state : 'UNKNOWN';
}

function callerFromHomeCenterUser(user = {}, agentId = 'Venice') {
  const email = safeText(user.email, 320).toLowerCase();
  if (!email) {
    const err = new Error('A Home Center user email is required.');
    err.status = 401;
    err.code = 'home_center_user_required';
    throw err;
  }
  const cleanAgentId = safeText(agentId, 80) || 'Venice';
  return {
    email,
    agentId: cleanAgentId,
    authKind: safeText(user.authKind, 80),
    actor: `${slug(cleanAgentId, 'agent')}:${email}`,
    ownerKey: ownerKeyFromActor(email),
  };
}

function sessionIdForCaller(caller, agentId = 'Venice') {
  return `${caller.ownerKey}__${slug(agentId, 'agent')}`.slice(0, 120);
}

function defaultRepository() {
  return safeText(process.env.HOME_CENTER_DEFAULT_REPOSITORY, 240) || 'Valar05/home-center';
}

function defaultProjectInput(args = {}) {
  const repository = safeText(args.repository, 240) || defaultRepository();
  const projectIdHint = safeText(args.projectId, 120) || repository.split('/').pop() || 'home-center';
  return cleanProjectPacket({
    projectId: projectIdHint,
    repository,
    name: safeText(args.name, 200) || projectIdHint,
    capability: safeText(args.capability, 200) || 'fortress-online',
    repositoryBinding: safeObject(args.repositoryBinding),
    currentBranch: safeText(args.currentBranch, 120) || 'main',
    projectPacketRefs: safeList(args.projectPacketRefs, 80, 800),
    recentRelevantOutcomes: safeObjectList(args.recentRelevantOutcomes, 20),
    durable: true,
  });
}

function workspaceIdForProject(project = {}, override = '') {
  return slug(override || project.workspaceId || `${safeText(project.projectId, 120) || 'project'}-workspace`, 'workspace');
}

function workspaceLabelForProject(project = {}, override = '') {
  return safeText(override, 160) || safeText(project.workspaceLabel, 160) || `${safeText(project.name, 120) || safeText(project.projectId, 120) || 'Project'} workspace`;
}

function projectSummary(project = {}) {
  return {
    projectId: safeText(project.projectId, 120),
    name: safeText(project.name, 200),
    repository: safeText(project.repository, 240),
    capability: safeText(project.capability, 200),
    workspaceId: safeText(project.workspaceId, 120),
    workspaceLabel: safeText(project.workspaceLabel, 160),
    repositoryBinding: safeObject(project.repositoryBinding),
    projectPacketRefs: safeList(project.projectPacketRefs, 40, 800),
    provenance: safeObject(project.provenance),
  };
}

function summarizeWorkItem(work = {}) {
  return {
    taskId: safeText(work.taskId, 120),
    requestText: safeText(work.requestText, 400),
    taskKind: safeText(work.taskKind, 120),
    route: safeText(work.route, 120),
    normalizedState: normalizeWorkState(work.normalizedState || work.status),
    receiptRefs: safeList(work.receiptRefs, 10, 800),
    artifactRefs: safeList(work.artifactRefs, 10, 800),
    updatedAtMs: Number(work.updatedAtMs || 0) || 0,
  };
}

function buildOrientationPacket(session = {}, project = {}, work = {}) {
  return {
    project: projectSummary(project),
    workspace: {
      workspaceId: safeText(session.workspaceId || project.workspaceId, 120),
      label: safeText(session.workspaceLabel || project.workspaceLabel, 160),
    },
    last_checkpoint: safeText(session.lastCheckpointRef, 800),
    current_objective: safeText(session.currentObjective, 1000),
    recent_completed_work: (Array.isArray(work.completed) ? work.completed : []).map(summarizeWorkItem),
    pending_work: (Array.isArray(work.pending) ? work.pending : []).map(summarizeWorkItem),
    blockers: safeList(session.blockers, 20, 400),
    artifact_refs: safeList(session.artifactRefs, 20, 800),
    provenance: {
      sessionId: safeText(session.sessionId, 120),
      sessionRef: session.sessionId ? firestoreRef(HOME_CENTER_FORTRESS_COLLECTIONS.sessions, session.sessionId) : '',
      updatedAtMs: Number(session.updatedAtMs || 0) || 0,
      ownerEmail: safeText(session.ownerEmail, 320),
      agentId: safeText(session.agentId, 80),
      source: safeText(session.provenance && session.provenance.source, 200) || 'home_center.fortress_online',
    },
  };
}

async function readFirestoreRefDoc(admin, ref) {
  const parsed = parseFirestoreRef(ref);
  if (!parsed) return null;
  const snap = await collection(admin, parsed.collection).doc(parsed.id).get();
  return snap.exists ? {id: parsed.id, collection: parsed.collection, ref, data: snap.data() || {}} : null;
}

async function readReferencedWork(admin, refs = []) {
  const docs = [];
  for (const ref of safeList(refs, 20, 800)) {
    const loaded = await readFirestoreRefDoc(admin, ref);
    if (loaded && loaded.collection === HOME_CENTER_FORTRESS_COLLECTIONS.workItems) docs.push(loaded.data);
  }
  docs.sort((left, right) => Number(right.updatedAtMs || 0) - Number(left.updatedAtMs || 0));
  return docs;
}

async function loadHomeCenterProject(admin, caller, projectId) {
  const cleanProjectId = safeText(projectId, 120);
  if (!cleanProjectId) return null;
  const snap = await collection(admin, HOME_CENTER_FORTRESS_COLLECTIONS.projects).doc(cleanProjectId).get();
  if (!snap.exists) return null;
  const project = {projectId: cleanProjectId, ...(snap.data() || {})};
  assertOwnerAccess(project, caller, 'Home Center project');
  return project;
}

async function loadCompatProject(admin, caller, projectId) {
  const cleanProjectId = safeText(projectId, 120);
  if (!cleanProjectId) return null;
  const snap = await collection(admin, COMMAND_CENTER_COLLECTIONS.projects).doc(cleanProjectId).get();
  if (snap.exists) {
    const compat = {projectId: cleanProjectId, ...(snap.data() || {})};
    assertOwnerAccess(compat, caller, 'Command Center project');
    return {project: compat, sourceRef: firestoreRef(COMMAND_CENTER_COLLECTIONS.projects, cleanProjectId)};
  }
  if (COMMAND_CENTER_DEFAULT_PROJECTS[cleanProjectId]) {
    return {project: COMMAND_CENTER_DEFAULT_PROJECTS[cleanProjectId], sourceRef: `command-center-default://${cleanProjectId}`};
  }
  return null;
}

function promotedProjectFromCompat(compat = {}, caller = {}, args = {}, timeMs = nowMs()) {
  const packet = defaultProjectInput({
    projectId: compat.projectId || args.projectId,
    repository: compat.repository || args.repository,
    name: compat.name || args.name,
    capability: compat.capability || args.capability || 'fortress-online',
    repositoryBinding: compat.repositoryBinding || args.repositoryBinding,
    currentBranch: compat.currentBranch || args.currentBranch,
    projectPacketRefs: compat.projectPacketRefs || args.projectPacketRefs,
    recentRelevantOutcomes: compat.recentRelevantOutcomes || args.recentRelevantOutcomes,
  });
  return {
    ...packet,
    workspaceId: workspaceIdForProject(packet, args.workspaceId),
    workspaceLabel: workspaceLabelForProject(packet, args.workspaceLabel),
    ownerKey: caller.ownerKey,
    createdBy: caller.actor,
    updatedBy: caller.actor,
    createdAtMs: Number(compat.createdAtMs || packet.createdAtMs || timeMs) || timeMs,
    updatedAtMs: timeMs,
    provenance: {
      source: 'home_center.project.promoted_from_command_center',
      actor: caller.actor,
      sourceProjectId: safeText(compat.projectId, 120),
      sourceProjectRef: safeText(args.sourceProjectRef, 800),
    },
  };
}

function createdProjectRecord(caller = {}, args = {}, timeMs = nowMs()) {
  const packet = defaultProjectInput(args);
  return {
    ...packet,
    workspaceId: workspaceIdForProject(packet, args.workspaceId),
    workspaceLabel: workspaceLabelForProject(packet, args.workspaceLabel),
    ownerKey: caller.ownerKey,
    createdBy: caller.actor,
    updatedBy: caller.actor,
    createdAtMs: timeMs,
    updatedAtMs: timeMs,
    provenance: {
      source: 'home_center.project.created',
      actor: caller.actor,
    },
  };
}

async function resolveProject(admin, caller, args = {}, options = {}) {
  const timeMs = Number(options.nowMs || nowMs()) || nowMs();
  const preferred = defaultProjectInput(args);
  const existing = await loadHomeCenterProject(admin, caller, preferred.projectId);
  if (existing) return {project: existing, created: false, source: 'home_center'};
  const compat = await loadCompatProject(admin, caller, preferred.projectId);
  if (compat) {
    const promoted = promotedProjectFromCompat(compat.project, caller, {...args, sourceProjectRef: compat.sourceRef}, timeMs);
    await collection(admin, HOME_CENTER_FORTRESS_COLLECTIONS.projects).doc(promoted.projectId).set(promoted, {merge: false});
    return {project: promoted, created: true, source: 'command_center_compatibility'};
  }
  const created = createdProjectRecord(caller, args, timeMs);
  await collection(admin, HOME_CENTER_FORTRESS_COLLECTIONS.projects).doc(created.projectId).set(created, {merge: false});
  return {project: created, created: true, source: 'home_center_created'};
}

async function loadSession(admin, caller, agentId = 'Venice') {
  const sessionId = sessionIdForCaller(caller, agentId);
  const snap = await collection(admin, HOME_CENTER_FORTRESS_COLLECTIONS.sessions).doc(sessionId).get();
  if (!snap.exists) return null;
  const session = {sessionId, ...(snap.data() || {})};
  assertOwnerAccess(session, caller, 'Home Center session');
  return session;
}

function createdSessionRecord(caller = {}, project = {}, args = {}, timeMs = nowMs()) {
  const sessionId = sessionIdForCaller(caller, caller.agentId);
  return {
    sessionId,
    ownerKey: caller.ownerKey,
    ownerEmail: caller.email,
    agentId: caller.agentId,
    state: 'ACTIVE',
    projectId: safeText(project.projectId, 120),
    workspaceId: workspaceIdForProject(project, args.workspaceId),
    workspaceLabel: workspaceLabelForProject(project, args.workspaceLabel),
    currentObjective: safeText(args.currentObjective, 1000),
    lastCheckpointRef: safeText(args.lastCheckpointRef || args.checkpointRef, 800),
    pendingWorkRefs: safeList(args.pendingWorkRefs, 20, 800),
    recentCompletedWorkRefs: safeList(args.recentCompletedWorkRefs, 20, 800),
    artifactRefs: safeList(args.artifactRefs, 20, 800),
    blockers: safeList(args.blockers, 20, 400),
    lastWorkRef: safeText(args.lastWorkRef, 800),
    createdAtMs: timeMs,
    updatedAtMs: timeMs,
    provenance: {
      source: 'home_center.fortress_online',
      actor: caller.actor,
    },
  };
}

async function ensureActiveSession(admin, caller, args = {}, options = {}) {
  const timeMs = Number(options.nowMs || nowMs()) || nowMs();
  const existing = await loadSession(admin, caller, caller.agentId);
  if (existing) {
    const project = await resolveProject(admin, caller, {
      projectId: existing.projectId,
      repository: safeText(args.repository, 240) || '',
    }, {nowMs: timeMs});
    return {session: existing, project: project.project, createdSession: false, createdProject: project.created};
  }
  const resolved = await resolveProject(admin, caller, args, {nowMs: timeMs});
  const session = createdSessionRecord(caller, resolved.project, args, timeMs);
  await collection(admin, HOME_CENTER_FORTRESS_COLLECTIONS.sessions).doc(session.sessionId).set(session, {merge: false});
  return {session, project: resolved.project, createdSession: true, createdProject: resolved.created};
}

async function loadOrientation(admin, session, project) {
  const pending = await readReferencedWork(admin, session.pendingWorkRefs);
  const completed = await readReferencedWork(admin, session.recentCompletedWorkRefs);
  return buildOrientationPacket(session, project, {pending, completed});
}

async function fortressOnlineOperation({admin, caller, args = {}, now: nowFn = nowMs} = {}) {
  const active = await ensureActiveSession(admin, caller, args, {nowMs: nowFn()});
  const orientation = await loadOrientation(admin, active.session, active.project);
  return {
    ok: true,
    createdSession: active.createdSession,
    createdProject: active.createdProject,
    session: {
      sessionId: active.session.sessionId,
      projectId: active.session.projectId,
      workspaceId: active.session.workspaceId,
      agentId: active.session.agentId,
      ownerEmail: active.session.ownerEmail,
      updatedAtMs: active.session.updatedAtMs,
    },
    orientation,
  };
}

async function homeCenterSessionStatusOperation({admin, caller, args = {}} = {}) {
  const session = await loadSession(admin, caller, safeText(args.agentId, 80) || caller.agentId);
  if (!session) {
    return {
      ok: true,
      active: false,
      orientation: buildOrientationPacket({}, {}, {pending: [], completed: []}),
    };
  }
  const project = await resolveProject(admin, caller, {projectId: session.projectId}, {});
  return {
    ok: true,
    active: true,
    session: {
      sessionId: session.sessionId,
      projectId: session.projectId,
      workspaceId: session.workspaceId,
      agentId: session.agentId,
      ownerEmail: session.ownerEmail,
      updatedAtMs: session.updatedAtMs,
    },
    orientation: await loadOrientation(admin, session, project.project),
  };
}

async function homeCenterSessionUpdateOperation({admin, caller, args = {}, now: nowFn = nowMs} = {}) {
  const timeMs = nowFn();
  const active = await ensureActiveSession(admin, caller, args, {nowMs: timeMs});
  const nextSession = {
    ...active.session,
    workspaceId: workspaceIdForProject(active.project, safeText(args.workspaceId, 120) || active.session.workspaceId),
    workspaceLabel: workspaceLabelForProject(active.project, safeText(args.workspaceLabel, 160) || active.session.workspaceLabel),
    currentObjective: safeText(args.currentObjective, 1000) || active.session.currentObjective,
    lastCheckpointRef: safeText(args.checkpointRef || args.lastCheckpointRef, 800) || active.session.lastCheckpointRef,
    blockers: safeList(args.blockers, 20, 400).length ? safeList(args.blockers, 20, 400) : active.session.blockers,
    artifactRefs: mergeUniqueStrings(active.session.artifactRefs, safeList(args.artifactRefs, 20, 800), 20),
    updatedAtMs: timeMs,
    updatedBy: caller.actor,
    provenance: {
      ...(safeObject(active.session.provenance)),
      source: 'home_center.session.update',
      actor: caller.actor,
      requestId: safeText(args.requestId, 160),
      objectiveStatement: safeText(args.objectiveStatement, 1000),
    },
  };
  await collection(admin, HOME_CENTER_FORTRESS_COLLECTIONS.sessions).doc(nextSession.sessionId).set(nextSession, {merge: false});
  return {
    ok: true,
    session: {
      sessionId: nextSession.sessionId,
      projectId: nextSession.projectId,
      workspaceId: nextSession.workspaceId,
      updatedAtMs: nextSession.updatedAtMs,
    },
    orientation: await loadOrientation(admin, nextSession, active.project),
  };
}

function workReceiptForItem(work) {
  return {
    receiptRef: firestoreRef(HOME_CENTER_FORTRESS_COLLECTIONS.workItems, safeText(work.taskId, 120)),
    status: normalizeWorkState(work.normalizedState || work.status),
    taskId: safeText(work.taskId, 120),
    taskKind: safeText(work.taskKind, 120),
    summary: safeText(work.resultSummary || work.requestText, 400),
    updatedAtMs: Number(work.updatedAtMs || 0) || 0,
  };
}

function stagedWorkItem(caller = {}, session = {}, args = {}, timeMs = nowMs()) {
  const taskId = safeText(args.taskId, 120) || `work-${timeMs}-${randomUUID().slice(0, 8)}`;
  const route = safeText(args.route, 120) || 'manual_followup';
  return {
    taskId,
    ownerKey: caller.ownerKey,
    ownerEmail: caller.email,
    agentId: caller.agentId,
    sessionId: safeText(session.sessionId, 120),
    projectId: safeText(session.projectId, 120),
    workspaceId: safeText(session.workspaceId, 120),
    taskKind: safeText(args.taskKind, 120) || 'general_work_request',
    route,
    requestText: safeText(args.requestText, 2000),
    normalizedState: 'REQUESTED',
    status: 'REQUESTED',
    receiptRefs: [],
    artifactRefs: safeList(args.artifactRefs, 20, 800),
    subsystemRefs: safeList(args.subsystemRefs, 20, 800),
    statusHistory: [{state: 'REQUESTED', atMs: timeMs, note: 'Work request recorded in Home Center.'}],
    createdAtMs: timeMs,
    updatedAtMs: timeMs,
    provenance: {
      source: 'home_center.work_request',
      actor: caller.actor,
      requestId: safeText(args.requestId, 160),
    },
  };
}

function advanceWorkItem(work, state, note, timeMs) {
  const next = {...work};
  next.normalizedState = normalizeWorkState(state);
  next.status = normalizeWorkState(state);
  next.updatedAtMs = timeMs;
  next.statusHistory = [...safeObjectList(next.statusHistory, 20), {
    state: next.status,
    atMs: timeMs,
    note: safeText(note, 400),
  }];
  return next;
}

async function persistSessionWorkLink(admin, session, work, timeMs) {
  const ref = firestoreRef(HOME_CENTER_FORTRESS_COLLECTIONS.workItems, work.taskId);
  const pending = normalizeWorkState(work.status) === 'SUCCEEDED' || normalizeWorkState(work.status) === 'FAILED'
    ? activeWithoutRef(session.pendingWorkRefs, ref)
    : mergeUniqueStrings(activeWithoutRef(session.pendingWorkRefs, ref), [ref], 20);
  const completed = normalizeWorkState(work.status) === 'SUCCEEDED' || normalizeWorkState(work.status) === 'FAILED'
    ? mergeUniqueStrings([ref], activeWithoutRef(session.recentCompletedWorkRefs, ref), 20)
    : activeWithoutRef(session.recentCompletedWorkRefs, ref);
  const nextSession = {
    ...session,
    pendingWorkRefs: pending,
    recentCompletedWorkRefs: completed,
    artifactRefs: mergeUniqueStrings(session.artifactRefs, work.artifactRefs, 20),
    lastWorkRef: ref,
    updatedAtMs: timeMs,
    updatedBy: safeText(work.provenance && work.provenance.actor, 160),
    provenance: {
      ...(safeObject(session.provenance)),
      source: 'home_center.work_request',
      actor: safeText(work.provenance && work.provenance.actor, 160),
    },
  };
  await collection(admin, HOME_CENTER_FORTRESS_COLLECTIONS.sessions).doc(nextSession.sessionId).set(nextSession, {merge: false});
  return nextSession;
}

function activeWithoutRef(refs, ref) {
  return safeList(refs, 20, 800).filter((item) => item !== ref);
}

async function homeCenterWorkRequestOperation({admin, caller, args = {}, now: nowFn = nowMs, executeWork = null} = {}) {
  const timeMs = nowFn();
  const active = await ensureActiveSession(admin, caller, args, {nowMs: timeMs});
  let work = stagedWorkItem(caller, active.session, args, timeMs);
  const executor = typeof executeWork === 'function' ? executeWork : defaultFortressWorkExecutor;
  work = await executor({admin, caller, session: active.session, project: active.project, work, args, now: nowFn});
  work.receiptRefs = mergeUniqueStrings(work.receiptRefs, [workReceiptForItem(work).receiptRef], 10);
  await collection(admin, HOME_CENTER_FORTRESS_COLLECTIONS.workItems).doc(work.taskId).set(work, {merge: false});
  const nextSession = await persistSessionWorkLink(admin, active.session, work, Number(work.updatedAtMs || timeMs) || timeMs);
  return {
    ok: true,
    work: {
      taskId: work.taskId,
      normalizedState: normalizeWorkState(work.status),
      route: work.route,
      requestText: work.requestText,
      receipt: workReceiptForItem(work),
      statusHistory: safeObjectList(work.statusHistory, 20),
    },
    orientation: await loadOrientation(admin, nextSession, active.project),
  };
}

async function defaultFortressWorkExecutor({work, now: nowFn = nowMs}) {
  const first = Number(work.updatedAtMs || nowFn()) || nowFn();
  if (work.route !== 'fortress_session_probe') {
    return advanceWorkItem(work, 'REQUESTED', 'No executable Home Center work route is registered for this request yet.', first);
  }
  let next = advanceWorkItem(work, 'QUEUED', 'Queued in the Home Center fortress-session probe lane.', first + 1);
  next = advanceWorkItem(next, 'RUNNING', 'Executing the Home Center fortress-session probe.', first + 2);
  next = advanceWorkItem(next, 'SUCCEEDED', 'Completed the Home Center fortress-session probe and recorded a durable receipt.', first + 3);
  next.resultSummary = `Completed ${safeText(work.taskKind, 120) || 'fortress_session_probe'} for ${safeText(work.requestText, 200) || 'requested work'}.`;
  return next;
}

async function homeCenterWorkStatusOperation({admin, caller, args = {}} = {}) {
  const taskId = safeText(args.taskId, 120);
  let work = null;
  if (taskId) {
    const snap = await collection(admin, HOME_CENTER_FORTRESS_COLLECTIONS.workItems).doc(taskId).get();
    if (snap.exists) {
      work = {taskId, ...(snap.data() || {})};
      assertOwnerAccess(work, caller, 'Home Center work item');
    }
  } else {
    const session = await loadSession(admin, caller, caller.agentId);
    if (session && session.lastWorkRef) {
      const loaded = await readFirestoreRefDoc(admin, session.lastWorkRef);
      if (loaded && loaded.collection === HOME_CENTER_FORTRESS_COLLECTIONS.workItems) {
        work = {taskId: loaded.id, ...(loaded.data || {})};
        assertOwnerAccess(work, caller, 'Home Center work item');
      }
    }
  }
  if (!work) return {ok: true, found: false};
  return {
    ok: true,
    found: true,
    work: {
      taskId: work.taskId,
      requestText: safeText(work.requestText, 2000),
      taskKind: safeText(work.taskKind, 120),
      route: safeText(work.route, 120),
      normalizedState: normalizeWorkState(work.status),
      statusHistory: safeObjectList(work.statusHistory, 20),
      receipt: workReceiptForItem(work),
      artifactRefs: safeList(work.artifactRefs, 20, 800),
      subsystemRefs: safeList(work.subsystemRefs, 20, 800),
      updatedAtMs: Number(work.updatedAtMs || 0) || 0,
    },
  };
}

module.exports = {
  HOME_CENTER_FORTRESS_COLLECTIONS,
  callerFromHomeCenterUser,
  resolveProject,
  fortressOnlineOperation,
  homeCenterSessionStatusOperation,
  homeCenterSessionUpdateOperation,
  homeCenterWorkRequestOperation,
  homeCenterWorkStatusOperation,
  defaultFortressWorkExecutor,
  buildOrientationPacket,
  normalizeWorkState,
};
