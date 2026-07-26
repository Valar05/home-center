import assert from 'node:assert/strict';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const {
  driveOperationRunOperation,
  loadDroobiedooContextIndex,
  runDroobiedooContextOperation,
} = require('../functions/home_center_mcp.js');

const index = loadDroobiedooContextIndex();
assert.equal(index.schemaVersion, 'droobiedoo.context-index.v1');
assert.equal(index.readOnly, true);
assert.equal(index.remoteMutationAllowed, false);
assert.ok(index.forbiddenRemoteTools.includes('scripts/sync_workspace_artifacts.py'));
assert.equal(index.entries.some((entry) => entry.path.startsWith('wwdd/')), false, 'raw wwdd exports must not be MCP indexed');

const health = runDroobiedooContextOperation('droobiedoo.context_health', {});
assert.equal(health.readOnly, true);
assert.equal(health.remoteMutationAllowed, false);
assert.ok(health.relationships.home_center);
assert.ok(health.relationships.she_raw);
assert.ok(health.relationships.command_center);
assert.ok(health.relationships.simulation_frames);

const staleHealth = runDroobiedooContextOperation('droobiedoo.context_health', {
  maxAgeDays: 1,
  nowMs: Date.parse(index.generatedAt) + (2 * 24 * 60 * 60 * 1000),
});
assert.equal(staleHealth.freshness.isStale, true);
assert.ok(staleHealth.freshness.staleReasons.includes('generatedAt-older-than-maxAgeDays'));

const search = runDroobiedooContextOperation('droobiedoo.context_search', {query: 'workspace bootstrap doctrine', limit: 8});
assert.ok(search.results.length > 0);
assert.ok(search.results.some((entry) => ['AGENTS.md', 'README.md'].includes(entry.path) || entry.kind === 'doctrine'));

const project = runDroobiedooContextOperation('droobiedoo.project_resolve', {query: 'meshy asset workflow', limit: 8});
assert.ok(project.results.some((entry) => entry.path.includes('meshy_asset_workflow')));

const skills = runDroobiedooContextOperation('droobiedoo.skill_match', {query: 'visual qa screenshot stale build', limit: 8});
assert.ok(skills.results.some((entry) => entry.path.includes('visual-qa-harness') || entry.path.includes('visual-red-build-contract')));
assert.equal(skills.results.every((entry) => entry.kind === 'skill'), true);

const artifacts = runDroobiedooContextOperation('droobiedoo.artifact_search', {query: 'thunder pressure manifest', limit: 8});
assert.ok(artifacts.results.some((entry) => entry.path === 'generated/ml/thunder_pressure_manifest.json'));

const provenance = runDroobiedooContextOperation('droobiedoo.provenance_lookup', {path: 'scripts/sync_workspace_artifacts.py'});
assert.equal(provenance.results.length, 1);
assert.equal(provenance.results[0].remoteCallable, false);
assert.equal(provenance.results[0].remoteExposure.allowed, false);
assert.ok(provenance.results[0].sha256);

const packet = runDroobiedooContextOperation('droobiedoo.task_context_packet', {query: 'project context packet visual qa provenance', limit: 10, maxChars: 6000});
assert.equal(packet.readOnly, true);
assert.equal(packet.remoteMutationAllowed, false);
assert.ok(packet.guards.some((guard) => guard.includes('sync_workspace_artifacts.py')));
assert.ok(packet.entries.length > 0);
assert.equal(packet.provenance.length, packet.entries.length);

const routed = await driveOperationRunOperation({
  google: null,
  admin: null,
  auth: null,
  user: null,
  args: {operation: 'droobiedoo.skill_match', args: {query: 'workspace write operator shared storage', limit: 5}},
});
assert.equal(routed.completed, true);
assert.equal(routed.operation, 'droobiedoo.skill_match');
assert.ok(routed.result.results.length > 0);

const registryHealth = await driveOperationRunOperation({
  google: null,
  admin: null,
  auth: null,
  user: null,
  args: {operation: 'droobiedoo.context_health', args: {}},
});
assert.equal(registryHealth.result.forbiddenRemoteTools.includes('scripts/sync_workspace_artifacts.py'), true);

console.log('droobiedoo context source contract passed');
