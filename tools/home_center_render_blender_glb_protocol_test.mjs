#!/usr/bin/env node
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const {createHomeCenterMcpServer} = require('../functions/home_center_mcp.js');

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
assert.equal(props.glbFile?.contentEncoding, 'binary');
assert.match(props.glbFile?.description || '', /top-level uploaded binary GLB file/i);
assert.equal(props.scriptFile?.format, 'binary');
assert.equal(props.scriptFile?.contentEncoding, 'binary');
assert.match(props.scriptFile?.description || '', /top-level uploaded Blender Python/i);
assert.equal(props.glbRef, undefined, 'direct tool must not advertise glbRef');
assert.equal(props.scriptRef, undefined, 'direct tool must not advertise scriptRef');
assert.equal(props.scriptText, undefined, 'direct tool must not advertise scriptText');

const registeredTool = server._registeredTools.render_blender_glb;
const stringResult = registeredTool.inputSchema.safeParse({idempotencyKey: 'render-test', glbFile: '/tmp/a.glb', scriptFile: '/tmp/render.py'});
assert.equal(stringResult.success, false, 'strings passed as files must fail schema validation');
assert.match(String(stringResult.error), /expected file, received string/);
const fileResult = registeredTool.inputSchema.safeParse({idempotencyKey: 'render-test', glbFile: new File([new Uint8Array([1, 2, 3])], 'a.glb', {type: 'model/gltf-binary'}), scriptFile: new File([new Uint8Array([4, 5])], 'render.py', {type: 'text/x-python'})});
assert.equal(fileResult.success, true, 'top-level File objects must pass schema validation');
console.log('Home Center render_blender_glb protocol/schema test: OK');
