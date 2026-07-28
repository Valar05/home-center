#!/usr/bin/env node
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFileSync} from 'node:fs';

const require = createRequire(import.meta.url);
const shared = require('../functions/render_input_validation.js');
const command = require('../functions/command_center_mcp.js');
const home = require('../functions/home_center_mcp.js');

function glb(length = 12, declared = length) {
  const bytes = Buffer.alloc(length);
  bytes.write('glTF', 0, 'ascii');
  bytes.writeUInt32LE(2, 4);
  bytes.writeUInt32LE(declared, 8);
  return bytes;
}
const lfs = Buffer.from('version https://git-lfs.github.com/spec/v1\noid sha256:' + 'a'.repeat(64) + '\nsize 880000\n', 'utf8');

assert.equal(shared.gitLfsPointer(lfs), true);
assert.equal(shared.validateGlbBytes(glb()).declaredLength, 12);
assert.throws(() => shared.validateGlbBytes(lfs), (error) => error.failureKind === 'invalid_binary.git_lfs_pointer');
assert.throws(() => shared.validateGlbBytes(glb(16, 12)), (error) => error.failureKind === 'invalid_binary.glb_length');
assert.throws(() => shared.validateGlbBytes(glb(12, 16)), (error) => error.failureKind === 'invalid_binary.glb_length');
assert.throws(() => shared.validateGlbBytes(Buffer.from('not a model payload')), (error) => error.failureKind === 'invalid_binary.glb_magic');

assert.equal(shared.validatePythonScriptBytes(Buffer.from('import bpy\nprint("ok")\n')).text.includes('print'), true);
assert.throws(() => shared.validatePythonScriptBytes(Buffer.from([0xff, 0xfe, 0xfd])), (error) => error.failureKind === 'invalid_text.utf8');
assert.throws(() => shared.validatePythonScriptBytes(Buffer.from('if True print("bad")\n')), (error) => error.failureKind === 'invalid_text.python_syntax');
assert.throws(() => shared.validatePythonScriptBytes(Buffer.from('print("unterminated)\n')), (error) => error.failureKind === 'invalid_text.python_syntax');

assert.throws(() => command.validateGlbBytes(lfs, 'glbFile'), (error) => error.failureKind === 'invalid_binary.git_lfs_pointer');
assert.throws(() => command.validateGlbBytes(glb(16, 12), 'glbFile'), (error) => error.failureKind === 'invalid_binary.glb_length');
assert.throws(() => command.validateScriptBytes(Buffer.from('if True print("bad")\n'), 'scriptFile'), (error) => error.failureKind === 'invalid_text.python_syntax');
assert.throws(() => home.validateHomeCenterRenderBytes(lfs, 'glb', 'glbFile'), (error) => error.failureKind === 'invalid_binary.git_lfs_pointer');
assert.throws(() => home.validateHomeCenterRenderBytes(Buffer.from('if True print("bad")\n'), 'script', 'scriptFile'), (error) => error.failureKind === 'invalid_text.python_syntax');

const homeSource = readFileSync(new URL('../functions/home_center_mcp.js', import.meta.url), 'utf8');
const commandSource = readFileSync(new URL('../functions/command_center_mcp.js', import.meta.url), 'utf8');
assert.match(homeSource, /require\('\.\/render_input_validation'\)/);
assert.match(commandSource, /require\('\.\/render_input_validation'\)/);
assert.match(homeSource, /header\.readUInt32LE\(8\) !== byteCount/);
assert.doesNotMatch(homeSource, /declares more bytes than were downloaded/);
assert.doesNotMatch(commandSource, /declaredLength > bytes\.length/);

console.log(JSON.stringify({ok: true, gitLfsFailureKind: 'invalid_binary.git_lfs_pointer', exactLength: true, strictUtf8: true, pythonSyntax: '@lezer/python'}, null, 2));
