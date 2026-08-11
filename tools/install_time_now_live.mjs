import fs from 'node:fs';

const path = 'functions/home_center_mcp.js';
let src = fs.readFileSync(path, 'utf8');

const helper = String.raw`
function timeNowOperationEntries() {
  return {
    'time.now': {
      summary: 'Return the current system clock with raw UTC timestamp plus date-aware America/Chicago rendering. Read-only and model-free.',
      write: false,
      requiresRequestId: false,
      requiredScopes: [],
      input: {},
      output: {
        rawTimestamp: 'ISO-8601 UTC timestamp',
        unixMs: 'integer Unix epoch milliseconds',
        sourceTimezone: 'UTC',
        local: 'America/Chicago date/time, UTC offset, and CST/CDT abbreviation',
      },
      agentRecipe: {
        whenUserSays: 'What time/date is it, praise the Sun, daily update, or any task whose correctness depends on the real current date.',
        prefer: 'Call drive_operation with operation=time.now before reasoning about the current date/time.',
        verification: 'Use rawTimestamp as source truth and local.timeZone=America/Chicago for local rendering. Never guess the date from conversation context.',
      },
    },
  };
}

function timeNowOperation(now = new Date()) {
  if (!(now instanceof Date) || Number.isNaN(now.getTime())) {
    throw Object.assign(new Error('time.now requires a valid system clock Date.'), {status: 500});
  }
  const timeZone = 'America/Chicago';
  const baseOptions = {
    timeZone,
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
    hourCycle: 'h23',
  };
  const parts = Object.fromEntries(new Intl.DateTimeFormat('en-US', baseOptions).formatToParts(now).filter((p) => p.type !== 'literal').map((p) => [p.type, p.value]));
  const zoneParts = new Intl.DateTimeFormat('en-US', {timeZone, timeZoneName: 'short'}).formatToParts(now);
  const offsetParts = new Intl.DateTimeFormat('en-US', {timeZone, timeZoneName: 'shortOffset'}).formatToParts(now);
  const abbreviation = (zoneParts.find((p) => p.type === 'timeZoneName') || {}).value || '';
  const gmtOffset = (offsetParts.find((p) => p.type === 'timeZoneName') || {}).value || 'GMT';
  const match = /^GMT([+-])(\d{1,2})(?::(\d{2}))?$/.exec(gmtOffset);
  const offset = match ? match[1] + String(match[2]).padStart(2, '0') + ':' + (match[3] || '00') : '+00:00';
  const localDate = parts.year + '-' + parts.month + '-' + parts.day;
  const localTime = parts.hour + ':' + parts.minute + ':' + parts.second;
  return {
    ok: true,
    rawTimestamp: now.toISOString(),
    unixMs: now.getTime(),
    sourceClock: 'runtime-system-clock',
    sourceTimezone: 'UTC',
    local: {
      timeZone,
      date: localDate,
      time: localTime,
      iso8601: localDate + 'T' + localTime + offset,
      utcOffset: offset,
      abbreviation,
    },
  };
}
`;

if (!src.includes('function timeNowOperationEntries()')) {
  const anchor = 'function driveOperationRegistry() {';
  if (!src.includes(anchor)) throw new Error('driveOperationRegistry anchor missing');
  src = src.replace(anchor, helper + '\n' + anchor);
}

if (!src.includes('      ...timeNowOperationEntries(),\n')) {
  const anchor = '      ...tvtroperOperationEntries(),\n';
  if (!src.includes(anchor)) throw new Error('registry spread anchor missing');
  src = src.replace(anchor, anchor + '      ...timeNowOperationEntries(),\n');
}

if (!src.includes("if (operation === 'time.now')")) {
  const anchor = '  if (localVoiceOperationEntries()[operation]) {\n';
  if (!src.includes(anchor)) throw new Error('dispatcher anchor missing');
  const dispatch = "  if (operation === 'time.now') {\n    const result = timeNowOperation();\n    return {operation, registryVersion: registry.version, completed: true, result};\n  }\n";
  src = src.replace(anchor, dispatch + anchor);
}

fs.writeFileSync(path, src);
console.log('time.now installed in stable drive_operation pump');
