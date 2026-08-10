import fs from 'node:fs';

function read(path) { return fs.readFileSync(path, 'utf8'); }
function write(path, text) { fs.writeFileSync(path, text, 'utf8'); }
function insertAfterOnce(text, anchor, insertion, label) {
  if (text.includes(insertion.trim())) return text;
  const index = text.indexOf(anchor);
  if (index < 0) throw new Error(`Missing ${label} anchor: ${anchor}`);
  return text.slice(0, index + anchor.length) + insertion + text.slice(index + anchor.length);
}

const mcpPath = 'functions/home_center_mcp.js';
let mcp = read(mcpPath);
const importAnchor = "const {localVoiceOperationEntries, localVoiceOperationRunOperation} = require('./local_voice_farm_api');";
const importLine = "\nconst {computerHandsOperationEntries, computerHandsOperationRunOperation} = require('./computer_hands_api');";
mcp = insertAfterOnce(mcp, importAnchor, importLine, 'local voice import');

if (!mcp.includes('...computerHandsOperationEntries()')) {
  const spreadRegex = /\.\.\.localVoiceOperationEntries\(\),?/g;
  const matches = [...mcp.matchAll(spreadRegex)];
  if (!matches.length) throw new Error('Could not locate localVoiceOperationEntries registry spread.');
  mcp = mcp.replace(spreadRegex, (match) => `${match}\n    ...computerHandsOperationEntries(),`);
}

if (!mcp.includes('computerHandsOperationRunOperation({')) {
  const blockRegex = /if\s*\(\s*localVoiceOperationEntries\(\)\[operation\]\s*\)\s*\{([\s\S]{0,900}?)\n\s*\}/;
  const block = mcp.match(blockRegex);
  if (block && block[0].includes('localVoiceOperationRunOperation')) {
    const clone = block[0].replaceAll('localVoiceOperationEntries', 'computerHandsOperationEntries').replaceAll('localVoiceOperationRunOperation', 'computerHandsOperationRunOperation');
    mcp = mcp.replace(block[0], `${block[0]}\n  ${clone}`);
  } else {
    const lineRegex = /(^\s*if\s*\([^\n]*localVoiceOperationEntries\(\)[^\n]*\)[^\n]*localVoiceOperationRunOperation\([^\n]*$)/m;
    const line = mcp.match(lineRegex);
    if (!line) throw new Error('Could not locate local voice operation dispatcher.');
    const clone = line[1].replaceAll('localVoiceOperationEntries', 'computerHandsOperationEntries').replaceAll('localVoiceOperationRunOperation', 'computerHandsOperationRunOperation');
    mcp = mcp.replace(line[1], `${line[1]}\n${clone}`);
  }
}

const importCount = (mcp.match(/computer_hands_api/g) || []).length;
const entryCount = (mcp.match(/computerHandsOperationEntries/g) || []).length;
const runCount = (mcp.match(/computerHandsOperationRunOperation/g) || []).length;
if (importCount < 1 || entryCount < 2 || runCount < 2) throw new Error(`Computer Hands MCP integration incomplete: imports=${importCount} entries=${entryCount} runners=${runCount}`);
write(mcpPath, mcp);

const indexPath = 'functions/index.js';
let index = read(indexPath);
index = insertAfterOnce(index, "const {createLocalVoiceFarmHandler} = require('./local_voice_farm_api');", "\nconst {createComputerHandsHandler} = require('./computer_hands_api');", 'index local voice import');
index = insertAfterOnce(index, "exports.localVoiceFarm = onRequest({timeoutSeconds: 300, memory: '1GiB'}, createLocalVoiceFarmHandler({admin}));", "\n\nexports.computerHands = onRequest({timeoutSeconds: 300}, createComputerHandsHandler({admin}));", 'localVoiceFarm export');
write(indexPath, index);

const packagePath = 'functions/package.json';
const pkg = JSON.parse(read(packagePath));
if (pkg.scripts && typeof pkg.scripts.lint === 'string' && !pkg.scripts.lint.includes('computer_hands_api.js')) {
  pkg.scripts.lint = pkg.scripts.lint.replace('node --check local_voice_farm_api.js', 'node --check local_voice_farm_api.js && node --check computer_hands_api.js');
}
write(packagePath, JSON.stringify(pkg, null, 2) + '\n');

console.log(JSON.stringify({ok: true, mcp: {importCount, entryCount, runCount}, indexExport: index.includes('exports.computerHands'), fileLayer: 'drive_sync'}));
