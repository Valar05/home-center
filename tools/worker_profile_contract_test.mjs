import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const registryPath = path.join(root, 'ops/worker_profiles.v1.json');
const doctrinePath = path.join(root, 'docs/WORKER_RESOURCE_CONTRACT.md');
const ciPath = path.join(root, 'tools/home_center_ci_validate.sh');
const registry = JSON.parse(fs.readFileSync(registryPath, 'utf8'));
const doctrine = fs.readFileSync(doctrinePath, 'utf8');

assert.equal(registry.schemaVersion, 'home-center.worker-resource-contract.v1');
assert.equal(registry.policy.scaleToZeroDefault, true);
assert.equal(registry.policy.singleArtifactConcurrency, 1);
assert.equal(registry.policy.maxVcpuWithoutBenchmark, 4);
assert.ok(Array.isArray(registry.policy.promotionEvidence));
assert.ok(registry.policy.promotionEvidence.length >= 4);

const profiles = registry.profiles || {};
const assignments = registry.assignments || {};
for (const required of ['control-plane', 'codex-job', 'media-forge-light', 'media-forge-heavy', 'browser-session']) {
  assert.ok(profiles[required], `missing profile ${required}`);
  assert.ok(doctrine.includes('`' + required + '`'), `doctrine must explain ${required}`);
}

function memoryMi(value) {
  const match = String(value).match(/^(\d+)(Mi|Gi)$/);
  assert.ok(match, `invalid memory value ${value}`);
  return Number(match[1]) * (match[2] === 'Gi' ? 1024 : 1);
}

for (const [name, profile] of Object.entries(profiles)) {
  assert.ok(['cloud-run-service', 'cloud-run-job'].includes(profile.runtime), `${name} has invalid runtime`);
  assert.ok(Number.isInteger(profile.cpu) && profile.cpu >= 1, `${name} needs integer CPU`);
  assert.ok(profile.cpu <= registry.policy.maxVcpuWithoutBenchmark, `${name} exceeds unbenchmarked CPU ceiling`);
  assert.ok(memoryMi(profile.memory) >= 512, `${name} memory is below the Gen-2 floor`);
  assert.ok(Number.isInteger(profile.timeoutSeconds) && profile.timeoutSeconds > 0, `${name} needs a timeout`);
  if (name.startsWith('media-forge')) {
    assert.equal(profile.concurrency, 1, `${name} must own one artifact per instance`);
    assert.equal(profile.minInstances, 0, `${name} must scale to zero by default`);
    assert.ok(profile.maxInstances <= registry.policy.maxForgeInstancesWithoutReview, `${name} exceeds forge scale ceiling`);
    assert.equal(profile.nativeThreads, 'available', `${name} must delegate safe threading to native tools`);
  }
}

for (const [worker, assignment] of Object.entries(assignments)) {
  assert.ok(profiles[assignment.profile], `${worker} references unknown profile ${assignment.profile}`);
  assert.ok(['bound', 'guardrail', 'target'].includes(assignment.state), `${worker} has invalid assignment state`);
  assert.ok(doctrine.includes('`' + worker + '`'), `doctrine must name assignment ${worker}`);
  if (assignment.state === 'target') {
    assert.ok(assignment.promotionGate, `${worker} target needs a promotion gate`);
    assert.equal(assignment.deployment, undefined, `${worker} target must not pretend to be bound`);
  }
  if (assignment.state === 'bound') {
    assert.ok(assignment.deployment?.path, `${worker} bound assignment needs a deployment path`);
    const deployPath = path.join(root, assignment.deployment.path);
    assert.ok(fs.existsSync(deployPath), `${worker} deployment path is missing`);
    const source = fs.readFileSync(deployPath, 'utf8');
    for (const marker of assignment.deployment.requiredMarkers || []) {
      assert.ok(source.includes(marker), `${worker} deployment is missing contract marker: ${marker}`);
    }
  }
}

assert.equal(assignments['home-center-mcp'].profile, 'control-plane');
assert.equal(assignments['command-center-blender-render'].profile, 'media-forge-heavy');
assert.equal(assignments['home-center-audio-render'].state, 'target');
assert.equal(profiles['media-forge-heavy'].cpu, 4);
assert.equal(profiles['media-forge-heavy'].memory, '8Gi');
assert.equal(profiles['media-forge-heavy'].maxInstances, 4);

const ci = fs.readFileSync(ciPath, 'utf8');
assert.ok(ci.includes('node tools/worker_profile_contract_test.mjs'), 'Home Center CI must run worker profile contract');

console.log(JSON.stringify({
  ok: true,
  schemaVersion: registry.schemaVersion,
  profiles: Object.keys(profiles).length,
  assignments: Object.keys(assignments).length,
  bound: Object.values(assignments).filter((item) => item.state === 'bound').length
}, null, 2));
