import { randomUUID } from "node:crypto";
import { makeCoherenceStatus, makeEventEnvelope, makeWorkingState } from "../../staging-placeholder-do-not-import.mjs";

// NOTE: installer rewrites the schema import to ./schema.mjs when copying this file
// into src/durable-core. Keeping transport location explicit prevents accidental
// execution from the Home Center staging tree.

const DEFAULT_VERSIONS = Object.freeze({
  core: "phase2-event-spine-v1",
  identity: "VENICE_IDENTITY_PROFILE.md",
  routing: "phase1-explicit-routing-v1",
  store: "workstation-sqlite-v2",
});

function clip(value, max = 320) {
  return String(value ?? "").replace(/\s+/g, " ").trim().slice(0, max);
}

function projectState(store) {
  return store.listProjects().map((project) => ({
    projectId: project.id,
    title: project.title,
    updatedAt: project.updatedAt,
  }));
}

function jobLoop(job, extra = {}) {
  return {
    jobId: job.id,
    threadId: job.threadId,
    kind: job.kind,
    status: job.status,
    promptPreview: clip(job.prompt),
    updatedAt: job.updatedAt,
    ...extra,
  };
}

function currentOpenLoops(store, extraOpenLoops = []) {
  const byId = new Map();
  for (const job of store.listActiveJobs()) byId.set(job.id, jobLoop(job));
  for (const loop of extraOpenLoops || []) {
    const id = loop?.jobId || loop?.id || `recovery:${randomUUID()}`;
    byId.set(id, { ...loop, jobId: loop?.jobId || id });
  }
  return [...byId.values()];
}

function scheduleCommitments(store) {
  return store.listSchedules().filter((schedule) => schedule.enabled).map((schedule) => ({
    scheduleId: schedule.id,
    projectId: schedule.projectId,
    threadId: schedule.threadId,
    title: schedule.title,
    nextRunAt: schedule.nextRunAt,
  }));
}

export class VeniceDurableRuntime {
  constructor({ store, surfaceId = "workstation", versions = DEFAULT_VERSIONS } = {}) {
    if (!store) throw new TypeError("VeniceDurableRuntime requires store.");
    this.store = store;
    this.surfaceId = surfaceId;
    this.versions = { ...DEFAULT_VERSIONS, ...versions };
    this.state = null;
    this.lastCoherence = null;
  }

  initialize() {
    const existing = this.store.loadDurableWorkingState();
    if (existing) {
      this.state = existing;
      const tail = this.store.listDurableEventsAfter(existing.derivedThroughEventId, 1000);
      if (tail.length) {
        return this.refresh({
          eventKind: "runtime.event_tail.reconciled",
          reason: "A durable event tail existed beyond the last snapshot; state was reconciled from authoritative SQLite tables.",
          payload: { tailEventIds: tail.map((event) => event.eventId) },
        });
      }
      this.lastCoherence = this.coherence();
      return { state: this.state, coherence: this.lastCoherence, bootstrapped: false };
    }
    return this.refresh({
      eventKind: "runtime.bootstrap.observed",
      reason: "Initial durable-core bootstrap from existing Workstation SQLite state.",
      payload: { bootstrap: true },
    });
  }

  refresh({ eventKind = "runtime.state.reconciled", reason = "Durable state reconciled.", payload = {}, extraOpenLoops = [] } = {}) {
    const before = this.state?.stateVersion || 0;
    const after = before + 1;
    const correlationId = `runtime:${randomUUID()}`;
    const activeProjects = projectState(this.store);
    const openLoops = currentOpenLoops(this.store, extraOpenLoops);
    const pendingApprovals = this.store.listActiveJobs().filter((job) => job.status === "waiting_approval").map(jobLoop);
    const commitments = scheduleCommitments(this.store);
    const event = makeEventEnvelope({
      surfaceId: this.surfaceId,
      actor: { id: "venice-durable-runtime", kind: "system" },
      eventKind,
      correlationId,
      privacy: "private",
      stateVersionBefore: before,
      stateVersionAfter: after,
      payload: {
        reason,
        activeProjectCount: activeProjects.length,
        openLoopCount: openLoops.length,
        commitmentCount: commitments.length,
        ...payload,
      },
      provenance: [{ kind: "sqlite", ref: "work/workstation-v2/venice.db" }],
    });
    const state = makeWorkingState({
      stateVersion: after,
      derivedThroughEventId: event.eventId,
      activeProjects,
      openLoops,
      commitments,
      pendingApprovals,
      surfaces: [{ surfaceId: this.surfaceId, status: "ok" }],
      activeTask: openLoops.find((loop) => loop.status === "running") || openLoops[0] || undefined,
      lastCheckpoint: { eventId: event.eventId, eventKind, reason },
      versions: this.versions,
    });
    this.store.commitDurableTransition(event, state);
    this.state = state;
    this.lastCoherence = this.coherence();
    return { state, coherence: this.lastCoherence, event, bootstrapped: before === 0 };
  }

  coherence() {
    const state = this.state || this.store.loadDurableWorkingState();
    const reachable = this.store.durableEventCount() >= 1;
    const loaded = Boolean(state);
    return makeCoherenceStatus({
      status: reachable && loaded ? "ready" : "degraded",
      stateVersion: state?.stateVersion || 0,
      eventSpine: { reachable, eventCount: this.store.durableEventCount() },
      snapshot: { loaded, replayComplete: loaded },
      versions: state?.versions || this.versions,
      organs: [{ organId: "workstation-store", required: true, status: reachable && loaded ? "ok" : "degraded" }],
      surfaces: state?.surfaces || [],
      blockers: [],
    });
  }

  summary() {
    const state = this.state || this.store.loadDurableWorkingState();
    const coherence = this.lastCoherence || this.coherence();
    return {
      stateVersion: state?.stateVersion || 0,
      derivedThroughEventId: state?.derivedThroughEventId || null,
      openLoopCount: state?.openLoops?.length || 0,
      commitmentCount: state?.commitments?.length || 0,
      activeProjectCount: state?.activeProjects?.length || 0,
      coherence: { status: coherence.status, blockers: coherence.blockers || [] },
      versions: state?.versions || this.versions,
    };
  }
}
