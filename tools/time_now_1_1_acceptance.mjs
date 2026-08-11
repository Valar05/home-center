import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';

const src = fs.readFileSync('functions/home_center_mcp.js', 'utf8');
const start = src.indexOf('function timeNowOperationEntries()');
const end = src.indexOf('function driveOperationRegistry()', start);
assert.ok(start >= 0 && end > start, 'time.now helper block present');
const block = src.slice(start, end) + '\nthis.timeNowOperationEntries=timeNowOperationEntries; this.timeNowOperation=timeNowOperation;';
const ctx = {Intl, Date};
vm.createContext(ctx);
vm.runInContext(block, ctx);
const op = ctx.timeNowOperation;
const entries = ctx.timeNowOperationEntries;
let passed = 0;
const test = (name, fn) => { fn(); passed += 1; console.log(`ok ${passed} - ${name}`); };

test('registry exposes literal time.now', () => assert.ok(entries()['time.now']));
test('operation is read only', () => assert.equal(entries()['time.now'].write, false));
test('raw timestamp is UTC ISO', () => assert.equal(op(new Date('2026-08-11T23:20:00Z')).rawTimestamp, '2026-08-11T23:20:00.000Z'));
test('unix milliseconds match source', () => assert.equal(op(new Date('2026-08-11T23:20:00Z')).unixMs, Date.parse('2026-08-11T23:20:00Z')));
test('source timezone is identified', () => assert.equal(op(new Date('2026-08-11T23:20:00Z')).sourceTimezone, 'UTC'));
test('Chicago summer date renders correctly', () => assert.equal(op(new Date('2026-08-11T23:20:00Z')).local.date, '2026-08-11'));
test('Chicago summer time renders correctly', () => assert.equal(op(new Date('2026-08-11T23:20:00Z')).local.time, '18:20:00'));
test('Chicago summer offset is CDT -05:00', () => assert.equal(op(new Date('2026-08-11T23:20:00Z')).local.utcOffset, '-05:00'));
test('Chicago winter offset is CST -06:00', () => assert.equal(op(new Date('2026-01-11T23:20:00Z')).local.utcOffset, '-06:00'));
test('Chicago ISO rendering carries date-aware offset', () => assert.equal(op(new Date('2026-01-11T23:20:00Z')).local.iso8601, '2026-01-11T17:20:00-06:00'));
assert.equal(passed, 10);
console.log('TIME_TRUTH_1_1_PASS=10/10');
