#!/usr/bin/env node
const fs = require('fs');
const vm = require('vm');

const source = fs.readFileSync('functions/index.js', 'utf8');
const start = source.indexOf('function numberWordToInt');
const stop = source.indexOf('async function askOpenAIToolTurn');
if (start < 0 || stop < start) {
  throw new Error('Could not locate calendar relative-time helpers');
}
const helpers = source.slice(start, stop);
const sandbox = {
  Number,
  Date,
  String,
  RegExp,
  Math,
  safeText(value, limit) {
    const text = String(value || '');
    return text.length > limit ? text.slice(0, limit) : text;
  },
  normalizedReferenceLiteral(value) {
    return String(value || '').trim().toLowerCase().replace(/^['"]|['"]$/g, '').replace(/\s+/g, ' ');
  },
};
vm.createContext(sandbox);
vm.runInContext(`${helpers}\nthis.resolveCalendarRelativeTimesFromContext = resolveCalendarRelativeTimesFromContext;`, sandbox);

const body = {
  timeContext: {
    nowEpochMillis: Date.parse('2026-06-27T12:00:00-05:00'),
    nowIso: '2026-06-27T12:00:00-05:00',
    timeZoneId: 'America/Chicago',
    timeZoneOffsetMillis: -5 * 60 * 60 * 1000,
  },
};
const args = {title: 'home center notification', startTime: 'five minutes from now'};
sandbox.resolveCalendarRelativeTimesFromContext(body, 'calendar.create_event', args);
if (args.startTime !== '2026-06-27T12:05:00-05:00') {
  throw new Error(`bad startTime: ${args.startTime}`);
}
if (args.endTime !== '2026-06-27T12:20:00-05:00') {
  throw new Error(`bad notification endTime: ${args.endTime}`);
}
if (/five minutes|from now/i.test(`${args.startTime} ${args.endTime}`)) {
  throw new Error(`relative text leaked into calendar args: ${JSON.stringify(args)}`);
}
const generic = {title: 'check oven', startTime: 'in 2 hours'};
sandbox.resolveCalendarRelativeTimesFromContext(body, 'calendar.create_event', generic);
if (generic.startTime !== '2026-06-27T14:00:00-05:00' || generic.endTime !== '2026-06-27T14:30:00-05:00') {
  throw new Error(`bad generic event times: ${JSON.stringify(generic)}`);
}
console.log('Home Center calendar relative-time test: OK');
