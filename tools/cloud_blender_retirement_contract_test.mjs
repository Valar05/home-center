#!/usr/bin/env node
import assert from 'node:assert/strict';import fs from 'node:fs';
const home=fs.readFileSync(new URL('../functions/home_center_mcp.js',import.meta.url),'utf8');const command=fs.readFileSync(new URL('../functions/command_center_mcp.js',import.meta.url),'utf8');
for(const source of [home,command]){assert.match(source,/capability_retired\.use_blender_workspace/);assert.doesNotMatch(source,/capability_retired\.use_foundry/);}
assert.match(home,/blenderWorkspaceOperationEntries/);assert.match(home,/operation\.startsWith\('foundry\.'/);
for(const relative of ['functions/foundry_capability.js','functions/foundry_kernel.mjs','functions/foundry_worker_process.mjs','tools/deploy_foundry_worker.sh']) assert.equal(fs.existsSync(new URL('../'+relative,import.meta.url)),false,relative+' must be absent');
console.log(JSON.stringify({ok:true,retiredExecutionReachability:0,replacement:'drive_operation/blender.workspace.*',historicalReceipts:'read-only only'}));
