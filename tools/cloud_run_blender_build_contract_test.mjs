import assert from 'node:assert/strict';
import fs from 'node:fs';

const server = fs.readFileSync(new URL('../cloud-render/src/server.mjs', import.meta.url), 'utf8');
const renderer = fs.readFileSync(new URL('../cloud-render/src/render_bundle.mjs', import.meta.url), 'utf8');
const commandCenter = fs.readFileSync(new URL('../functions/command_center_mcp.js', import.meta.url), 'utf8');
const homeCenter = fs.readFileSync(new URL('../functions/home_center_mcp.js', import.meta.url), 'utf8');
const recipe = fs.readFileSync(new URL('../factory/sherman-cleanroom-cloudrun-a/build_sherman_cleanroom_a.py', import.meta.url), 'utf8');

assert.match(server, /POST' && req\.url === '\/render\/build'/);
assert.match(renderer, /COMMAND_CENTER_BLENDER_MODE: mode/);
assert.match(renderer, /Array\.isArray\(settings\[key\]\) && settings\[key\]\.length === 0/);
assert.match(renderer, /mode === 'build' \? Promise\.resolve\(Buffer\.alloc\(0\)\)/);
assert.match(renderer, /empty Blender factory scene \+ authoring script/);
assert.match(commandCenter, /case 'render\.blender_build'/);
assert.match(commandCenter, /baseUrl \+ \(normalizeRenderMode\(payload\.mode\) === 'build' \? '\/render\/build'/);
assert.match(commandCenter, /render\.blender_build starts from Blender factory state and does not accept a GLB source/);
assert.match(homeCenter, /'render\.blender_build'/);
assert.match(homeCenter, /scriptSource: '\{provider: github, repository: owner\/name, ref: immutable commit/);
assert.match(recipe, /bpy\.ops\.wm\.save_as_mainfile/);
assert.match(recipe, /bpy\.ops\.export_scene\.gltf/);
assert.match(recipe, /"startsFromFactoryEmptyScene": True/);
assert.doesNotMatch(recipe, /import_scene|bpy\.data\.libraries\.load/);

console.log('Cloud Run Blender empty-scene authoring contract passed.');
