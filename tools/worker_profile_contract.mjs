#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const registry = JSON.parse(fs.readFileSync(path.join(root, 'ops/worker_profiles.v1.json'), 'utf8'));

function fail(message) {
  process.stderr.write(`worker profile contract: ${message}\n`);
  process.exit(2);
}

function assignmentFor(name) {
  const assignment = registry.assignments?.[name];
  if (!assignment) fail(`unknown assignment ${name}`);
  if (assignment.state !== 'bound') fail(`${name} is ${assignment.state}, not bound`);
  return assignment;
}

function expectedFor(name) {
  const assignment = assignmentFor(name);
  const profile = registry.profiles[assignment.profile];
  const deployment = assignment.deployment;
  const expected = {
    profile: assignment.profile,
    runtime: profile.runtime,
    cpu: profile.cpu,
    memory: profile.memory,
    timeoutSeconds: profile.timeoutSeconds,
  };
  if (profile.runtime === 'cloud-run-service') {
    Object.assign(expected, {
      concurrency: profile.concurrency,
      minInstances: profile.minInstances,
      maxInstances: profile.maxInstances,
    });
    if (assignment.serviceAccount) expected.serviceAccount = assignment.serviceAccount;
  } else {
    Object.assign(expected, {
      tasks: profile.taskConcurrency,
      maxRetries: deployment.maxRetries,
    });
  }
  return expected;
}

function shellQuote(value) {
  return `'${String(value).replaceAll("'", "'\\''")}'`;
}

function emitShell(name) {
  const expected = expectedFor(name);
  const names = {
    profile: 'WORKER_PROFILE',
    runtime: 'WORKER_RUNTIME',
    cpu: 'WORKER_CPU',
    memory: 'WORKER_MEMORY',
    concurrency: 'WORKER_CONCURRENCY',
    minInstances: 'WORKER_MIN_INSTANCES',
    maxInstances: 'WORKER_MAX_INSTANCES',
    timeoutSeconds: 'WORKER_TIMEOUT_SECONDS',
    tasks: 'WORKER_TASKS',
    maxRetries: 'WORKER_MAX_RETRIES',
    serviceAccount: 'WORKER_SERVICE_ACCOUNT',
  };
  for (const [key, value] of Object.entries(expected)) {
    process.stdout.write(`${names[key]}=${shellQuote(value)}\n`);
  }
}

function parsePairs(values) {
  const parsed = {};
  for (const pair of values) {
    const index = pair.indexOf('=');
    if (index < 1) fail(`expected key=value, received ${pair}`);
    parsed[pair.slice(0, index)] = pair.slice(index + 1);
  }
  return parsed;
}

function normalizeCpu(value) {
  const text = String(value).trim();
  if (text.endsWith('m')) return Number(text.slice(0, -1)) / 1000;
  return Number(text);
}

function normalizeMemory(value) {
  const match = String(value).trim().match(/^(\d+(?:\.\d+)?)(Ki|Mi|Gi|Ti|K|M|G|T)?B?$/i);
  if (!match) return Number.NaN;
  const unit = (match[2] || '').toLowerCase();
  const factors = {ki: 1 / 1024, k: 1 / 1024, mi: 1, m: 1, gi: 1024, g: 1024, ti: 1024 * 1024, t: 1024 * 1024};
  return Number(match[1]) * (factors[unit] || 1);
}

function normalizeInteger(value) {
  return Number(String(value).replace(/s$/, ''));
}

function equivalent(key, actual, expected) {
  if (key === 'cpu') return normalizeCpu(actual) === normalizeCpu(expected);
  if (key === 'memory') return normalizeMemory(actual) === normalizeMemory(expected);
  if (['concurrency', 'minInstances', 'maxInstances', 'timeoutSeconds', 'tasks', 'maxRetries'].includes(key)) {
    return normalizeInteger(actual) === normalizeInteger(expected);
  }
  return String(actual) === String(expected);
}

function validateResolved(name, pairs) {
  const expected = expectedFor(name);
  const actual = parsePairs(pairs);
  for (const key of Object.keys(expected).filter((item) => !['profile', 'runtime'].includes(item))) {
    assert.ok(Object.hasOwn(actual, key), `missing resolved value ${key}`);
    assert.ok(equivalent(key, actual[key], expected[key]), `${name} ${key} drift: expected ${expected[key]}, received ${actual[key]}`);
  }
  process.stdout.write(JSON.stringify({ok: true, assignment: name, phase: 'pre-deploy', expected}) + '\n');
}

function at(value, dotted) {
  return dotted.split('.').reduce((current, key) => current?.[key], value);
}

function first(value, paths) {
  for (const candidate of paths) {
    const found = at(value, candidate);
    if (found !== undefined && found !== null && found !== '') return found;
  }
  return undefined;
}

function annotation(value, key) {
  return value?.spec?.template?.metadata?.annotations?.[key]
    ?? value?.metadata?.annotations?.[key];
}

function liveValues(name, live) {
  const expected = expectedFor(name);
  if (expected.runtime === 'cloud-run-service') {
    return {
      cpu: first(live, [
        'spec.template.spec.containers.0.resources.limits.cpu',
        'template.containers.0.resources.limits.cpu',
      ]),
      memory: first(live, [
        'spec.template.spec.containers.0.resources.limits.memory',
        'template.containers.0.resources.limits.memory',
      ]),
      concurrency: first(live, [
        'spec.template.spec.containerConcurrency',
        'template.maxInstanceRequestConcurrency',
      ]),
      minInstances: first(live, [
        'scaling.minInstanceCount',
        'template.scaling.minInstanceCount',
      ]) ?? annotation(live, 'autoscaling.knative.dev/minScale') ?? 0,
      maxInstances: first(live, [
        'scaling.maxInstanceCount',
        'template.scaling.maxInstanceCount',
      ]) ?? annotation(live, 'autoscaling.knative.dev/maxScale'),
      timeoutSeconds: first(live, [
        'spec.template.spec.timeoutSeconds',
        'template.timeout',
      ]),
      serviceAccount: first(live, [
        'spec.template.spec.serviceAccountName',
        'template.serviceAccount',
        'serviceConfig.serviceAccountEmail',
      ]),
    };
  }
  return {
    cpu: first(live, [
      'spec.template.spec.template.spec.containers.0.resources.limits.cpu',
      'template.template.containers.0.resources.limits.cpu',
    ]),
    memory: first(live, [
      'spec.template.spec.template.spec.containers.0.resources.limits.memory',
      'template.template.containers.0.resources.limits.memory',
    ]),
    tasks: first(live, [
      'spec.template.spec.taskCount',
      'template.taskCount',
    ]),
    maxRetries: first(live, [
      'spec.template.spec.template.spec.maxRetries',
      'template.template.maxRetries',
    ]),
    timeoutSeconds: first(live, [
      'spec.template.spec.template.spec.timeoutSeconds',
      'template.template.timeout',
    ]),
  };
}

function verifyLive(name) {
  const input = fs.readFileSync(0, 'utf8');
  if (!input.trim()) fail('live configuration JSON is empty');
  const live = JSON.parse(input);
  const expected = expectedFor(name);
  const actual = liveValues(name, live);
  for (const key of Object.keys(expected).filter((item) => !['profile', 'runtime'].includes(item))) {
    assert.ok(actual[key] !== undefined, `live ${name} omitted ${key}`);
    assert.ok(equivalent(key, actual[key], expected[key]), `live ${name} ${key} drift: expected ${expected[key]}, received ${actual[key]}`);
  }
  process.stdout.write(JSON.stringify({ok: true, assignment: name, phase: 'post-deploy', expected, actual}) + '\n');
}

const [command, name, ...rest] = process.argv.slice(2);
if (command === 'shell') emitShell(name);
else if (command === 'validate-resolved') validateResolved(name, rest);
else if (command === 'verify-live') verifyLive(name);
else fail('usage: worker_profile_contract.mjs <shell|validate-resolved|verify-live> <assignment> [key=value ...]');
