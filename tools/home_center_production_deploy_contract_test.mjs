#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs';
const worker=fs.readFileSync(new URL('deploy_blender_workspace_worker.sh',import.meta.url),'utf8');
const release=fs.readFileSync(new URL('deploy_blender_workspace_release.sh',import.meta.url),'utf8');
const workflow=fs.readFileSync(new URL('../.github/workflows/deploy-home-center-mcp.yml',import.meta.url),'utf8');
assert.match(worker,/assert_home_center_mcp_main_release\.sh/);assert.match(worker,/BLENDER_RELEASE_GUARDED/);assert.match(worker,/gcloud builds submit/);assert.match(worker,/gcloud run deploy/);assert.match(worker,/blenderWorkspace/);
assert.match(release,/deploy_blender_workspace_worker\.sh/);assert.match(release,/home_center_production_catalog_test\.mjs/);assert.match(release,/functions delete foundryAssetWorker/);assert.match(release,/tasks queues delete/);assert.doesNotMatch(release,/resume.*foundry/i);
assert.match(workflow,/deploy_blender_workspace_release\.sh/);assert.doesNotMatch(workflow,/deploy_foundry/);
console.log('Home Center Blender workspace production deploy contract: OK');
