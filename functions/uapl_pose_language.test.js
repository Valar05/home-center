const assert = require('node:assert/strict');
const {
  parseUapl,
  canonicalUapl,
  uaplHash,
  parseUat,
  renderAsciiContactSheet,
  toVectorNoodle,
  expandTiming,
} = require('./uapl_pose_language');

const jab = `UAPL 1
NAME jab
AXES X=right Y=up Z=forward
RIG humanoid17
JOINT P ROOT
JOINT C P
JOINT N C
JOINT H N
JOINT LS N
JOINT LE LS
JOINT LW LE
JOINT RS N
JOINT RE RS
JOINT RW RE
JOINT LH P
JOINT LK LH
JOINT LA LK
JOINT LF LA
JOINT RH P
JOINT RK RH
JOINT RA RK
JOINT RF RA
POSE guard
P 0 0 0
C 0 2 0
N 0 4 0
H 0 6 0
LS -1 4 0
LE -2 3 0
LW -1 5 0
RS 1 4 0
RE 2 3 0
RW 1 5 0
LH -1 -1 0
LK -2 -3 0
LA -2 -5 0
LF -3 -5 0
RH 1 -1 0
RK 2 -3 0
RA 2 -5 0
RF 3 -5 0
ENDPOSE
POSE load
P 0 0 0
C 0 2 0
N -1 4 0
H -1 6 0
LS -2 4 0
LE -3 3 0
LW -2 5 0
RS 0 4 0
RE 1 3 0
RW 0 5 0
LH -1 -1 0
LK -2 -3 0
LA -2 -5 0
LF -3 -5 0
RH 1 -1 0
RK 2 -3 0
RA 2 -5 0
RF 3 -5 0
ENDPOSE
POSE contact
P 0 0 0
C 1 2 0
N 2 4 0
H 2 6 0
LS 1 4 0
LE 0 3 0
LW 1 5 0
RS 3 4 0
RE 5 4 0
RW 7 4 0
LH -1 -1 0
LK -2 -3 0
LA -2 -5 0
LF -3 -5 0
RH 1 -1 0
RK 2 -3 0
RA 2 -5 0
RF 3 -5 0
ENDPOSE
POSE recoil
P 0 0 0
C 0 2 0
N 1 4 0
H 1 6 0
LS 0 4 0
LE -1 3 0
LW 0 5 0
RS 2 4 0
RE 3 3 0
RW 2 5 0
LH -1 -1 0
LK -2 -3 0
LA -2 -5 0
LF -3 -5 0
RH 1 -1 0
RK 2 -3 0
RA 2 -5 0
RF 3 -5 0
ENDPOSE
POSE settle
P 0 0 0
C 0 2 0
N 0 4 0
H 0 6 0
LS -1 4 0
LE -2 3 0
LW -1 5 0
RS 1 4 0
RE 2 3 0
RW 1 5 0
LH -1 -1 0
LK -2 -3 0
LA -2 -5 0
LF -3 -5 0
RH 1 -1 0
RK 2 -3 0
RA 2 -5 0
RF 3 -5 0
ENDPOSE
ORDER guard load contact recoil settle
ENDUAPL
`;

const program = parseUapl(jab);
assert.equal(program.name, 'jab');
assert.equal(program.joints.length, 18);
assert.deepEqual(program.order, ['guard', 'load', 'contact', 'recoil', 'settle']);

const canonical = canonicalUapl(program);
assert.equal(canonicalUapl(parseUapl(canonical)), canonical, 'canonicalization must be idempotent');
assert.equal(uaplHash(jab), uaplHash(canonical), 'formatting/comments must not change canonical identity');
assert.match(uaplHash(jab), /^[a-f0-9]{64}$/);

const sheetA = renderAsciiContactSheet(jab);
const sheetB = renderAsciiContactSheet(canonical);
assert.equal(sheetA, sheetB, 'same canonical source must render the same ASCII contact sheet');
assert.match(sheetA, /guard/);
assert.match(sheetA, /contact/);
assert.match(sheetA, /\*/);
assert.match(sheetA, /\+/);

const noodleA = toVectorNoodle(jab);
const noodleB = toVectorNoodle(canonical);
assert.deepEqual(noodleA, noodleB, 'vector noodle must be a deterministic projection of UAPL');
assert.equal(noodleA.sourceSha256, uaplHash(jab));
assert.equal(noodleA.poses[2].name, 'contact');
assert.deepEqual(noodleA.poses[2].joints.find((joint) => joint.id === 'RW').xyz, [7, 4, 0]);

const timing = `UAT 1
SOURCE ${uaplHash(jab)}
FPS 60
STEP guard 4
STEP load 2
STEP contact 1
STEP recoil 2
STEP settle 3
ENDUAT
`;
const uat = parseUat(timing, jab);
assert.equal(uat.fps, 60);
assert.deepEqual(expandTiming(uat), [
  'guard','guard','guard','guard',
  'load','load',
  'contact',
  'recoil','recoil',
  'settle','settle','settle',
]);

assert.throws(
  () => parseUat(timing.replace(uaplHash(jab), '0'.repeat(64)), jab),
  (error) => error && error.code === 'UAT_SOURCE_MISMATCH',
  'timing must refuse a stale/different pose source',
);

assert.throws(
  () => parseUapl(jab.replace('RW 7 4 0\n', '')),
  (error) => error && error.code === 'UAPL_INCOMPLETE_POSE',
  'a pose cannot omit a joint',
);

assert.throws(
  () => parseUapl(jab.replace('JOINT C P', 'JOINT C N')),
  (error) => error && error.code === 'UAPL_CYCLE',
  'rig cycles must reject deterministically',
);

console.log('UAPL_CONTRACT_OK');
console.log(uaplHash(jab));
console.log(sheetA);
