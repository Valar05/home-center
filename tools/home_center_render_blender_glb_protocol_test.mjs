#!/usr/bin/env node
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const {
  HOME_CENTER_CONNECTOR_SCHEMA_REVISION,
  HOME_CENTER_DIRECT_FILE_TOOLS,
  HOME_CENTER_REGISTRY_VERSION,
  createHomeCenterMcpServer,
} = require('../functions/home_center_mcp.js');

assert.match(HOME_CENTER_CONNECTOR_SCHEMA_REVISION, /^2026-07-25\.blender-direct-file-catalog-v2$/);
assert.equal(HOME_CENTER_REGISTRY_VERSION, HOME_CENTER_CONNECTOR_SCHEMA_REVISION);
assert.deepEqual([...HOME_CENTER_DIRECT_FILE_TOOLS], ['render_blender_glb']);

const server = createHomeCenterMcpServer({google: {}, admin: {}, googleClientId: '', googleClientSecret: ''});
const toolNames = Object.keys(server._registeredTools || {}).filter((name) => name === 'render_blender_glb');
assert.deepEqual(toolNames, ['render_blender_glb'], 'render_blender_glb must be registered exactly once as a top-level Home Center tool');

const handler = server.server._requestHandlers.get('tools/list');
assert.equal(typeof handler, 'function', 'tools/list handler must be installed');
const listed = await handler({method: 'tools/list', params: {}}, {});
const renderTools = (listed.tools || []).filter((tool) => tool.name === 'render_blender_glb');
assert.equal(renderTools.length, 1, 'tools/list must expose exactly one render_blender_glb tool');
const tool = renderTools[0];
const schema = tool.inputSchema || {};
const props = schema.properties || {};
assert.deepEqual(schema.required, ['idempotencyKey', 'glbFile', 'scriptFile']);
assert.equal(props.glbFile?.format, 'binary');
assert.equal(props.glbFile?.contentEncoding, undefined, 'ChatGPT host-file catalog schema must not publish JSON contentEncoding for binary upload slots');
assert.equal(props.glbFile?.contentMediaType, 'model/gltf-binary');
assert.match(props.glbFile?.description || '', /top-level host-file upload.*binary GLB/i);
assert.equal(props.scriptFile?.format, 'binary');
assert.equal(props.scriptFile?.contentEncoding, undefined, 'ChatGPT host-file catalog schema must not publish JSON contentEncoding for binary upload slots');
assert.equal(props.scriptFile?.contentMediaType, 'text/x-python');
assert.match(props.scriptFile?.description || '', /top-level host-file upload.*Blender Python/i);
assert.equal(props.glbRef, undefined, 'direct tool must not advertise glbRef');
assert.equal(props.scriptRef, undefined, 'direct tool must not advertise scriptRef');
assert.equal(props.scriptText, undefined, 'direct tool must not advertise scriptText');

const healthResult = await server._registeredTools.health.handler({}, {});
const health = JSON.parse(healthResult.content[0].text);
assert.equal(health.registryVersion, HOME_CENTER_REGISTRY_VERSION);
assert.equal(health.connectorSchemaRevision, HOME_CENTER_CONNECTOR_SCHEMA_REVISION);
assert.equal(health.catalogCacheKey, HOME_CENTER_CONNECTOR_SCHEMA_REVISION);
assert.deepEqual(health.directFileTools, ['render_blender_glb']);
assert.deepEqual(health.directToolContracts.render_blender_glb.required, ['idempotencyKey', 'glbFile', 'scriptFile']);
assert.equal(health.directToolContracts.render_blender_glb.binaryInputs.glbFile.format, 'binary');
assert.equal(health.directToolContracts.render_blender_glb.binaryInputs.glbFile.contentMediaType, 'model/gltf-binary');
assert.equal(health.directToolContracts.render_blender_glb.binaryInputs.glbFile.contentEncoding, undefined);
assert.equal(health.discoverability.topLevelDirectTools.render_blender_glb.status, 'published');
assert.equal(health.discoverability.commandCenter.registryVersion, HOME_CENTER_REGISTRY_VERSION);

const registeredTool = server._registeredTools.render_blender_glb;
const stringResult = registeredTool.inputSchema.safeParse({idempotencyKey: 'render-test', glbFile: '/tmp/a.glb', scriptFile: '/tmp/render.py'});
assert.equal(stringResult.success, false, 'strings passed as files must fail schema validation');
assert.match(String(stringResult.error), /expected file, received string/);
const fileResult = registeredTool.inputSchema.safeParse({idempotencyKey: 'render-test', glbFile: new File([new Uint8Array([1, 2, 3])], 'a.glb', {type: 'model/gltf-binary'}), scriptFile: new File([new Uint8Array([4, 5])], 'render.py', {type: 'text/x-python'})});
assert.equal(fileResult.success, true, 'top-level File objects must pass schema validation');
console.log('Home Center render_blender_glb protocol/schema test: OK');
