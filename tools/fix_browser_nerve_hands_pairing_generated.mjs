import fs from 'node:fs';

const file = 'functions/browser_nerve_api.js';
let text = fs.readFileSync(file, 'utf8');
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
fs.writeFileSync(file, text, 'utf8');
console.log(JSON.stringify({ok:true, pairingPlacement:'module_scope'}));
