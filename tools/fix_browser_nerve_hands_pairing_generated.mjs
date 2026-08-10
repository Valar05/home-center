import fs from 'node:fs';

const apiFile = 'functions/browser_nerve_api.js';
let text = fs.readFileSync(apiFile, 'utf8');
const authDecl = "async function authenticateWorker(admin, req, nowMs = Date.now()) {\n";
const nestedStart = `${authDecl}async function authenticateComputerHandsPairing`;
const authBodyAnchor = "  const snap = await admin.firestore().collection(COLLECTIONS.tokens).doc(hash(bearer(req))).get();";

if (text.includes(nestedStart)) {
  const declIndex = text.indexOf(authDecl);
  const blockStart = declIndex + authDecl.length;
  const bodyIndex = text.indexOf(authBodyAnchor, blockStart);
  if (declIndex < 0 || bodyIndex < 0) throw new Error('Could not locate generated Browser Nerve pairing block.');
  const pairingBlock = text.slice(blockStart, bodyIndex);
  text = text.slice(0, declIndex) + pairingBlock + authDecl + text.slice(bodyIndex);
}
if (!text.includes('async function authenticateComputerHandsPairing')) throw new Error('Pairing function is missing after placement fix.');
if (text.includes(nestedStart)) throw new Error('Pairing function remains nested inside authenticateWorker.');
fs.writeFileSync(apiFile, text, 'utf8');

const testFile = 'functions/browser_nerve_api.test.js';
let tests = fs.readFileSync(testFile, 'utf8');
const marker = "test('Computer Hands pairing is explicitly scoped to Browser Nerve worker identities'";
const first = tests.indexOf(marker);
if (first >= 0) {
  const second = tests.indexOf(marker, first + marker.length);
  if (second >= 0) {
    const blockStart = tests.lastIndexOf('\n\n', second);
    const blockEndMarker = '\n});';
    const end = tests.indexOf(blockEndMarker, second);
    if (blockStart < 0 || end < 0) throw new Error('Could not isolate duplicate Browser Nerve pairing test.');
    tests = tests.slice(0, blockStart) + tests.slice(end + blockEndMarker.length);
  }
}
if ((tests.match(/Computer Hands pairing is explicitly scoped to Browser Nerve worker identities/g) || []).length > 1) throw new Error('Duplicate Browser Nerve pairing test remains.');
fs.writeFileSync(testFile, tests, 'utf8');

console.log(JSON.stringify({ok:true, pairingPlacement:'module_scope', pairingTestCount:(tests.match(/Computer Hands pairing is explicitly scoped to Browser Nerve worker identities/g) || []).length}));
