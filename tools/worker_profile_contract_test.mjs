import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync, spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const registryPath = path.join(root, 'ops/worker_profiles.v1.json');
const doctrinePath = path.join(root, 'docs/WORKER_RESOURCE_CONTRACT.md');
const agentsPath = path.join(root, 'AGENTS.md');
const ciPath = path.join(root, 'tools/home_center_ci_validate.sh');
const helperPath = path.join(root, 'tools/worker_profile_contract.mjs');
const registry = JSON.parse(fs.readFileSync(registryPath, 'utf8'));
const doctrine = fs.readFileSync(doctrinePath, 'utf8');
const agents = fs.readFileSync(agentsPath, 'utf8');

assert.equal(registry.schemaVersion, 'home-center.worker-resource-contract.v1');
assert.equal(registry.policy.scaleToZeroDefault, true);
assert.equal(registry.policy.singleArtifactConcurrency, 1);
assert.equal(registry.policy.maxVcpuWithoutBenchmark, 4);
assert.ok(Array.isArray(registry.policy.promotionEvidence));
assert.ok(registry.policy.promotionEvidence.length >= 4);
assert.ok(fs.existsSync(helperPath), 'worker profile resolver is missing');
assert.ok(agents.includes('ops/worker_profiles.v1.json'), 'AGENTS.md must route worker deployment changes to the registry');
assert.ok(agents.includes('CI is authoritative'), 'AGENTS.md must name CI as the enforcement authority');

const profiles = registry.profiles || {};
const assignments = registry.assignments || {};
for (const required of ['control-plane', 'media-forge-light', 'media-forge-heavy', 'browser-session']) {
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

const boundDeployments = new Map();
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
    assert.ok(assignment.deployment?.kind, `${worker} bound assignment needs a deployment kind`);
    assert.ok(!boundDeployments.has(assignment.deployment.path), `${assignment.deployment.path} is assigned twice`);
    boundDeployments.set(assignment.deployment.path, {worker, kind: assignment.deployment.kind});
    const deployPath = path.join(root, assignment.deployment.path);
    assert.ok(fs.existsSync(deployPath), `${worker} deployment path is missing`);
    const source = fs.readFileSync(deployPath, 'utf8');
    for (const marker of assignment.deployment.requiredMarkers || []) {
      assert.ok(source.includes(marker), `${worker} deployment is missing contract marker: ${marker}`);
    }
    for (const marker of assignment.deployment.forbiddenMarkers || []) {
      assert.ok(!source.includes(marker), `${worker} deployment restores forbidden resource override: ${marker}`);
    }
  }
}

const discovery = registry.deploymentDiscovery;
assert.ok(discovery?.roots?.length, 'deployment discovery roots are required');
assert.ok(discovery?.extensions?.length, 'deployment discovery extensions are required');
const extensions = new Set(discovery.extensions);
const ignoredDirectories = new Set(['.git', 'node_modules', 'generated']);
const rules = [
  {kind: 'cloud-run-job', pattern: /\bgcloud(?:\s+beta)?\s+run\s+jobs\s+deploy\b/},
  {kind: 'cloud-run-service', pattern: /\bgcloud(?:\s+beta)?\s+run\s+deploy\b/},
  {kind: 'cloud-functions', pattern: /\bgcloud(?:\s+beta)?\s+functions\s+deploy\b/},
  {kind: 'firebase-functions', pattern: /\bfirebase\s+deploy[^\n]*--only(?:=|\s+)functions\b/},
  {kind: 'cloud-run-service', pattern: /\bgoogle-github-actions\/deploy-cloudrun@/},
];

function walk(relative) {
  const absolute = path.join(root, relative);
  if (!fs.existsSync(absolute)) return [];
  const stat = fs.statSync(absolute);
  if (stat.isFile()) return [relative];
  const found = [];
  for (const entry of fs.readdirSync(absolute, {withFileTypes: true})) {
    if (entry.isDirectory() && ignoredDirectories.has(entry.name)) continue;
    const child = path.posix.join(relative.replaceAll('\\', '/'), entry.name);
    if (entry.isDirectory()) found.push(...walk(child));
    else if (extensions.has(path.extname(entry.name))) found.push(child);
  }
  return found;
}

const discovered = new Map();
for (const file of discovery.roots.flatMap(walk)) {
  const source = fs.readFileSync(path.join(root, file), 'utf8');
  const kinds = rules.filter((rule) => rule.pattern.test(source)).map((rule) => rule.kind);
  if (kinds.length) discovered.set(file, new Set(kinds));
}

const exemptions = discovery.exemptions || {};
for (const [file, kinds] of discovered) {
  const bound = boundDeployments.get(file);
  const exemption = exemptions[file];
  assert.ok(Boolean(bound) !== Boolean(exemption), `${file} must be bound exactly once or explicitly exempt`);
  const contract = bound || exemption;
  assert.ok(kinds.has(contract.kind), `${file} discovered ${[...kinds].join(', ')} but declares ${contract.kind}`);
  if (exemption) assert.ok(exemption.reason?.length >= 20, `${file} exemption needs a durable reason`);
}
for (const [file, bound] of boundDeployments) {
  assert.ok(discovered.has(file), `${bound.worker} deployment path is not discoverable as a deployment surface`);
}
for (const file of Object.keys(exemptions)) {
  assert.ok(discovered.has(file), `${file} exemption is stale or no longer deploys`);
}

assert.equal(assignments['home-center-mcp'].profile, 'control-plane');
assert.equal(assignments['command-center-blender-render'], undefined, 'retired generic renderer profile must stay deleted');
assert.equal(assignments['fortress-model-foundry'], undefined, 'retired custom geometry worker must stay deleted');
assert.equal(assignments['home-center-blender-workspace'].profile, 'media-forge-heavy');
assert.equal(assignments['home-center-blender-workspace'].state, 'bound');
assert.equal(assignments['home-center-audio-render'].state, 'target');
assert.equal(profiles['media-forge-heavy'].cpu, 4);
assert.equal(profiles['media-forge-heavy'].memory, '8Gi');
assert.equal(profiles['media-forge-heavy'].maxInstances, 4);

const blenderShell = execFileSync(process.execPath, [helperPath, 'shell', 'home-center-blender-workspace'], {encoding: 'utf8'});
assert.ok(blenderShell.includes("WORKER_CPU='4'"));
assert.ok(blenderShell.includes("WORKER_MEMORY='8Gi'"));
assert.ok(blenderShell.includes("WORKER_CONCURRENCY='1'"));
const serviceFixture = {spec:{template:{metadata:{annotations:{'autoscaling.knative.dev/maxScale':'4'}},spec:{containerConcurrency:1,timeoutSeconds:1800,containers:[{resources:{limits:{cpu:'4000m',memory:'8Gi'}}}]}}}};
function verifyFixture(name, fixture) { return spawnSync(process.execPath, [helperPath, 'verify-live', name], {input: JSON.stringify(fixture), encoding: 'utf8'}); }
assert.equal(verifyFixture('home-center-blender-workspace', serviceFixture).status, 0, 'Blender workspace live-readback fixture must pass');
serviceFixture.spec.template.spec.containerConcurrency = 80;
assert.notEqual(verifyFixture('home-center-blender-workspace', serviceFixture).status, 0, 'Blender workspace live drift must fail closed');

const ci = fs.readFileSync(ciPath, 'utf8');
assert.ok(ci.includes('node tools/worker_profile_contract_test.mjs'), 'Home Center CI must run worker profile contract');

console.log(JSON.stringify({
  ok: true,
  schemaVersion: registry.schemaVersion,
  profiles: Object.keys(profiles).length,
  assignments: Object.keys(assignments).length,
  bound: boundDeployments.size,
  discovered: discovered.size,
  exemptions: Object.keys(exemptions).length,
  automaticEnforcement: true,
}, null, 2));
