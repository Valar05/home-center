#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const OUT = path.join(ROOT, 'generated/backend_automation/introspection.json');
const COMMAND_CENTER = path.join(ROOT, 'functions/command_center_mcp.js');
const INDEX = path.join(ROOT, 'functions/index.js');

function read(file) {
  return fs.readFileSync(file, 'utf8');
}

function unique(items) {
  return Array.from(new Set(items)).sort();
}

function functionBodySlice(source, functionName) {
  const start = source.indexOf(`function ${functionName}`);
  if (start < 0) return '';
  const nextFunction = source.indexOf('\nfunction ', start + 1);
  return source.slice(start, nextFunction > start ? nextFunction : undefined);
}

function caseNames(source, functionName) {
  const body = functionBodySlice(source, functionName);
  return unique(Array.from(body.matchAll(/case '([^']+)'/g)).map((match) => match[1]));
}

function literalArray(name, source) {
  const match = source.match(new RegExp(`const\\s+${name}\\s*=\\s*\\[([\\s\\S]*?)\\];`));
  if (!match) return [];
  return unique(Array.from(match[1].matchAll(/'([^']+)'/g)).map((item) => item[1]));
}

function count(pattern, source) {
  return Array.from(source.matchAll(pattern)).length;
}

const commandCenter = read(COMMAND_CENTER);
const index = read(INDEX);
const operations = caseNames(commandCenter, 'runCommandCenterOperation');
const automationOperations = operations.filter((op) => /^(workers|agents|jobs|app_control|browser_sessions|browser_discoveries|browser_playbooks|bucket)\./.test(op));
const defaultWorkerCaps = unique(Array.from(commandCenter.matchAll(/advertisedCapabilities\s*:\s*\[([\s\S]*?)\]/g)).flatMap((match) => Array.from(match[1].matchAll(/'([^']+)'/g)).map((item) => item[1])));
const cloudRunJobConfigured = commandCenter.includes("channel.mode === 'cloud_run_job'") && commandCenter.includes('invokeCloudRunJobActivation');
const workerEndpoints = unique(Array.from(commandCenter.matchAll(/app\.post\('([^']+)'/g)).map((match) => match[1]).filter((route) => route.startsWith('/agent/')));
const homeGatewayExports = unique(Array.from(index.matchAll(/exports\.([A-Za-z0-9_]+)\s*=/g)).map((match) => match[1]));
const result = {
  ok: true,
  generatedAt: new Date().toISOString(),
  sourceFiles: ['functions/command_center_mcp.js', 'functions/index.js'],
  commandCenter: {
    operationCount: operations.length,
    operations,
    automationOperationCount: automationOperations.length,
    automationOperations,
    workerEndpoints,
    cloudRunJobConfigured,
    defaultWorkerCapabilities: defaultWorkerCaps,
    appControlProfileSurface: operations.some((op) => op.startsWith('app_control.')),
    browserAutomationSurface: operations.some((op) => op.startsWith('browser_')),
    durableWorkerSurface: operations.some((op) => op.startsWith('workers.')) && operations.some((op) => op.startsWith('agents.')),
  },
  homeGateway: {
    exportCount: homeGatewayExports.length,
    exports: homeGatewayExports,
    ttsVoicesExported: homeGatewayExports.includes('ttsVoices'),
    termuxTokenRefreshExported: homeGatewayExports.includes('termuxTokenRefresh'),
  },
  codeSignals: {
    workerRecordFunctions: count(/workerRecords|selectWorker|isWorkerLeaseEligible/g, commandCenter),
    shizukuMentions: count(/shizuku|rish/gi, commandCenter + index),
    commandCenterOperationMentions: count(/command_center_operation/g, commandCenter + index),
  },
};
fs.mkdirSync(path.dirname(OUT), {recursive: true});
fs.writeFileSync(OUT, JSON.stringify(result, null, 2) + '\n');
console.log(JSON.stringify({ok: true, output: path.relative(ROOT, OUT), operations: operations.length, automationOperations: automationOperations.length, cloudRunJobConfigured}, null, 2));
