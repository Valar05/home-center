'use strict';

const {TextDecoder} = require('node:util');
const {parser: pythonParser} = require('@lezer/python');

const GIT_LFS_SIGNATURE = 'version https://git-lfs.github.com/spec/v1';

function defaultError(message, status = 400, code = 'input_validation') {
  const error = new Error(message);
  error.status = status;
  error.code = code;
  error.failureKind = code;
  return error;
}

function errorFrom(options, message, status, code) {
  return (options && typeof options.makeError === 'function' ? options.makeError : defaultError)(message, status, code);
}

function gitLfsPointer(bytes) {
  if (!Buffer.isBuffer(bytes) || bytes.length === 0) return false;
  const prefix = bytes.subarray(0, Math.min(bytes.length, 1024)).toString('utf8').replace(/^\uFEFF/, '');
  return prefix.startsWith(GIT_LFS_SIGNATURE + '\n') && /\noid sha256:[a-f0-9]{64}(?:\n|$)/i.test(prefix);
}

function validateGlbBytes(bytes, label = 'GLB input', options = {}) {
  const maxBytes = Number(options.maxBytes || 250 * 1024 * 1024);
  if (gitLfsPointer(bytes)) throw errorFrom(options, label + ' contains Git LFS pointer text instead of GLB bytes.', 422, 'invalid_binary.git_lfs_pointer');
  if (!Buffer.isBuffer(bytes) || bytes.length < 12) throw errorFrom(options, label + ' is too small to be a GLB file.', 400, 'invalid_binary.glb_too_small');
  if (bytes.length > maxBytes) throw errorFrom(options, label + ' exceeds max GLB size ' + maxBytes + ' bytes.', 413, 'invalid_binary.glb_too_large');
  if (bytes.subarray(0, 4).toString('ascii') !== 'glTF') throw errorFrom(options, label + ' is not a GLB: missing glTF magic.', 422, 'invalid_binary.glb_magic');
  const version = bytes.readUInt32LE(4);
  const declaredLength = bytes.readUInt32LE(8);
  if (version !== 2) throw errorFrom(options, label + ' must be GLB version 2.', 422, 'invalid_binary.glb_version');
  if (declaredLength !== bytes.length) throw errorFrom(options, label + ' GLB length header does not match the exact byte length.', 422, 'invalid_binary.glb_length');
  return {byteLength: bytes.length, version, declaredLength};
}

function validatePythonScriptBytes(bytes, label = 'render script', options = {}) {
  const maxBytes = Number(options.maxBytes || 1024 * 1024);
  const maxSyntaxNodes = Number(options.maxSyntaxNodes || 250000);
  if (!Buffer.isBuffer(bytes) || bytes.length === 0) throw errorFrom(options, label + ' is empty.', 400, 'invalid_text.empty');
  if (bytes.length > maxBytes) throw errorFrom(options, label + ' exceeds max script size ' + maxBytes + ' bytes.', 413, 'invalid_text.too_large');
  if (bytes.includes(0)) throw errorFrom(options, label + ' must be a text Python script, not binary data.', 422, 'invalid_text.binary_nul');
  let text;
  try {
    text = new TextDecoder('utf-8', {fatal: true}).decode(bytes);
  } catch (_) {
    throw errorFrom(options, label + ' is not valid UTF-8 text.', 422, 'invalid_text.utf8');
  }
  const tree = pythonParser.parse(text);
  const cursor = tree.cursor();
  let nodeCount = 0;
  let firstError = null;
  do {
    nodeCount += 1;
    if (cursor.type.isError && !firstError) firstError = {from: cursor.from, to: cursor.to};
    if (nodeCount > maxSyntaxNodes) throw errorFrom(options, label + ' exceeds the bounded Python syntax complexity limit.', 413, 'invalid_text.syntax_too_complex');
  } while (cursor.next());
  if (firstError) throw errorFrom(options, label + ' contains invalid Python syntax near byte offset ' + firstError.from + '.', 422, 'invalid_text.python_syntax');
  return {byteLength: bytes.length, text, syntaxNodes: nodeCount};
}

module.exports = {GIT_LFS_SIGNATURE, gitLfsPointer, validateGlbBytes, validatePythonScriptBytes};
