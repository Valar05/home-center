import fs from 'node:fs';

function read(path) { return fs.readFileSync(path, 'utf8'); }
function write(path, text) { fs.writeFileSync(path, text, 'utf8'); }
function insertAfterOnce(text, anchor, insertion, label) {
  if (text.includes(insertion.trim())) return text;
  const index = text.indexOf(anchor);
  if (index < 0) throw new Error(`Missing ${label} anchor: ${anchor}`);
  return text.slice(0, index + anchor.length) + insertion + text.slice(index + anchor.length);
}

const commandPath = 'functions/command_center_mcp.js';
let command = read(commandPath);
if (!/\n\s*runCommandCenterOperation,\s*\n/.test(command)) {
  command = insertAfterOnce(command, '  lookupBrowserPlaybook,\n', '  runCommandCenterOperation,\n', 'Command Center export');
}
if (!command.includes('runCommandCenterOperation,')) throw new Error('Command Center runner export missing.');
write(commandPath, command);

const mcpPath = 'functions/home_center_mcp.js';
let mcp = read(mcpPath);
const importAnchor = "const {computerHandsOperationEntries, computerHandsOperationRunOperation} = require('./computer_hands_api');";
const importLine = "\nconst {veniceBodyOperationEntries, veniceBodyOperationRunOperation} = require('./venice_body_router');";
mcp = insertAfterOnce(mcp, importAnchor, importLine, 'Computer Hands import');

if (!mcp.includes('...veniceBodyOperationEntries()')) {
  const spreadRegex = /\.\.\.computerHandsOperationEntries\(\),?/g;
  const matches = [...mcp.matchAll(spreadRegex)];
  if (!matches.length) throw new Error('Could not locate Computer Hands registry spread.');
  mcp = mcp.replace(spreadRegex, (match) => `${match}\n    ...veniceBodyOperationEntries(),`);
}

if (!mcp.includes('veniceBodyOperationRunOperation({')) {
  const blockRegex = /if\s*\(\s*computerHandsOperationEntries\(\)\[operation\]\s*\)\s*\{([\s\S]{0,1400}?)\n\s*\}/;
  const block = mcp.match(blockRegex);
  if (!block || !block[0].includes('computerHandsOperationRunOperation')) {
    throw new Error('Could not locate Computer Hands operation dispatcher block.');
  }
  let clone = block[0]
    .replaceAll('computerHandsOperationEntries', 'veniceBodyOperationEntries')
    .replaceAll('computerHandsOperationRunOperation', 'veniceBodyOperationRunOperation');
  clone = clone.replace(/veniceBodyOperationRunOperation\(\{/, 'veniceBodyOperationRunOperation({extra, ');
  if (!clone.includes('veniceBodyOperationRunOperation({extra,')) throw new Error('Could not inject MCP request context into Venice body dispatcher.');
  mcp = mcp.replace(block[0], `${block[0]}\n  ${clone}`);
}

const importCount = (mcp.match(/venice_body_router/g) || []).length;
const entryCount = (mcp.match(/veniceBodyOperationEntries/g) || []).length;
const runCount = (mcp.match(/veniceBodyOperationRunOperation/g) || []).length;
if (importCount < 1 || entryCount < 2 || runCount < 2) {
  throw new Error(`Venice body router MCP integration incomplete: imports=${importCount} entries=${entryCount} runners=${runCount}`);
}
write(mcpPath, mcp);

console.log(JSON.stringify({
  ok: true,
  commandCenterRunnerExported: command.includes('runCommandCenterOperation,'),
  mcp: {importCount, entryCount, runCount},
  contract: 'browser_nerve_owns_page__computer_hands_owns_machine',
}));
