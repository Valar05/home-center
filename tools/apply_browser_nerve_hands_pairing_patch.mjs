import fs from 'node:fs';

function read(file) { return fs.readFileSync(file, 'utf8'); }
function write(file, text) { fs.writeFileSync(file, text, 'utf8'); }
function insertAfter(text, anchor, insertion, label) {
  if (text.includes(insertion.trim())) return text;
  const i = text.indexOf(anchor);
  if (i < 0) throw new Error(`Missing ${label} anchor`);
  return text.slice(0, i + anchor.length) + insertion + text.slice(i + anchor.length);
}
function replaceOnce(text, from, to, label) {
  if (text.includes(to)) return text;
  const i = text.indexOf(from);
  if (i < 0) throw new Error(`Missing ${label} anchor`);
  return text.slice(0, i) + to + text.slice(i + from.length);
}

const apiPath = 'functions/browser_nerve_api.js';
let api = read(apiPath);
api = insertAfter(api,
  "const SUPPORTED_ACTIONS = Object.freeze(['navigate', 'observe', 'find', 'read', 'click', 'type', 'select', 'submit', 'scroll', 'wait_for']);",
  "\nconst COMPUTER_HANDS_TOKEN_COLLECTION = 'computerHandsWorkerTokens';",
  'token collection',
);
api = insertAfter(api,
  "async function exchangeBootstrap({admin, args = {}, nowMs = Date.now()}) {",
  `\n`,
  'exchange bootstrap noop',
);
const authAnchor = "async function authenticateWorker(admin, req, nowMs = Date.now()) {";
const pairingFunctions = `async function authenticateComputerHandsPairing(admin, req, nowMs = Date.now()) {\n  const match = String(req && typeof req.get === 'function' ? req.get('Authorization') || '' : '').match(/^Bearer\\s+(.+)$/i);\n  if (!match) throw Object.assign(new Error('Computer Hands worker bearer token is required for pairing.'), {status: 401, failureKind: 'browser_nerve_hands_auth_required'});\n  const snap = await admin.firestore().collection(COMPUTER_HANDS_TOKEN_COLLECTION).doc(hash(match[1])).get();\n  if (!snap.exists) throw Object.assign(new Error('Computer Hands worker token is invalid.'), {status: 401, failureKind: 'browser_nerve_hands_auth_invalid'});\n  const hands = snap.data() || {};\n  if (hands.revokedAtMs || Number(hands.expiresAtMs || 0) <= nowMs) throw Object.assign(new Error('Computer Hands worker token is inactive.'), {status: 401, failureKind: 'browser_nerve_hands_auth_inactive'});\n  const headerWorker = safeId(req.get('X-Home-Center-Worker') || hands.workerId, 'computerHandsWorkerId');\n  if (headerWorker !== hands.workerId) throw Object.assign(new Error('Computer Hands worker identity mismatch.'), {status: 403, failureKind: 'browser_nerve_hands_worker_mismatch'});\n  if (!hands.ownerKey || !hands.ownerEmail) throw Object.assign(new Error('Computer Hands worker owner identity is incomplete.'), {status: 403, failureKind: 'browser_nerve_hands_owner_missing'});\n  return hands;\n}\n\nfunction pairedBrowserWorkerId(value) {\n  const workerId = safeId(value || 'windows-browser-nerve-01', 'workerId');\n  if (!/^windows-browser-nerve-[A-Za-z0-9_.:-]+$/.test(workerId)) throw Object.assign(new Error('Paired Browser Nerve workerId must begin with windows-browser-nerve-.'), {status: 400, failureKind: 'browser_nerve_pair_worker_invalid'});\n  return workerId;\n}\n\nasync function pairWithComputerHands({admin, req, args = {}, nowMs = Date.now()}) {\n  const hands = await authenticateComputerHandsPairing(admin, req, nowMs);\n  const workerId = pairedBrowserWorkerId(args.workerId);\n  const token = randomBytes(32).toString('base64url');\n  const tokenDigest = hash(token);\n  const workerRef = admin.firestore().collection(COLLECTIONS.workers).doc(workerDocId(hands.ownerKey, workerId));\n  await admin.firestore().runTransaction(async (tx) => {\n    tx.set(admin.firestore().collection(COLLECTIONS.tokens).doc(tokenDigest), {\n      tokenDigest, workerId, ownerKey: hands.ownerKey, ownerEmail: hands.ownerEmail, capabilities: SUPPORTED_ACTIONS,\n      pairedFromComputerHandsWorkerId: hands.workerId, createdAtMs: nowMs, expiresAtMs: nowMs + TOKEN_TTL_MS, revokedAtMs: 0,\n    }, {merge: false});\n    tx.set(workerRef, {\n      apiVersion: API_VERSION, contractVersion: CONTRACT_VERSION, workerId, ownerKey: hands.ownerKey, ownerEmail: hands.ownerEmail,\n      capabilities: SUPPORTED_ACTIONS, selectorPolicy: 'aria_role_name_then_testid_id_css_then_text', state: 'registered',\n      pairedFromComputerHandsWorkerId: hands.workerId, tokenDigest, createdAtMs: nowMs, updatedAtMs: nowMs, lastSeenAtMs: nowMs,\n    }, {merge: true});\n  });\n  return {status: 'registered', workerId, token, origin: PUBLIC_ORIGIN, contractVersion: CONTRACT_VERSION, expiresAtMs: nowMs + TOKEN_TTL_MS, pairedFrom: 'computer_hands', computerHandsWorkerId: hands.workerId};\n}\n\n`;
api = insertAfter(api, authAnchor, pairingFunctions, 'pairing functions');
api = replaceOnce(api,
  "      if (req.method === 'POST' && path === 'bootstrap') return send(res, 200, await exchangeBootstrap({admin, args: bodyObject(req)}));\n      const worker = await authenticateWorker(admin, req);",
  "      if (req.method === 'POST' && path === 'bootstrap') return send(res, 200, await exchangeBootstrap({admin, args: bodyObject(req)}));\n      if (req.method === 'POST' && path === 'pair-computer-hands') return send(res, 200, await pairWithComputerHands({admin, req, args: bodyObject(req)}));\n      const worker = await authenticateWorker(admin, req);",
  'pair route',
);
api = replaceOnce(api,
  "  ownerKey, actionName, registerWorkerOperation, workerStatusOperation, enqueueBrowserNerveTicket,",
  "  ownerKey, actionName, pairedBrowserWorkerId, pairWithComputerHands, registerWorkerOperation, workerStatusOperation, enqueueBrowserNerveTicket,",
  'pair exports',
);
api = replaceOnce(api,
  "  API_VERSION, CONTRACT_VERSION, PUBLIC_ORIGIN, COLLECTIONS, SUPPORTED_ACTIONS,",
  "  API_VERSION, CONTRACT_VERSION, PUBLIC_ORIGIN, COLLECTIONS, SUPPORTED_ACTIONS, COMPUTER_HANDS_TOKEN_COLLECTION,",
  'pair constant export',
);
write(apiPath, api);

const installerPath = 'browser-nerve/windows/install.ps1';
let installer = read(installerPath);
installer = replaceOnce(installer,
  "  [string]$SourceDirectory = '',\n  [switch]$ForceRefreshToken",
  "  [string]$SourceDirectory = '',\n  [switch]$PairWithComputerHands,\n  [switch]$ForceRefreshToken",
  'pair installer parameter',
);
const tokenOld = `if ($needsToken) {\n  if ([string]::IsNullOrWhiteSpace($BootstrapCode)) { throw 'BootstrapCode is required for first install or -ForceRefreshToken.' }\n  $registration = Invoke-RestMethod -Method Post -Uri "$Origin/browser-nerve/v1/bootstrap" -ContentType 'application/json' -Body (@{bootstrapCode=$BootstrapCode;workerId=$WorkerId}|ConvertTo-Json -Compress) -TimeoutSec 30\n  if (-not $registration.token) { throw 'Browser Nerve bootstrap did not return a worker token.' }\n  $secure = ConvertTo-SecureString ([string]$registration.token) -AsPlainText -Force\n  $secure | ConvertFrom-SecureString | Set-Content -LiteralPath $TokenPath -Encoding ASCII\n} else { Write-Host 'Existing DPAPI worker token retained.' }`;
const tokenNew = `if ($needsToken) {\n  if (-not [string]::IsNullOrWhiteSpace($BootstrapCode)) {\n    $registration = Invoke-RestMethod -Method Post -Uri "$Origin/browser-nerve/v1/bootstrap" -ContentType 'application/json' -Body (@{bootstrapCode=$BootstrapCode;workerId=$WorkerId}|ConvertTo-Json -Compress) -TimeoutSec 30\n  } elseif ($PairWithComputerHands) {\n    $handsConfigPath = Join-Path $env:LOCALAPPDATA 'HomeCenter\\ComputerHands\\config.json'\n    if (-not (Test-Path -LiteralPath $handsConfigPath -PathType Leaf)) { throw "Computer Hands config not found for secure pairing: $handsConfigPath" }\n    $handsConfig = Get-Content -LiteralPath $handsConfigPath -Raw | ConvertFrom-Json\n    if (-not $handsConfig.workerId -or -not $handsConfig.tokenPath) { throw 'Computer Hands config is incomplete for secure pairing.' }\n    $serializedHandsToken = (Get-Content -LiteralPath ([string]$handsConfig.tokenPath) -Raw).Trim()\n    $handsSecure = $serializedHandsToken | ConvertTo-SecureString\n    $handsPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($handsSecure)\n    try {\n      $handsToken = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($handsPtr)\n      $headers = @{Authorization="Bearer $handsToken";'X-Home-Center-Worker'=[string]$handsConfig.workerId}\n      $registration = Invoke-RestMethod -Method Post -Uri "$Origin/browser-nerve/v1/pair-computer-hands" -Headers $headers -ContentType 'application/json' -Body (@{workerId=$WorkerId}|ConvertTo-Json -Compress) -TimeoutSec 30\n    } finally {\n      [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($handsPtr)\n    }\n  } else {\n    throw 'First install requires -BootstrapCode or -PairWithComputerHands.'\n  }\n  if (-not $registration.token) { throw 'Browser Nerve registration did not return a worker token.' }\n  $secure = ConvertTo-SecureString ([string]$registration.token) -AsPlainText -Force\n  $secure | ConvertFrom-SecureString | Set-Content -LiteralPath $TokenPath -Encoding ASCII\n} else { Write-Host 'Existing DPAPI worker token retained.' }`;
installer = replaceOnce(installer, tokenOld, tokenNew, 'pair installer token exchange');
write(installerPath, installer);

const testPath = 'functions/browser_nerve_api.test.js';
let test = read(testPath);
test = replaceOnce(test,
  "const {CONTRACT_VERSION, SUPPORTED_ACTIONS, ownerKey, actionName} = require('./browser_nerve_api');",
  "const {CONTRACT_VERSION, SUPPORTED_ACTIONS, COMPUTER_HANDS_TOKEN_COLLECTION, ownerKey, actionName, pairedBrowserWorkerId} = require('./browser_nerve_api');",
  'pair test import',
);
test += `\n\ntest('Computer Hands pairing is explicitly scoped to Browser Nerve worker identities', () => {\n  assert.equal(COMPUTER_HANDS_TOKEN_COLLECTION, 'computerHandsWorkerTokens');\n  assert.equal(pairedBrowserWorkerId('windows-browser-nerve-01'), 'windows-browser-nerve-01');\n  assert.throws(() => pairedBrowserWorkerId('windows-hands-01'), /must begin with windows-browser-nerve-/);\n});\n`;
write(testPath, test);

console.log(JSON.stringify({ok:true, apiPairRoute:api.includes('pair-computer-hands'), installerPairMode:installer.includes('PairWithComputerHands'), tests:test.includes('Computer Hands pairing')}));
