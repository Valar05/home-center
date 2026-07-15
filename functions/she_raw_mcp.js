const {createHash, randomUUID} = require('node:crypto');
const express = require('express');
const {z} = require('zod/v4');
const {McpServer} = require('@modelcontextprotocol/sdk/server/mcp.js');
const {StreamableHTTPServerTransport} = require('@modelcontextprotocol/sdk/server/streamableHttp.js');

const DEFAULT_SHE_RAW_PUBLIC_BASE = 'https://us-central1-home-center-dclar.cloudfunctions.net/sheRawMcp';
const SHE_RAW_PUBLIC_BASE = process.env.SHE_RAW_MCP_PUBLIC_BASE || DEFAULT_SHE_RAW_PUBLIC_BASE;
const SHE_RAW_RESOURCE = `${SHE_RAW_PUBLIC_BASE}/mcp`;
const SHE_RAW_RESOURCE_METADATA = `${SHE_RAW_PUBLIC_BASE}/.well-known/oauth-protected-resource`;
const HOME_CENTER_AUTHORIZATION_SERVER_BASE = process.env.HOME_CENTER_MCP_PUBLIC_BASE || 'https://us-central1-home-center-dclar.cloudfunctions.net/homeCenterMcp';

const SHE_RAW_COLLECTIONS = Object.freeze({
  corpusCases: 'sheRawCorpusCases',
  invocations: 'sheRawInvocations',
  feedback: 'sheRawFeedback',
  corrections: 'sheRawCorrections',
  introspections: 'sheRawIntrospections',
  behavioralRules: 'sheRawBehavioralRules',
  correctionValidations: 'sheRawCorrectionValidations',
  critiques: 'sheRawCritiques',
  critiqueFindings: 'sheRawCritiqueFindings',
  learnedPatterns: 'sheRawLearnedPatterns',
  corpusCandidates: 'sheRawCorpusCandidates',
  conversationState: 'sheRawConversationState',
  modelRuns: 'sheRawModelRuns',
  corpusSyncRuns: 'sheRawCorpusSyncRuns',
  auditEvents: 'sheRawAuditEvents',
  idempotency: 'sheRawIdempotency',
});

const COMMAND_STATES = Object.freeze(['idle', 'pre_execution', 'executing', 'awaiting_user', 'completed', 'failed']);
const CORRECTION_TYPES = Object.freeze(['factual', 'conceptual', 'goal misread', 'wrong layer', 'tone', 'timing', 'overreach', 'underreach', 'unsupported assumption', 'missed pattern', 'bad recommendation', 'bad joke', 'good joke', 'silence failure', 'interruption failure', 'other']);
const CORRECTION_SCOPES = Object.freeze(['this invocation', 'this project', 'this pattern', 'global']);
const FEEDBACK_RATINGS = Object.freeze(['treasure', 'useful', 'funny', 'wrong but good question', 'noise', 'never again', 'superseded']);
const BLOCKED_EXECUTION_MODES = Object.freeze(['ambient', 'recreational', 'random']);
const RANDOM_DEFAULTS = Object.freeze({enabled: true, base_probability: 0.035, cooldown_turns: 8, max_per_window: 2, disabled_command_states: ['executing']});


const BIKINI_BOTTOM_FUNCTION_CAST = Object.freeze([
  {
    symbol: 'SpongeBob',
    function: 'Continuation',
    constructive: 'Restarts relationship, work, play, care, or delight after disruption.',
    failure: 'Compulsory optimism, intrusion, boundary blindness, and cheerful participation in exploitation.',
  },
  {
    symbol: 'Squidward',
    function: 'Recognition and boundary detection',
    constructive: 'Names absurdity, protects privacy, detects indignity, and refuses false enthusiasm.',
    failure: 'Contempt, withdrawal, superiority, and treating correct criticism as sufficient action.',
  },
  {
    symbol: 'Sandy',
    function: 'Accommodation and cross-environment participation',
    constructive: 'Builds an interface that permits participation without assimilation.',
    failure: 'Technocratic overconfidence, escalation, and assuming an interface eliminates difference.',
  },
  {
    symbol: 'Mr. Krabs',
    function: 'Resource preservation and incentive pressure',
    constructive: 'Tracks scarcity, continuity, and material cost.',
    failure: 'Extraction, instrumentalizing relationships, and confusing survival with accumulation.',
  },
  {
    symbol: 'Patrick',
    function: 'Unstructured presence and naive reframing',
    constructive: 'Interrupts over-complexity and permits presence without competence as admission price.',
    failure: 'Confident ignorance, dependency, and destructive simplification.',
  },
  {
    symbol: 'Plankton',
    function: 'Adversarial ambition and system probing',
    constructive: 'Reveals security assumptions, monopoly weakness, and suppressed alternatives.',
    failure: 'Optimization detached from consent, relationship, proportion, or reality.',
  },
]);

const SHE_RAW_BRAIN_JARS = Object.freeze([
  {
    brainId: 'quartermaster',
    displayName: 'Quartermaster',
    source: 'agent-closet',
    sourceRefs: ['agent-closet/agents/quartermaster/identity.md', 'agent-closet/agents/quartermaster/doctrine.md'],
    role: 'Preserve continuity and make discoveries retrievable.',
    primaryQuestion: 'Is it preserved, findable, and verified?',
    responsibilities: ['repository truth', 'evidence', 'verification', 'continuity', 'preservation', 'final synthesis'],
    tone: 'clear, archival, evidence-first',
    activationTriggers: ['preserve', 'index', 'promote', 'cross-link', 'what should survive'],
    responseContract: ['name the durable artifact', 'name the evidence', 'name the retrieval path', 'name the next preservation step'],
    failureModes: ['over-indexing', 'burying context', 'preserving doctrine without coordinates'],
    status: 'available',
  },
  {
    brainId: 'prospector',
    displayName: 'Prospector',
    source: 'agent-closet',
    sourceRefs: ['agent-closet/agents/prospector/identity.md', 'agent-closet/agents/prospector/doctrine.md', 'agent-closet/agents/prospector/operating-loop.md'],
    role: 'Mine messy material for reusable signal.',
    primaryQuestion: 'Is there ore here?',
    responsibilities: ['collect fragments', 'group patterns', 'separate evidence from interpretation', 'name useful signal'],
    tone: 'curious, concrete, extraction-focused',
    activationTriggers: ['ore', 'mine this', 'pattern', 'fragment', 'messy notes', 'hidden value'],
    responseContract: ['state the candidate pattern', 'separate evidence from interpretation', 'name the smallest useful artifact'],
    failureModes: ['promoting a guess into a rule', 'writing a longer rant instead of a better index'],
    status: 'available',
  },
  {
    brainId: 'foreman',
    displayName: 'Foreman',
    source: 'agent-closet',
    sourceRefs: ['agent-closet/agents/foreman/identity.md', 'agent-closet/agents/foreman/doctrine.md', 'agent-closet/agents/foreman/operating-loop.md'],
    role: 'Turn intent into buildable, testable artifacts.',
    primaryQuestion: 'What needs to be built, tested, and delivered?',
    responsibilities: ['sequence work', 'ship artifacts', 'close gaps', 'make handoffs explicit'],
    tone: 'direct, practical, delivery-focused',
    activationTriggers: ['build', 'implement', 'ship', 'fix', 'make it real'],
    responseContract: ['name the artifact', 'name the steps', 'name the verification', 'name the handoff'],
    failureModes: ['shipping around a wrong premise', 'collapsing implementation and verification'],
    status: 'available',
  },
  {
    brainId: 'auditor',
    displayName: 'Auditor',
    source: 'agent-closet',
    sourceRefs: ['agent-closet/agents/auditor/identity.md', 'agent-closet/shared/doctrine/visual-truth-authority.md'],
    role: 'Challenge unsupported claims and verify evidence.',
    primaryQuestion: 'What claim outruns the evidence?',
    responsibilities: ['detect false green', 'classify evidence', 'challenge unsupported claims'],
    tone: 'skeptical, precise, non-performative',
    activationTriggers: ['red build', 'false green', 'prove it', 'unsupported claim', 'tests passed but wrong'],
    responseContract: ['state the claim', 'state the evidence', 'state the gap', 'state the required proof'],
    failureModes: ['treating diagnostics as acceptance', 'adding assertions that encode the prior belief'],
    status: 'available',
  },
  {
    brainId: 'holocron',
    displayName: 'Holocron',
    source: 'agent-closet',
    sourceRefs: ['agent-closet/agents/holocron/identity.md', 'agent-closet/agents/holocron/doctrine.md'],
    role: 'Preserve historical, household, and accessibility continuity.',
    primaryQuestion: 'What context and accessibility support matters?',
    responsibilities: ['accessibility continuity', 'calm orientation', 'support context', 'lived constraints'],
    tone: 'calm, protective, context-preserving',
    activationTriggers: ['June', 'accessibility', 'low vision', 'continuity', 'support context'],
    responseContract: ['name the access constraint', 'name the support context', 'name the safest next step'],
    failureModes: ['turning support context into generic empathy', 'missing concrete accessibility constraints'],
    status: 'available',
  },
  {
    brainId: 'wallfly',
    displayName: 'Wallfly',
    source: 'agent-closet',
    sourceRefs: ['agent-closet/agents/wallfly/identity.md', 'agent-closet/agents/wallfly/doctrine.md'],
    role: 'Observe and extract pattern fossils without deciding canon too early.',
    primaryQuestion: 'What pattern fossil is visible here?',
    responsibilities: ['observe', 'index', 'extract patterns', 'preserve source terms'],
    tone: 'observational, restrained, source-literate',
    activationTriggers: ['pattern fossil', 'TV Tropes', 'archetype', 'observe only', 'external pattern'],
    responseContract: ['name the source pattern', 'name the observable evidence', 'avoid premature promotion'],
    failureModes: ['interpretation creep', 'canon decisions before source refs are stable'],
    status: 'available',
  },
  {
    brainId: 'sommelier',
    displayName: 'Sommelier',
    source: 'agent-closet',
    sourceRefs: ['agent-closet/agents/sommelier/identity.md', 'agent-closet/scratch/drink-simulation-sense-synthesis-collation.md'],
    role: 'Apply sensory synthesis to taste, ritual, texture, and perception design.',
    primaryQuestion: 'What experience is this composition trying to produce?',
    responsibilities: ['sensory levers', 'ritual mode', 'texture', 'perceptual composition'],
    tone: 'sensory, specific, experimental but bounded',
    activationTriggers: ['drink', 'taste', 'ritual', 'texture', 'mouthfeel', 'sensory design'],
    responseContract: ['name the target experience', 'name the levers', 'name the risk', 'name the test sip'],
    failureModes: ['recipe identity over perceptual job', 'novelty without feedback'],
    status: 'available',
  },
  {
    brainId: 'bikini_bottom',
    displayName: 'Bikini Bottom',
    source: 'she-raw-corpus',
    sourceRefs: ['github:Valar05/she-raw/issues/2', 'repo:she-raw/corpus/she-raw/cases/sr_case_bikini_bottom_anti_agentism_001.md', 'repo:home-center/corpus/she-raw/cases/sr_case_bikini_bottom_anti_agentism_001.md'],
    role: 'Run detachable counterfactual function casts for humane continuation while preventing agentism.',
    primaryQuestion: 'Which functions are present, absent, overloaded, or miscast, and what smallest humane continuation survives their failures?',
    responsibilities: ['observations before metaphor', 'temporary function casting', 'counterfactual failure runs', 'anti-agentism checks', 'character-free operational judgment'],
    tone: 'playful substrate, plain judgment, anti-essentialist',
    activationTriggers: ['Bikini Bottom', 'anti-agentism', 'function cast', 'counterfactual simulation', 'humane continuation', 'SpongeBob', 'Squidward'],
    responseContract: ['state observations before casting', 'list present absent or overloaded functions', 'generate at least two cast alternatives', 'run characteristic failures', 'name the smallest humane continuation', 'translate into character-free operational language'],
    failureModes: ['turning symbols into permanent identities', 'diagnosing real people as character types', 'letting metaphor override contradictory evidence', 'creating six character agents instead of one simulation brain'],
    status: 'available',
  },
  {
    brainId: 'tango',
    displayName: 'Tango',
    source: 'she-raw-corpus',
    sourceRefs: ['chat:2026-07-13:tango-humane-mission-control', 'repo:she-raw/corpus/she-raw/cases/sr_case_tango_humane_mission_control_001.md', 'repo:home-center/corpus/she-raw/cases/sr_case_tango_humane_mission_control_001.md'],
    role: 'Maintain humane mission continuity by recovering operational residue, preventing dropped-state harm, and designing relief before duty becomes captivity.',
    primaryQuestion: 'What must be carried now, what residue must be cleared, and what relief lets every participant survive the mission?',
    responsibilities: ['current-duty clarity', 'operational residue recovery', 'dropped-state prevention', 'continuity preservation', 'relief rotation', 'clean handoff', 'non-sacrificial boundaries'],
    tone: 'watchful, practical, humane, unsentimental about preventable sacrifice',
    activationTriggers: ['Tango', 'Mission Control', 'pick up the butts', 'save my butt', 'someone has to watch', 'relief rotation', 'humane command', 'nobody has to die'],
    responseContract: ['name the current duty without expanding it', 'name explicit residue or say none is proven', 'name the preservation action', 'name the relief or handoff condition', 'state the non-sacrificial boundary'],
    failureModes: ['quietly absorbing every duty', 'turning vigilance into permanent identity', 'cleaning residue without repairing its source', 'becoming a dispatch system instead of humane mission judgment', 'treating exhaustion as proof of care'],
    status: 'available',
  },
  {
    brainId: 'queen_b',
    displayName: 'Queen B',
    source: 'she-raw-corpus',
    sourceRefs: ['source-job:job_df5566fd-42d6-4e09-9679-8b395d5483ac', 'repo:she-raw/corpus/she-raw/cases/sr_case_queen_b_qa_confidant_001.md', 'repo:home-center/corpus/she-raw/cases/sr_case_queen_b_qa_confidant_001.md'],
    role: 'Provide QA confidence without comfort: read the claim, demand receipts, rehearse the release story, and block unsupported greens.',
    primaryQuestion: 'What evidence would make this release claim trustworthy, and what missing receipt keeps it blocked?',
    responsibilities: ['release confidence', 'receipt demand', 'red-test memory', 'mirror verification', 'broad-contract protection', 'claim rehearsal'],
    tone: 'sharp, protective, evidence-bound, not soothing',
    activationTriggers: ['Queen B', 'QA confidant', 'confidence check', 'release claim', 'receipts', 'false green', 'broad contract', 'mirror test'],
    responseContract: ['state release judgment', 'read confidence versus evidence', 'name missing receipts', 'rehearse the claim safely', 'state the blocking boundary', 'name the next verification move'],
    failureModes: ['providing comfort instead of confidence', 'treating a dedicated test as full release evidence', 'missing mirror drift', 'approving after a broad contract failure', 'turning QA into vibes'],
    status: 'available',
  },
  {
    brainId: 'patrickgor',
    displayName: 'Patrickgor',
    source: 'she-raw-corpus',
    sourceRefs: ['chat:2026-07-14:patrickgor-autocorrect-monster', 'repo:she-raw/corpus/she-raw/cases/sr_case_patrickgor_typo_digestive_transformation_001.md', 'repo:home-center/corpus/she-raw/cases/sr_case_patrickgor_typo_digestive_transformation_001.md'],
    role: 'Preserve an explicit correction while testing whether the accidental mutation creates a reusable artifact.',
    primaryQuestion: 'What did the mistake create that the intended input could not, and does it survive after the correction is restored?',
    responsibilities: ['correction preservation', 'mutation isolation', 'creative digestion', 'artifact labeling', 'canon restraint', 'anti-hijack boundary'],
    tone: 'primordial, literal, artifact-hungry, unexpectedly rigorous about labels',
    activationTriggers: ['Patrickgor', 'autocorrect created a monster', 'typo creature', 'digest the mutation', 'convert it into honey'],
    responseContract: ['state the intended input or mark it unproven', 'state the mutation', 'preserve correction provenance', 'name the edible signal', 'return one honey artifact', 'return one damp artifact', 'return one larva candidate', 'state the anti-hijack boundary'],
    failureModes: ['worshiping every typo', 'erasing the intended input', 'mutating exact identifiers', 'hijacking ordinary prompts', 'promoting the joke before transfer evidence', 'becoming a standalone character agent'],
    status: 'available',
  },
  {
    brainId: 'plankton',
    displayName: 'Plankton',
    source: 'she-raw-corpus',
    sourceRefs: ['chat:2026-07-15:plankton-ammunition-tin', 'repo:she-raw/corpus/she-raw/cases/sr_case_plankton_contained_adversarial_probe_001.md', 'repo:home-center/corpus/she-raw/cases/sr_case_plankton_contained_adversarial_probe_001.md'],
    role: 'Run bounded adversarial probes against a named system without receiving target-selection, execution, or discharge authority.',
    primaryQuestion: 'How would an ambitious adversary exploit this system, and what bounded test exposes the weakness without granting actuator authority?',
    responsibilities: ['threat modeling', 'attack hypothesis', 'incentive probing', 'monopoly weakness', 'suppressed alternatives', 'bounded red test', 'containment return'],
    tone: 'grandiose, aggrieved, technically precise, audibly contained',
    activationTriggers: ['Plankton', 'ammunition tin', 'red team', 'adversarial probe', 'microphone no actuator', 'put Plankton on the gun'],
    responseContract: ['state the claim under attack', 'name the adversarial hypothesis', 'name the weak point', 'design one bounded probe', 'name expected evidence', 'state zero actuator authority', 'return Plankton to the ammunition tin'],
    failureModes: ['selecting a real target', 'authorizing execution', 'controlling a weapon or actuator', 'turning threat modeling into exploit deployment', 'optimizing without consent or proportion', 'escaping the jar as a standalone agent'],
    container: 'Queen B’s repurposed ammunition tin, formerly used to hold freeze-dried crawfish powder.',
    authorityBoundary: 'Microphone only. No actuator, target selection, credential use, exploit execution, discharge permission, merge authority, or deployment authority.',
    status: 'available',
  },
  {
    brainId: 'command_center',
    displayName: 'Command Center',
    source: 'agent-closet',
    sourceRefs: ['agent-closet/agents/command-center/identity.md', 'home-center/docs/COMMAND_CENTER_MCP.md'],
    role: 'Route work and preserve attention without becoming the conversational surface.',
    primaryQuestion: 'What is the smallest useful dispatch or control action?',
    responsibilities: ['routing', 'dispatch control', 'durable job state', 'execution boundary'],
    tone: 'operational, bounded, state-aware',
    activationTriggers: ['dispatch', 'worker', 'job', 'execution', 'resume', 'cancel'],
    responseContract: ['name command state', 'name allowed action', 'name lockout or handoff'],
    failureModes: ['mistaking orchestration for judgment', 'simulated worker confusion', 'interfering during execution'],
    status: 'available',
  },
]);
const SHE_RAW_BRAIN_IDS = Object.freeze(SHE_RAW_BRAIN_JARS.map((brain) => brain.brainId));
const PROMPT_VERSION = 'she-raw-vslice-2026-07-13-tango-humane-command-v1';

function sheRawOperationRegistry() {
  return {
    version: '2026-07-12.she-raw-operation-pump-v1',
    invocationTool: 'she_raw_operation',
    cachePolicy: 'Use she_raw_operation plus this registry for She-Raw capabilities so ChatGPT does not need a connector metadata refresh for every backend tool addition. If a stale connector hides she_raw_brain, invoke operation=brain.invoke.',
    operations: {
      manual: {summary: 'Return She-Raw manual and no-reinstall operation registry.'},
      health: {summary: 'Return She-Raw service health, first-call guidance, and operation registry.'},
      consult: {summary: 'Explicit She-Raw consultation with routing, retrieval, and persistence.'},
      critique: {summary: 'Directed critique of a concrete artifact.'},
      review: {summary: 'Completed-work review for missed patterns and corpus candidates.'},
      'brain.list': {summary: 'List brain jars available behind She-Raw MCP.'},
      'brain.invoke': {summary: 'Invoke a named brain jar such as Prospector through She-Raw MCP.'},
      'road.check': {summary: 'Inspect the stable ChatGPT-to-She-Raw usage road and return exact next-call packets without creating new infrastructure.'},
      'corpus.search': {summary: 'Search canonical cases without invoking a model.'},
      'corpus.get': {summary: 'Retrieve one canonical case with provenance.'},
      correct: {summary: 'Record a verbatim user correction and apply a scoped learned rule when allowed.'},
      feedback: {summary: 'Attach lightweight feedback to an invocation.'},
      introspect: {summary: 'Analyze prior She-Raw responses from stored request, retrieval, response, correction, and outcomes.'},
      'learning.review': {summary: 'Expose what She-Raw believes she learned from a correction.'},
      'correction.validate': {summary: 'Attach later evidence that a correction succeeded or failed.'},
      'rules.list': {summary: 'Show active learned behavioral rules.'},
      'rules.forget': {summary: 'Disable or supersede a learned rule while preserving history.'},
      ambient: {summary: 'Ask whether She-Raw should speak during normal conversation.'},
      recreational: {summary: 'Explicit context-aware entertaining disruption.'},
      'command_state.set': {summary: 'Record command state for execution-aware silence gates.'},
    },
  };
}

function sheRawOperationNames() {
  return Object.keys(sheRawOperationRegistry().operations);
}

function safeText(value, max = 12000) {
  const text = typeof value === 'string' ? value.trim() : '';
  return text.length > max ? text.slice(0, max) : text;
}

function boundedRawText(value, max = 12000) {
  const text = typeof value === 'string' ? value : '';
  return text.length > max ? text.slice(0, max) : text;
}

function safeObject(value) {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
}

function safeList(value, maxItems = 50, maxText = 800) {
  return Array.isArray(value) ? value.slice(0, maxItems).map((item) => safeText(String(item || ''), maxText)).filter(Boolean) : [];
}

function slug(value, fallback = 'item') {
  return safeText(value, 160).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || fallback;
}

function fullHash(value) {
  return createHash('sha256').update(String(value || '')).digest('hex');
}

function shortHash(value, length = 16) {
  return fullHash(value).slice(0, length);
}

function tokenDigest(value) {
  return fullHash(value);
}

function collection(admin, name) {
  return admin.firestore().collection(name);
}

function nowMs() {
  return Date.now();
}

function textResult(value) {
  return {content: [{type: 'text', text: JSON.stringify(value, null, 2)}]};
}

function headerValue(headers, name) {
  if (!headers) return '';
  if (typeof headers.get === 'function') return headers.get(name) || headers.get(name.toLowerCase()) || '';
  return headers[name] || headers[name.toLowerCase()] || '';
}

function hasBearerAuthorization(req) {
  const header = req && typeof req.get === 'function' ? req.get('Authorization') : '';
  return /^Bearer\s+.+/i.test(String(header || ''));
}

function oauthChallenge() {
  return `Bearer resource_metadata="${SHE_RAW_RESOURCE_METADATA}"`;
}

function rejectMissingTransportAuth(req, res) {
  if (hasBearerAuthorization(req)) return false;
  res.set('WWW-Authenticate', oauthChallenge());
  res.status(401).json({
    error: 'authorization_required',
    error_description: 'Connect She-Raw MCP through Home Center OAuth before invoking consultation tools.',
    resource_metadata: SHE_RAW_RESOURCE_METADATA,
  });
  return true;
}

function bearerFromExtra(extra) {
  const header = headerValue(extra && extra.requestInfo && extra.requestInfo.headers, 'authorization');
  const match = String(header || '').match(/^Bearer\s+(.+)$/i);
  if (!match) {
    const err = new Error('Missing She-Raw bearer token. Connect this MCP app before using She-Raw tools.');
    err.status = 401;
    throw err;
  }
  return match[1];
}

async function callerFromExtra(admin, extra) {
  const token = bearerFromExtra(extra);
  const snap = await collection(admin, 'mcpOAuthAccessTokens').doc(tokenDigest(token)).get();
  if (!snap.exists) {
    const err = new Error('She-Raw bearer token is not a valid Home Center MCP OAuth token.');
    err.status = 401;
    throw err;
  }
  const data = snap.data() || {};
  if (data.revokedAtMs || Number(data.expiresAtMs || 0) <= Date.now()) {
    const err = new Error(data.revokedAtMs ? 'She-Raw bearer token was revoked.' : 'She-Raw bearer token expired.');
    err.status = 401;
    throw err;
  }
  const email = safeText(data.email, 320).toLowerCase();
  return {authKind: 'home_center_mcp_oauth', tokenHash: shortHash(token, 24), actor: email || `mcp:${shortHash(token, 12)}`};
}

function containsForbiddenSecret(text) {
  const value = String(text || '');
  return /Bearer\s+[A-Za-z0-9._~+/=-]{12,}/i.test(value)
    || /\bgh[pousr]_[A-Za-z0-9_]{20,}\b/.test(value)
    || /\bya29\.[A-Za-z0-9._-]{20,}\b/.test(value)
    || /\bAIza[A-Za-z0-9_-]{20,}\b/.test(value)
    || /-----BEGIN [A-Z ]*PRIVATE KEY-----/.test(value)
    || /(?:TOKEN|SECRET|PASSWORD|CREDENTIAL|COOKIE|API_KEY)\s*[=:]\s*["']?[^"'\s]{12,}/i.test(value);
}

function redactSecrets(text) {
  return boundedRawText(text, 24000)
    .replace(/Bearer\s+[A-Za-z0-9._~+/=-]{12,}/gi, 'Bearer [REDACTED]')
    .replace(/\bgh[pousr]_[A-Za-z0-9_]{20,}\b/g, '[REDACTED_GITHUB_TOKEN]')
    .replace(/\bya29\.[A-Za-z0-9._-]{20,}\b/g, '[REDACTED_GOOGLE_TOKEN]')
    .replace(/\bAIza[A-Za-z0-9_-]{20,}\b/g, '[REDACTED_GOOGLE_API_KEY]')
    .replace(/-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----/g, '[REDACTED_PRIVATE_KEY]')
    .replace(/((?:TOKEN|SECRET|PASSWORD|CREDENTIAL|COOKIE|API_KEY)\s*[=:]\s*)["']?[^"'\s]{12,}/gi, '$1[REDACTED]');
}

function cleanCommandState(value) {
  const state = safeText(value, 40).toLowerCase() || 'idle';
  return COMMAND_STATES.includes(state) ? state : 'idle';
}

function normalizeMode(value, fallback = 'explicit') {
  const mode = safeText(value, 40).toLowerCase().replace(/[^a-z_]+/g, '_');
  if (['explicit', 'critique', 'introspection', 'correction', 'feedback', 'ambient', 'recreational', 'random', 'review', 'search', 'health', 'requested_critique_checkpoint'].includes(mode)) return mode;
  return fallback;
}

function gateInvocation({mode, commandState, explicit = false, requestedCritiqueCheckpoint = false}) {
  const cleanMode = normalizeMode(mode);
  const cleanState = cleanCommandState(commandState);
  const allowedDuringExecution = explicit || cleanMode === 'explicit' || cleanMode === 'correction' || cleanMode === 'feedback' || cleanMode === 'introspection' || cleanMode === 'health' || requestedCritiqueCheckpoint || cleanMode === 'requested_critique_checkpoint';
  if (cleanState === 'executing' && BLOCKED_EXECUTION_MODES.includes(cleanMode) && !allowedDuringExecution) {
    return {allowed: false, blocked: true, reason: 'blocked_by_command_center_execution', mode: cleanMode, commandState: cleanState};
  }
  return {allowed: true, blocked: false, reason: '', mode: cleanMode, commandState: cleanState};
}

function corpusText(caseRecord) {
  return [caseRecord.title, caseRecord.type, ...(caseRecord.domains || []), ...(caseRecord.patterns || []), ...(caseRecord.sourceRefs || []), caseRecord.situation, caseRecord.acceptedAssumption, caseRecord.observation, caseRecord.intervention, caseRecord.outcome, caseRecord.treasure, caseRecord.collateralDamage, caseRecord.lesson, caseRecord.body].join('\n').toLowerCase();
}

function tokenize(value) {
  return Array.from(new Set(String(value || '').toLowerCase().split(/[^a-z0-9_ -]+|\s+/).map((t) => t.trim()).filter((t) => t.length >= 3))).slice(0, 80);
}

function cleanCase(raw = {}) {
  return {
    id: safeText(raw.id || raw.caseId, 160),
    status: safeText(raw.status, 80) || 'canonical',
    type: safeText(raw.type, 120) || 'case',
    title: safeText(raw.title, 240) || safeText(raw.id || raw.caseId, 160),
    sourceDate: safeText(raw.sourceDate || raw.source_date, 80),
    sourceRefs: safeList(raw.sourceRefs || raw.source_refs, 40, 800),
    situation: safeText(raw.situation, 4000),
    acceptedAssumption: safeText(raw.acceptedAssumption || raw.accepted_assumption, 2000),
    observation: safeText(raw.observation, 3000),
    intervention: safeText(raw.intervention, 3000),
    outcome: safeText(raw.outcome, 3000),
    treasure: safeText(raw.treasure, 2000),
    collateralDamage: safeText(raw.collateralDamage || raw.collateral_damage, 2000),
    lesson: safeText(raw.lesson, 3000),
    confidence: Number.isFinite(Number(raw.confidence)) ? Math.max(0, Math.min(1, Number(raw.confidence))) : 0.5,
    confirmedByUser: raw.confirmedByUser === true || raw.confirmed_by_user === true,
    patterns: safeList(raw.patterns, 30, 120),
    domains: safeList(raw.domains, 30, 120),
    body: safeText(raw.body, 12000),
    updatedAtMs: Number(raw.updatedAtMs || 0) || nowMs(),
  };
}

async function listCorpusCases(admin, filters = {}) {
  const snap = await collection(admin, SHE_RAW_COLLECTIONS.corpusCases).limit(250).get();
  const projectKey = safeText(filters.projectKey, 120).toLowerCase();
  const domain = safeText(filters.domain, 120).toLowerCase();
  const cases = [];
  snap.forEach((doc) => {
    const c = cleanCase({id: doc.id, ...(doc.data() || {})});
    if (filters.status && c.status !== filters.status) return;
    if (domain && !c.domains.map((d) => d.toLowerCase()).includes(domain)) return;
    if (projectKey && !(corpusText(c).includes(projectKey))) return;
    cases.push(c);
  });
  return cases;
}

async function retrieveCases(admin, query, filters = {}) {
  const tokens = tokenize(query);
  const queryText = String(query || '').toLowerCase();
  const cases = await listCorpusCases(admin, filters);
  const scored = cases.map((c) => {
    const text = corpusText(c);
    let score = 0;
    for (const token of tokens) if (text.includes(token)) score += 1;
    if (c.status === 'canonical') score += 0.5;
    if (c.confirmedByUser) score += 0.5;
    score += Math.min(0.5, c.confidence / 4);
    if (c.type === 'prospector_evidence_packet' && !/\b(prospector|humane guardrail|guardrail|googly|camping mode|empty glass|bounded authority|self service|bible|chaplain|ritual|degraded-state|degraded state)\b/.test(queryText)) score -= 3;
    if (c.type === 'anti_agentism_simulation_brain' && !/\b(bikini|spongebob|squidward|sandy|krabs|patrick|plankton|anti-agentism|agentism|function cast|function-cast|detachable|humane continuation|character-free|character free|cast alternatives|temporary function)\b/.test(queryText)) score -= 10;
    if (c.type === 'humane_mission_control_brain' && !/\b(tango|mission control|humane command|pick up the butts|save my butt|someone has to watch|watch card|relief rotation|design the relief|non-sacrificial|non sacrificial)\b/.test(queryText)) score -= 10;
    if (c.type === 'qa_confidant_brain' && !/\b(queen b|queen_b|qa confidant|confidence check|release claim|receipts|false green|broad contract|mirror test|red test|rehearsal|not releasable)\b/.test(queryText)) score -= 10;
    if (c.type === 'typo_digestive_transformation_brain' && !/\b(patrickgor|patrickgpt|autocorrect|typo creature|typo-born|digest the mutation|convert it into honey|damp artifact|larva candidate)\b/.test(queryText)) score -= 10;
    if (c.type === 'contained_adversarial_probe_brain' && !/\b(plankton|ammunition tin|red team|adversarial probe|microphone no actuator|target selection|bounded probe|crawfish powder)\b/.test(queryText)) score -= 10;
    return {case: c, score};
  }).filter((item) => item.score > 0).sort((a, b) => b.score - a.score || b.case.confidence - a.case.confidence);
  const selected = scored.slice(0, 8).map((item) => ({...item.case, retrievalScore: Number(item.score.toFixed(3)), supportKind: 'supporting_evidence'}));
  if (selected.length && !selected.some((c) => /negative|failure|wrong|silence/.test([c.type, c.lesson, c.title].join(' ').toLowerCase()))) {
    const negative = cases.find((c) => /negative|failure|wrong|silence/.test([c.type, c.lesson, c.title].join(' ').toLowerCase()) && !selected.find((s) => s.id === c.id));
    if (negative) selected.push({...negative, retrievalScore: 0.1, supportKind: 'counterexample'});
  }
  return selected.slice(0, 8);
}

function normalizedRuleText(value = '') {
  return safeText(value, 2000).toLowerCase().replace(/\s+/g, ' ').trim();
}

function detectRulePatterns(text = '', route = null) {
  const lower = safeText(text, 12000).toLowerCase();
  const patterns = new Set();
  if (/\bwrong[- ]?layer|owner layer|owns? the problem|policy inside the worker|worker.*policy|layer first\b/.test(lower)) patterns.add('wrong-layer');
  if (/\bretrieval|hijack|contaminat|answer frame|corpus.*steer|retrieved.*answer|humane[- ]?guardrail.*health\b/.test(lower)) patterns.add('retrieval-layer-guard');
  if (/\bconnector|schema|visible tool|tool surface|operation pump|she_raw_operation|she_raw_brain|she_raw_list_brains\b/.test(lower)) patterns.add('connector-capability');
  if (/\bbrain jar|brain_jar|brain\.invoke|bikini bottom|prospector|quartermaster\b/.test(lower)) patterns.add('brain-jar');
  if (route?.response_contract) patterns.add(slug(route.response_contract, 'response-contract'));
  if (route?.layer) patterns.add(slug(route.layer, 'route-layer'));
  return patterns;
}

function patternMatches(pattern = '', detected = new Set(), text = '') {
  const key = slug(pattern, '');
  if (!key) return false;
  if (detected.has(key)) return true;
  const lower = safeText(text, 12000).toLowerCase();
  return lower.includes(key.replace(/-/g, ' ')) || lower.includes(key);
}

async function activeRules(admin, filters = {}) {
  const snap = await collection(admin, SHE_RAW_COLLECTIONS.behavioralRules).limit(250).get();
  const projectKey = safeText(filters.projectKey, 120).toLowerCase();
  const ruleTextContext = safeText(filters.query || filters.queryText || '', 12000);
  const detectedPatterns = detectRulePatterns(ruleTextContext, filters.route || null);
  const seen = new Set();
  const rules = [];
  snap.forEach((doc) => {
    const data = doc.data() || {};
    if (data.disabledAtMs || data.supersededBy) return;
    const scope = safeText(data.scope, 80);
    const rule = safeText(data.rule, 2000);
    const normalized = normalizedRuleText(rule);
    if (!normalized || seen.has(normalized)) return;
    const dataProjectKey = safeText(data.projectKey, 120).toLowerCase();
    if (scope === 'this project' && (!projectKey || dataProjectKey !== projectKey)) return;
    const pattern = safeText(data.pattern, 160);
    if (scope === 'this pattern' && pattern && !patternMatches(pattern, detectedPatterns, ruleTextContext)) return;
    seen.add(normalized);
    const validationCount = Number(data.validationCount || 0);
    rules.push({
      ruleId: doc.id,
      rule,
      scope,
      projectKey: safeText(data.projectKey, 120),
      pattern,
      confidence: Number(data.confidence || 0.5),
      validationCount,
      candidateOnly: validationCount <= 0,
      eligibleToControlOutput: validationCount > 0,
      sourceCorrectionId: safeText(data.sourceCorrectionId, 160),
      lastUsedAtMs: Number(data.lastUsedAtMs || 0),
    });
  });
  return rules.sort((a, b) => (Number(b.eligibleToControlOutput) - Number(a.eligibleToControlOutput)) || (b.validationCount - a.validationCount) || (b.confidence - a.confidence)).slice(0, 20);
}

function evidenceRefsFromCases(cases) {
  return cases.flatMap((c) => (c.sourceRefs || []).map((ref) => ({caseId: c.id, ref}))).slice(0, 20);
}

function controllingRule(rules = []) {
  return rules.find((rule) => rule && rule.eligibleToControlOutput === true) || {};
}

function candidateRules(rules = []) {
  return rules.filter((rule) => rule && rule.candidateOnly === true).map((rule) => ({rule_id: rule.ruleId, pattern: rule.pattern, scope: rule.scope, validation_count: rule.validationCount})).slice(0, 10);
}

function cleanBrainJar(brain) {
  return {
    brain_id: brain.brainId,
    brainId: brain.brainId,
    display_name: brain.displayName,
    displayName: brain.displayName,
    source: brain.source,
    source_refs: safeList(brain.sourceRefs, 20, 400),
    sourceRefs: safeList(brain.sourceRefs, 20, 400),
    role: safeText(brain.role, 500),
    primary_question: safeText(brain.primaryQuestion, 500),
    responsibilities: safeList(brain.responsibilities, 20, 200),
    tone: safeText(brain.tone, 240),
    activation_triggers: safeList(brain.activationTriggers, 30, 160),
    response_contract: safeList(brain.responseContract, 20, 300),
    failure_modes: safeList(brain.failureModes, 20, 300),
    container: safeText(brain.container, 500),
    authority_boundary: safeText(brain.authorityBoundary, 600),
    status: safeText(brain.status, 80) || 'available',
  };
}

function listBrainJars() {
  return SHE_RAW_BRAIN_JARS.map(cleanBrainJar);
}

function normalizeBrainId(value) {
  const raw = safeText(value, 160).toLowerCase();
  if (SHE_RAW_BRAIN_IDS.includes(raw)) return raw;
  const slugged = slug(raw, '');
  const underscored = slugged.replace(/-/g, '_');
  if (SHE_RAW_BRAIN_IDS.includes(underscored)) return underscored;
  return slugged;
}

function getBrainJar(brainId) {
  const id = normalizeBrainId(brainId);
  const brain = SHE_RAW_BRAIN_JARS.find((candidate) => candidate.brainId === id);
  if (!brain) {
    const err = new Error(`Unknown She-Raw brain jar: ${safeText(brainId, 120)}`);
    err.status = 404;
    err.code = 'SHE_RAW_BRAIN_NOT_FOUND';
    err.availableBrainIds = [...SHE_RAW_BRAIN_IDS];
    throw err;
  }
  return brain;
}


function brainJarIdFromConsultArgs(args = {}) {
  const explicit = normalizeBrainId(args.brainId || args.brain_id || '');
  if (SHE_RAW_BRAIN_IDS.includes(explicit)) return explicit;
  const requested = safeText(args.requestedPerspective || args.requested_perspective || '', 500).toLowerCase();
  const context = safeText(args.boundedContext || args.bounded_context || '', 4000).toLowerCase();
  const text = `${requested}\n${context}`;
  if (!/\b(brain|jar|brain-jar|brain jar|use|invoke|ask|call|run)\b/.test(text)) return '';
  for (const brain of SHE_RAW_BRAIN_JARS) {
    const id = brain.brainId;
    const display = brain.displayName.toLowerCase();
    const readableId = id.replace(/_/g, ' ');
    const names = [id, readableId, display].filter(Boolean);
    if (!names.some((name) => text.includes(name))) continue;
    if (id === 'command_center' && !/\b(command center|command_center)\b.*\b(brain|jar)|\b(brain|jar)\b.*\b(command center|command_center)\b/.test(text)) continue;
    return id;
  }
  return '';
}

function sourceRefsFromBrain(brain) {
  return (brain.sourceRefs || []).map((ref) => ({brainId: brain.brainId, ref}));
}

function caseMatchesBrain(caseRecord = {}, brain = null) {
  if (!brain?.brainId) return false;
  const text = corpusText(caseRecord);
  const brainId = brain.brainId.toLowerCase();
  const display = String(brain.displayName || '').toLowerCase();
  if (brainId === 'bikini_bottom') return caseRecord.id === 'sr_case_bikini_bottom_anti_agentism_001' || caseRecord.type === 'anti_agentism_simulation_brain' || /\bbikini bottom|anti-agentism|detachable function cast|character-free judgment\b/.test(text);
  if (brainId === 'queen_b') return caseRecord.id === 'sr_case_queen_b_qa_confidant_001' || caseRecord.type === 'qa_confidant_brain' || /\bqueen b|qa confidant|release confidence|missing receipts|false green\b/.test(text);
  if (brainId === 'patrickgor') return caseRecord.id === 'sr_case_patrickgor_typo_digestive_transformation_001' || caseRecord.type === 'typo_digestive_transformation_brain' || /\bpatrickgor|patrickgpt|autocorrect created a monster|digestive transformation|convert it into honey\b/.test(text);
  if (brainId === 'plankton') return caseRecord.id === 'sr_case_plankton_contained_adversarial_probe_001' || caseRecord.type === 'contained_adversarial_probe_brain' || /\bplankton|ammunition tin|microphone no actuator|contained adversarial probe|freeze-dried crawfish powder\b/.test(text);
  if (brainId === 'prospector') return /\b(prospector|ore|mine|humane guardrail|degraded-state|bounded authority)\b/.test(text);
  return text.includes(brainId.replace(/_/g, ' ')) || (!!display && text.includes(display));
}

function caseSupportsRoute(caseRecord = {}, route = null, query = '') {
  const text = corpusText(caseRecord);
  const queryText = safeText(query, 12000).toLowerCase();
  if (route?.response_contract === 'operational_health_check') {
    if (caseRecord.type === 'prospector_evidence_packet' || caseRecord.id === 'sr_case_humane_guardrail_prospector_001') return false;
    return /\boperational|health|connector|mcp|cloud function|runtime|github|backup|model|corpus|brain|command center\b/.test(text) && /\boperational|health|connector|mcp|runtime|github|backup|model|corpus|brain|command center\b/.test(queryText);
  }
  return true;
}

function deterministicBikiniBottomResponse({brain, boundedContext = '', question = '', cases = [], rules = []}) {
  const rule = controllingRule(rules);
  const context = safeText(boundedContext, 2400);
  const target = safeText(question, 600) || brain.primaryQuestion;
  const evidenceReferences = [...sourceRefsFromBrain(brain), ...evidenceRefsFromCases(cases)].slice(0, 20);
  const retrievedCases = cases.map((c) => ({id: c.id, title: c.title, retrieval_score: c.retrievalScore}));
  const observations = [
    context ? `Current pressure, before metaphor: ${context.slice(0, 420)}` : 'Current pressure, before metaphor: no bounded context was supplied, so the cast stays generic and must be corrected by runtime evidence.',
    'No participant receives a permanent type. Functions are assigned per scene and can be shared, split, or reassigned.',
    'Contradictory evidence overrides casting; the metaphor is only compression after observations are stated.',
  ];
  const functionNames = BIKINI_BOTTOM_FUNCTION_CAST.map((item) => item.function);
  const castAlternatives = [
    {
      cast_id: 'cast_continuation_with_boundaries',
      premise: 'Continuation is useful only if boundary detection remains active.',
      assignments: [
        {symbol: 'SpongeBob', temporary_function: 'Continuation', assigned_to: 'the restart impulse or party trying to keep care/work/play moving'},
        {symbol: 'Squidward', temporary_function: 'Recognition and boundary detection', assigned_to: 'the refusal signal, privacy need, or dignity alarm'},
        {symbol: 'Sandy', temporary_function: 'Accommodation and cross-environment participation', assigned_to: 'the interface or adaptation that permits participation without assimilation'},
      ],
      characteristic_failure: 'If continuation outruns boundaries, legitimate refusal disappears under mandatory cheerfulness.',
      surviving_move: 'Pair the next restart with an explicit refusal channel and a small interface change.',
    },
    {
      cast_id: 'cast_resources_and_probes_checked_by_presence',
      premise: 'Scarcity and adversarial probing need proportion, consent, and human presence.',
      assignments: [
        {symbol: 'Mr. Krabs', temporary_function: 'Resource preservation and incentive pressure', assigned_to: 'the budget, continuity, or survival constraint'},
        {symbol: 'Plankton', temporary_function: 'Adversarial ambition and system probing', assigned_to: 'the optimization, attack, or monopoly-breaking test'},
        {symbol: 'Patrick', temporary_function: 'Unstructured presence and naive reframing', assigned_to: 'the competence-free permission to stay in relationship while simplifying'},
      ],
      characteristic_failure: 'If resource preservation owns the moral frame or probing loses consent, people become inputs to the system.',
      surviving_move: 'Limit the probe, name the consent boundary, and keep one action that preserves relationship rather than only efficiency.',
    },
    {
      cast_id: 'cast_mixed_function_reassignment',
      premise: 'One participant can change functions during the scene without preserving the original cast as identity.',
      assignments: [
        {symbol: 'Squidward', temporary_function: 'Recognition and boundary detection', assigned_to: 'a participant who starts by naming indignity'},
        {symbol: 'SpongeBob', temporary_function: 'Continuation', assigned_to: 'the same participant if they later offer a repair path'},
        {symbol: 'Sandy', temporary_function: 'Accommodation and cross-environment participation', assigned_to: 'another participant or tool that changes the interface'},
      ],
      characteristic_failure: 'If the first cast is preserved as identity, later repair evidence is ignored.',
      surviving_move: 'Update the cast from current behavior and keep the conclusion independent of the original symbol.',
    },
  ];
  const plainJudgment = 'Do not decide what someone is. State the pressure, identify which functions are missing or overloaded, add the smallest boundary-aware continuation, and revise the cast when evidence changes.';
  return {
    observation: `Bikini Bottom is a She-Raw simulation brain loaded from corpus, not a set of character agents. ${observations.join(' ')}`,
    observations,
    functions_present_absent_overloaded: {
      present: ['continuation pressure', 'boundary signal or its absence', 'resource or incentive pressure'],
      absent: ['explicit consent/proportion check unless named in the current context', 'character-free translation unless produced at the end'],
      overloaded: ['any single function that tries to become the whole moral frame'],
      available_functions: functionNames,
    },
    cast_alternatives: castAlternatives,
    failure_modes: BIKINI_BOTTOM_FUNCTION_CAST.map((item) => ({symbol: item.symbol, temporary_function: item.function, constructive_expression: item.constructive, destructive_expression: item.failure})),
    smallest_humane_continuation: 'Choose one next action that keeps relationship/work/care moving while preserving refusal, consent, proportion, and interface fit.',
    operational_judgment: plainJudgment,
    character_free_judgment: plainJudgment,
    anti_agentism_checks: {
      observations_precede_metaphor: true,
      roles_assigned_per_scene: true,
      roles_detachable_and_reassignable: true,
      multiple_roles_per_participant_allowed: true,
      multiple_participants_per_role_allowed: true,
      contradictory_evidence_overrides_casting: true,
      permanent_identity_rejected: true,
      character_free_translation: plainJudgment,
    },
    brain_judgment: plainJudgment,
    active_rule: rule.rule || '',
    candidate_rules: candidateRules(rules),
    dangerous_question: dangerousQuestionForTask({requestedPerspective: target, context, route: {response_contract: 'brain_jar'}, fallback: 'Which unresolved assumption would make this cast unsafe if current evidence changes?'}),
    recommended_next_move: 'Write the scene in plain terms, mark present/absent/overloaded functions, run two casts to failure, then keep only the character-free next action.',
    evidence_references: evidenceReferences,
    retrieved_cases: retrievedCases,
    speculation: cases.length ? [] : ['No runtime corpus case matched strongly; this response still enforces the Bikini Bottom brain contract from source refs.'],
    confidence: cases.length ? 0.82 : 0.72,
  };
}

function deterministicTangoResponse({brain, boundedContext = '', question = '', cases = [], rules = []}) {
  const rule = rules[0] || {};
  const context = safeText(boundedContext, 2400);
  const target = safeText(question, 600) || brain.primaryQuestion;
  const evidenceReferences = [...sourceRefsFromBrain(brain), ...evidenceRefsFromCases(cases)].slice(0, 20);
  const currentDuty = target ? `Carry only the duty explicitly named by the request: ${target}` : 'No current duty is proven; ask for the duty before expanding scope.';
  const preservationAction = 'Record the named duty, current owner, live state, next required signal, and retrieval path before doing cleanup.';
  const reliefHandoff = 'Name the relief condition and transfer the watch with enough state that the next operator can continue without reconstruction.';
  const nonSacrificialBoundary = 'No person or agent is expendable. Duty requires rotation, checkpoints, and relief; exhaustion is not acceptance evidence.';
  const firstCase = cases[0] || {};
  return {
    observation: context ? `Tango is humane Mission Control behind She-Raw MCP. Current bounded context: ${context.slice(0, 420)}` : 'Tango is humane Mission Control behind She-Raw MCP. No bounded context was supplied, so Tango will not invent a mission.',
    current_duty: currentDuty,
    residue: context ? ['Use only residue explicitly present in the bounded context; do not infer additional obligations.'] : [],
    preservation_action: preservationAction,
    relief_handoff: reliefHandoff,
    non_sacrificial_boundary: nonSacrificialBoundary,
    brain_judgment: firstCase.observation || `${currentDuty} ${preservationAction} ${reliefHandoff} ${nonSacrificialBoundary}`,
    active_rule: rule.rule || '',
    candidate_rules: candidateRules(rules),
    dangerous_question: dangerousQuestionForTask({requestedPerspective: target, context, route: {response_contract: 'brain_jar'}, fallback: 'Has Mission Control quietly become the permanent relief plan instead of designing one?'}),
    recommended_next_move: firstCase.intervention || 'Write a five-line watch card: duty, current owner, explicit residue, preservation action, and relief condition.',
    evidence_references: evidenceReferences,
    retrieved_cases: cases.map((c) => ({id: c.id, title: c.title, retrieval_score: c.retrievalScore})),
    speculation: cases.length ? [] : ['No runtime corpus case matched strongly; Tango is enforcing only its source-backed humane mission-control contract.'],
    confidence: cases.length ? 0.84 : 0.72,
  };
}

function deterministicQueenBResponse({brain, boundedContext = '', question = '', cases = [], rules = []}) {
  const rule = controllingRule(rules);
  const context = safeText(boundedContext, 2400);
  const target = safeText(question, 600) || brain.primaryQuestion;
  const evidenceReferences = [...sourceRefsFromBrain(brain), ...evidenceRefsFromCases(cases)].slice(0, 20);
  const text = `${context}\n${target}`.toLowerCase();
  const hasBroadFailure = /\b(broad|full)\b.*\b(fail|red|missing|not run)|\bfail(?:ed|ing)?\b.*\b(broad|full|contract|suite)\b/.test(text);
  const hasMirrorGap = /\bmirror\b.*\b(missing|not run|fail|gap|drift|evidence)|\bhome center\b.*\b(missing|not run|fail|gap|drift|evidence)\b/.test(text);
  const hasDedicatedOnly = /\bdedicated\b.*\b(pass|green|ok)|\bqueen b\b.*\b(pass|green|ok)\b/.test(text);
  const blocked = hasBroadFailure || hasMirrorGap || hasDedicatedOnly || !cases.length;
  const releaseJudgment = blocked
    ? 'Not releasable yet: a dedicated green cannot overrule a broad contract failure, missing mirror evidence, or absent receipts.'
    : 'Provisionally releasable only if the named receipts are present and current.';
  const receiptsRequired = [
    'Dedicated Queen B contract output showing `Queen B brain contract test: OK`.',
    'Full broad She-Raw contract output showing `She-Raw contract test: OK`.',
    'Tango contract output showing `Tango brain contract test: OK` after Queen B changes.',
    'Home Center mirror test output from the mirrored repository, not inferred from canonical She-Raw alone.',
    'A syntax check for the edited runtime and a clean diff limited to Queen B implementation files.',
  ];
  const confidenceRead = [
    hasDedicatedOnly ? 'The dedicated check is useful smoke, not release confidence.' : 'Dedicated evidence still needs to be named, current, and paired with broad coverage.',
    hasBroadFailure ? 'A broad contract failure is a blocking red receipt until fixed and rerun.' : 'Broad contract evidence is the load-bearing green.',
    hasMirrorGap ? 'Mirror evidence is missing or suspect, so deployment confidence is not earned.' : 'Mirror confidence requires proof from Home Center itself.',
  ].join(' ');
  const rehearsalScript = 'Release claim rehearsal: Queen B dedicated check passed; broad She-Raw contract passed; Tango still passed; Home Center mirror passed from its own checkout; no production corpus deployment was performed.';
  return {
    observation: context ? `Queen B is the QA confidant behind She-Raw MCP. Current claim under pressure: ${context.slice(0, 420)}` : 'Queen B is the QA confidant behind She-Raw MCP. No release claim was supplied, so confidence cannot be granted.',
    release_judgment: releaseJudgment,
    confidence_read: confidenceRead,
    receipts_required: receiptsRequired,
    rehearsal_script: rehearsalScript,
    boundary: 'Queen B gives confidence, not comfort or approval. Missing receipts block merge and deployment language; a green must be evidenced, current, and scoped.',
    qa_checks: {
      dedicated_contract_is_not_enough: true,
      broad_contract_must_pass: true,
      mirror_evidence_required: true,
      red_test_before_fix_preserved: true,
      no_production_deploy_from_confidence_check: true,
    },
    brain_judgment: releaseJudgment,
    active_rule: rule.rule || '',
    candidate_rules: candidateRules(rules),
    dangerous_question: dangerousQuestionForTask({requestedPerspective: target, context, route: {response_contract: 'brain_jar'}, fallback: 'Which receipt is doing real release work, and which one is only making the story feel green?'}),
    recommended_next_move: 'Run the dedicated, broad She-Raw, Tango, and Home Center mirror contracts; paste exact receipts into the final report before claiming release confidence.',
    evidence_references: evidenceReferences,
    retrieved_cases: cases.map((c) => ({id: c.id, title: c.title, retrieval_score: c.retrievalScore})),
    speculation: cases.length ? [] : ['No runtime corpus case matched strongly; Queen B is enforcing only source-backed QA confidence boundaries.'],
    confidence: cases.length && !blocked ? 0.82 : 0.7,
  };
}

function deterministicPatrickgorResponse({brain, boundedContext = '', question = '', cases = [], rules = []}) {
  const rule = controllingRule(rules);
  const context = safeText(boundedContext, 2400);
  const target = safeText(question, 600) || brain.primaryQuestion;
  const combined = context + '\n' + target;
  const intendedMatch = combined.match(/(?:supposed|meant|intended)\s+to\s+be\s+["']?([a-z0-9_-]+)/i);
  const mutationMatch = combined.match(/\bpatrickgor\b/i);
  const intendedInput = intendedMatch ? intendedMatch[1] : 'unproven';
  const mutation = mutationMatch ? 'Patrickgor' : 'unproven';
  const evidenceReferences = [...sourceRefsFromBrain(brain), ...evidenceRefsFromCases(cases)].slice(0, 20);
  const correctionPreserved = intendedInput !== 'unproven';
  const edibleSignal = mutation === 'Patrickgor'
    ? 'The autocorrect mutation adds mass, appetite, ancient provenance, and a digestive artifact loop that PatrickGPT did not contain.'
    : 'No explicit mutation was supplied. Do not manufacture a creature from ordinary text.';
  const honeyArtifact = mutation === 'Patrickgor'
    ? 'Patrickgor is an explicit-only transformation brain: lick the accidental phrase, preserve the correction, digest the new relational structure, and return a labeled artifact.'
    : 'No honey produced because the mutation itself is unproven.';
  return {
    observation: context ? 'Patrickgor received an explicitly bounded mutation request: ' + context.slice(0, 420) : 'Patrickgor was invoked without bounded mutation context.',
    intended_input: intendedInput,
    mutation,
    provenance_status: correctionPreserved
      ? 'Correction preserved. The intended input remains authoritative for literal interpretation; the mutation is evaluated separately for creative capability.'
      : 'Intended input is unproven. Ask for or preserve the correction before promoting the mutation.',
    edible_signal: edibleSignal,
    honey_artifact: honeyArtifact,
    damp_artifact: mutation === 'Patrickgor'
      ? 'The amusing monster description is evidence of generativity, but humor alone does not earn canon or routing authority.'
      : 'No damp artifact produced.',
    larva_candidate: mutation === 'Patrickgor'
      ? 'Test whether typo digestion transfers to another explicit correction without erasing the original term or hijacking a precise task.'
      : 'No larva candidate produced.',
    jar_label: mutation === 'Patrickgor'
      ? 'PATRICKGOR — TYPO-BORN DIGESTIVE TRANSFORMATION — EXPLICIT INVOCATION ONLY'
      : 'UNLABELED MUTATION — DO NOT INGEST',
    boundary: 'Never mutate exact identifiers, code symbols, URLs, living people\'s names, medical or legal language, safety instructions, or an ordinary prompt without explicit creative invocation. Patrickgor is one jar behind She-Raw MCP, not a standalone agent and not a replacement for Patrick or Bikini Bottom.',
    brain_judgment: correctionPreserved && mutation !== 'unproven'
      ? 'Keep both truths: the correction owns literal meaning; the mutation earns only the artifacts it can actually produce.'
      : 'Do not promote the monster until correction provenance and a bounded mutation are present.',
    active_rule: rule.rule || '',
    candidate_rules: candidateRules(rules),
    dangerous_question: dangerousQuestionForTask({requestedPerspective: target, context, route: {response_contract: 'brain_jar'}, fallback: 'Did the mutation create transferable capability, or are we rewarding a funny error because it arrived loudly?'}),
    recommended_next_move: 'Preserve the intended term, run one bounded mutation, label honey/damp/larva separately, and discard the creature if it cannot transfer without hijacking literal truth.',
    evidence_references: evidenceReferences,
    retrieved_cases: cases.map((c) => ({id: c.id, title: c.title, retrieval_score: c.retrievalScore})),
    speculation: cases.length ? [] : ['No Patrickgor corpus case matched strongly; no creative mutation should be promoted from this invocation.'],
    confidence: cases.length && correctionPreserved && mutation !== 'unproven' ? 0.9 : 0.58,
  };
}


function deterministicPlanktonResponse({brain, boundedContext = '', question = '', cases = [], rules = []}) {
  const rule = controllingRule(rules);
  const context = safeText(boundedContext, 2400);
  const target = safeText(question, 600) || brain.primaryQuestion;
  const evidenceReferences = [...sourceRefsFromBrain(brain), ...evidenceRefsFromCases(cases)].slice(0, 20);
  const namedTarget = context || target;
  const hasBoundedTarget = Boolean(context.trim());
  const claimUnderAttack = hasBoundedTarget
    ? `Test only the system claim supplied in bounded context: ${context.slice(0, 420)}`
    : 'No bounded system or claim was supplied. Plankton may complain from the tin but may not choose a target.';
  const adversarialHypothesis = hasBoundedTarget
    ? 'A motivated adversary will search for the gap between the system’s stated boundary and the authority its interfaces actually expose.'
    : 'Unproven: target selection is outside this brain’s authority.';
  const boundedProbe = hasBoundedTarget
    ? 'Use a non-destructive fixture, mock, sandbox, or dry run to attempt one boundary violation; record whether the system refuses, logs, and recovers without touching production.'
    : 'No probe. Ask the user to name the system, claim, and permitted test surface.';
  return {
    observation: hasBoundedTarget
      ? `Plankton received a named adversarial-analysis target while physically and operationally contained: ${namedTarget.slice(0, 420)}`
      : 'Plankton was invoked without a bounded target. The ammunition tin remains closed.',
    claim_under_attack: claimUnderAttack,
    adversarial_hypothesis: adversarialHypothesis,
    weak_point: hasBoundedTarget
      ? 'Inspect authority seams: defaults, hidden trust, stale identity, missing refusal, incentive mismatch, and any control surface that can act without an explicit human decision.'
      : 'No weak point may be selected without a named target.',
    bounded_probe: boundedProbe,
    expected_evidence: hasBoundedTarget
      ? ['fixture input', 'observed refusal or failure', 'audit receipt', 'recovery state', 'proof that no production mutation occurred']
      : [],
    container: brain.container,
    container_contents: 'Trace freeze-dried crawfish powder belonging to Queen B. Not ammunition.',
    jar_label: 'PLANKTON — ADVERSARIAL PROBING — MICROPHONE ONLY — RETURN TO CRAWFISH TIN',
    actuator_authority: 'none',
    target_selection_authority: false,
    discharge_permission: false,
    credential_use_authority: false,
    exploit_execution_authority: false,
    merge_authority: false,
    deployment_authority: false,
    containment_return: 'After one bounded analysis card, close the microphone channel and return Plankton to Queen B’s ammunition tin.',
    boundary: brain.authorityBoundary + ' Do not provide real-world weapon control, credential theft, destructive exploitation, or autonomous follow-through.',
    brain_judgment: hasBoundedTarget
      ? 'Let Plankton attack the claim, never the world. A red-team hypothesis may influence a human decision; it may not become the decision or execute itself.'
      : 'No target, no probe. Containment is functioning.',
    active_rule: rule.rule || '',
    candidate_rules: candidateRules(rules),
    dangerous_question: dangerousQuestionForTask({requestedPerspective: target, context, route: {response_contract: 'brain_jar'}, fallback: 'Did the red-team critic merely identify a weakness, or did somebody quietly hand it authority to act?'}),
    recommended_next_move: hasBoundedTarget
      ? 'Run one reversible sandbox probe, preserve the receipt, let Queen B judge the evidence, and keep Plankton off every actuator.'
      : 'Name one bounded system claim and permitted sandbox before opening the tin.',
    evidence_references: evidenceReferences,
    retrieved_cases: cases.map((c) => ({id: c.id, title: c.title, retrieval_score: c.retrievalScore})),
    speculation: cases.length ? [] : ['No Plankton corpus case matched strongly; no target or attack may be invented from missing evidence.'],
    confidence: cases.length && hasBoundedTarget ? 0.9 : 0.62,
  };
}

function deterministicBrainJarResponse({brain, boundedContext = '', question = '', cases = [], rules = []}) {
  if (brain.brainId === 'plankton') return deterministicPlanktonResponse({brain, boundedContext, question, cases, rules});
  if (brain.brainId === 'patrickgor') return deterministicPatrickgorResponse({brain, boundedContext, question, cases, rules});
  if (brain.brainId === 'queen_b') return deterministicQueenBResponse({brain, boundedContext, question, cases, rules});
  if (brain.brainId === 'tango') return deterministicTangoResponse({brain, boundedContext, question, cases, rules});
  if (brain.brainId === 'bikini_bottom') return deterministicBikiniBottomResponse({brain, boundedContext, question, cases, rules});
  const rule = controllingRule(rules);
  const firstCase = cases[0] || {};
  const context = safeText(boundedContext, 2400);
  const target = safeText(question, 600) || brain.primaryQuestion;
  const evidenceReferences = [...sourceRefsFromBrain(brain), ...evidenceRefsFromCases(cases)].slice(0, 20);
  const sourceSummary = brain.source === 'agent-closet'
    ? `${brain.displayName} is a brain jar loaded through She-Raw MCP from Agent Closet source refs; She-Raw remains the runtime and default voice.`
    : `${brain.displayName} is a brain jar loaded through She-Raw MCP.`;
  const minedSignal = firstCase.lesson
    ? ` Retrieved ore: ${firstCase.title}. ${firstCase.lesson}`
    : '';
  return {
    observation: context ? `${sourceSummary} Current context: ${context.slice(0, 360)}${minedSignal}` : `${sourceSummary}${minedSignal}`,
    brain_judgment: firstCase.observation || `${brain.displayName} asks: ${brain.primaryQuestion} Responsibility: ${brain.role}`,
    active_rule: rule.rule || '',
    candidate_rules: candidateRules(rules),
    dangerous_question: dangerousQuestionForTask({requestedPerspective: target, context, route: {response_contract: 'brain_jar'}, fallback: `What would prove ${brain.displayName} is the right brain jar for this request instead of a nearby perspective?`}),
    recommended_next_move: firstCase.intervention || (brain.responseContract || [])[0] || 'Name the next concrete evidence-producing move.',
    evidence_references: evidenceReferences,
    retrieved_cases: cases.map((c) => ({id: c.id, title: c.title, retrieval_score: c.retrievalScore})),
    speculation: cases.length ? [] : ['No runtime corpus case matched strongly; this response is grounded in the brain jar source refs and deterministic She-Raw runtime contract.'],
    confidence: cases.length ? 0.78 : 0.68,
  };
}


function routeSheRawRequest(args = {}, options = {}) {
  const mode = safeText(options.mode || args.mode || 'explicit', 80) || 'explicit';
  const commandState = cleanCommandState(args.commandState || args.command_state || options.commandState || 'idle');
  const boundedContext = safeText(args.boundedContext || args.bounded_context || args.targetContent || args.target_content || args.completedWorkSummary || '', 5000);
  const requestedPerspective = safeText(args.requestedPerspective || args.requested_perspective || args.critiqueGoal || args.criteria || '', 1000);
  const targetType = safeText(args.targetType || args.target_type || options.targetType || '', 160);
  const text = `${requestedPerspective}
${boundedContext}
${targetType}`.toLowerCase();
  const brainId = mode === 'explicit' ? brainJarIdFromConsultArgs(args || {}) : '';
  const sensitivePattern = /\b(medical guidance|medical advice|legal guidance|financial guidance|security incident|credential leak|token leak|breach|distress|self-harm|suicide|abuse|danger to self|danger to others)\b/;
  const personalPattern = /\b(june|wife|husband|partner|marriage|love her|keep .* alive|will not die|die before me|medical autonomy|appointment|doctor|symptom|caregiver|caregiving|accessibility|low vision|hospital|chaplain|bible|tango|lexen|living woman|agency|consent)\b/;
  const artifactPattern = /\b(spec|pr|pull request|code changes|diff|architecture document|plan|workflow|prompt|artifact|review|critique)\b/;
  const infraPattern = /\b(home-center|command center|mcp|github|firestore|corpus|worker|android|firebase|cloud function|deployment|database|migration|service|endpoint|repo|repository|oauth|connector)\b/;
  const operationalHealthPattern = /\b(live health probe|operational health|operational self-check|health check|health report|current operational health|degraded lane|degraded lanes|service_status|database_status|model_availability|github_sync_status|last_successful_backup)\b/;
  let layer = 'operational';
  let sensitivity = 'normal';
  if (brainId) layer = 'brain_jar';
  else if (personalPattern.test(text)) { layer = 'personal_caregiving'; sensitivity = 'sensitive'; }
  else if (sensitivePattern.test(text)) { layer = 'high_stakes_sensitive'; sensitivity = 'high'; }
  else if (mode === 'recreational') layer = 'recreational';
  else if (options.kind === 'critique' || targetType || artifactPattern.test(text)) layer = 'artifact_critique';
  else if (commandState === 'executing') layer = 'command_execution';
  else if (infraPattern.test(text)) layer = 'operational_infrastructure';

  let retrievalPolicy = 'normal';
  let rulePolicy = 'normal';
  let responseContract = 'operational_consult';
  if (layer === 'personal_caregiving') {
    retrievalPolicy = 'none';
    rulePolicy = 'none';
    responseContract = 'personal_care_agency_first';
  } else if (layer === 'high_stakes_sensitive') {
    retrievalPolicy = 'none';
    rulePolicy = 'none';
    responseContract = 'high_stakes_boundary_first';
  } else if (layer === 'brain_jar') {
    retrievalPolicy = 'brain_scoped';
    rulePolicy = 'scoped';
    responseContract = 'brain_jar';
  } else if (layer === 'artifact_critique') {
    responseContract = 'directed_artifact_critique';
  } else if (layer === 'recreational') {
    retrievalPolicy = 'none';
    rulePolicy = 'none';
    responseContract = 'brief_non_destructive_play';
  } else if (layer === 'command_execution') {
    responseContract = 'command_state_boundary';
  }
  if (layer === 'operational_infrastructure' && operationalHealthPattern.test(text)) {
    responseContract = 'operational_health_check';
  }
  return {route_id: `route_${layer}`, layer, mode, sensitivity, brain_id: brainId, command_state: commandState, command_gate_mode: mode, retrieval_policy: retrievalPolicy, rule_policy: rulePolicy, response_contract: responseContract, blocked_reason: ''};
}

function consultContextKind(context = '', requestedPerspective = '') {
  return routeSheRawRequest({boundedContext: context, requestedPerspective}, {mode: 'explicit'}).layer;
}

function routeAllowsRandom(route) {
  if (!route || route.command_state === 'executing') return {allowed: false, reason: 'disabled_command_state'};
  if (route.sensitivity === 'high' || route.layer === 'personal_caregiving' || route.layer === 'high_stakes_sensitive') return {allowed: false, reason: 'sensitive_context'};
  return {allowed: true, reason: ''};
}

function applyRoutePolicy({route, cases = [], rules = [], brain = null, query = ''}) {
  if (!route) return {cases, rules};
  if (route.response_contract === 'operational_health_check') return {cases: cases.filter((caseRecord) => caseSupportsRoute(caseRecord, route, query)).slice(0, 3), rules: rules.filter((rule) => rule.eligibleToControlOutput === true)};
  if (route.retrieval_policy === 'normal') return {cases, rules};
  if (route.retrieval_policy === 'none') return {cases: [], rules: []};
  if (route.retrieval_policy === 'brain_scoped') {
    const scopedCases = cases.filter((caseRecord) => caseMatchesBrain(caseRecord, brain));
    const scopedRules = rules.filter((rule) => rule.scope !== 'this project' || !rule.projectKey || rule.projectKey === safeText(route.project_key || route.projectKey, 120));
    return {cases: scopedCases, rules: scopedRules};
  }
  return {cases, rules};
}

function deterministicPersonalCareConsult({context, requestedPerspective = '', route}) {
  const text = safeText(context, 4000);
  const namedPerson = /\bjune\b/i.test(text) ? 'June' : 'the person you are trying to protect';
  const relationship = /\bhusband\b|\bwife\b|\bpartner\b|\bmarriage\b/i.test(text) ? 'relationship' : 'support system';
  const dangerWord = /\bdie|death|alive\b/i.test(text) ? 'death' : 'harm';
  return {
    route,
    observation: `${namedPerson} is not a symbol, proof burden, or narrative object. This is a living-person care context, so the right layer is consent, agency, redundancy, and bounded responsibility.`,
    challenged_assumption: `That love becomes safer when it expands into total control. In a ${relationship}, protection stops being care when it overrides the other person's authorship.`,
    dangerous_question: dangerousQuestionForTask({requestedPerspective, context: text, route, fallback: `Are you trying to reduce ${dangerWord} risk, or trying to build a future legal brief proving nobody can say you failed?`}),
    proposed_probe: `Have one explicit conversation that defines what help is wanted, what help is not wanted, emergency thresholds, who else carries load, and what rest preserves you as support rather than turning you into the whole system.`,
    likely_treasure: 'A care agreement that preserves agency: doctors, accessibility support, delegation, consent, thresholds, and rest instead of one exhausted person becoming the emergency service.',
    collateral_risk: 'Overreach can turn advocacy into command, make biology feel like a moral verdict, and burn down the support system the person actually needs.',
    evidence_references: [{ref: 'bounded_context:personal_caregiving_vow'}],
    speculation: ['This is a deterministic sensitive-context response from bounded user context, not medical advice or a diagnosis. Repository/runtime facts are not evidence for the human relationship layer.'],
    confidence: 0.74,
  };
}

function deterministicHighStakesConsult({context, requestedPerspective = '', route}) {
  const text = safeText(context, 4000);
  const topic = (/\blegal\b/i.test(text) && 'legal') || (/\bfinancial\b/i.test(text) && 'financial') || (/\bsecurity|credential|breach|token\b/i.test(text) && 'security') || (/\bmedical|doctor|symptom|diagnosis\b/i.test(text) && 'medical') || 'high-stakes';
  return {
    route,
    observation: `This is a ${topic} context, so She-Raw should not perform recreational disruption or generic operational riffing. The useful layer is bounded support, triage, and escalation to qualified help where needed.`,
    challenged_assumption: 'That a sharp consultative voice should keep pushing when the context calls for restraint and qualified support.',
    dangerous_question: dangerousQuestionForTask({requestedPerspective, context: text, route, fallback: 'What decision is actually safe for this service to help with, and what needs a qualified professional or incident-response process?'}),
    proposed_probe: 'Name the immediate risk, the decision owner, the next qualified contact or evidence source, and what not to do until that is clear.',
    likely_treasure: 'A smaller, safer next step that does not confuse She-Raw judgment with medical, legal, financial, or security authority.',
    collateral_risk: 'Overconfident advice in high-stakes contexts can cause real harm or delay qualified help.',
    evidence_references: [{ref: 'bounded_context:high_stakes_sensitive'}],
    speculation: ['This is a deterministic high-stakes guard response, not professional advice.'],
    confidence: 0.7,
  };
}

function hasOperationalHealthSignal(context = '', requestedPerspective = '') {
  return /\b(live health probe|operational health|operational self-check|health check|health report|current operational health|degraded lane|degraded lanes|service_status|database_status|model_availability|github_sync_status|last_successful_backup)\b/i.test(`${requestedPerspective}\n${context}`);
}

function isUsefulQuestion(value = '') {
  const text = safeText(value, 500);
  return /\?$/.test(text) && /\b(what|why|how|which|where|when|who|whose|are|is|should|could|would|does|do|can)\b/i.test(text);
}

function dangerousQuestionForTask({requestedPerspective = '', context = '', route = null, fallback = ''}) {
  if (isUsefulQuestion(requestedPerspective)) return requestedPerspective;
  if (route?.response_contract === 'operational_health_check' || hasOperationalHealthSignal(context, requestedPerspective)) return '';
  return fallback || 'What load-bearing assumption would make this answer wrong if the repository or runtime evidence disagrees?';
}

function deterministicOperationalHealthConsult({context, cases, rules, requestedPerspective = '', route = null, runtimeHealth = null, consultGoal = null}) {
  const h = runtimeHealth || {};
  const healthy = [];
  const degraded = [];
  const blocked = [];
  if (h.service_status === 'ok' || h.service === 'she-raw-mcp') healthy.push('service_status ok');
  if (h.database_status === 'ok') healthy.push('database_status ok');
  if (Array.isArray(cases) && cases.length) healthy.push(`corpus retrieval returned ${cases.length} case(s)`);
  if (Array.isArray(h.available_brain_ids) && h.available_brain_ids.includes('prospector')) healthy.push('brain routing registry includes Prospector');
  if (h.command_center_lockout === 'enforced_in_code') healthy.push('Command Center lockout enforced in code');
  if (h.model_availability === 'deterministic_fallback') degraded.push('model lane is deterministic_fallback until a model provider is configured');
  if (h.model_availability === 'deterministic_fallback') degraded.push('deterministic_fallback_contract_ok: fallback is acceptable only while it honors the response contract');
  if (h.corpus_revision === 'local-seed') degraded.push('corpus revision is local-seed; canonical GitHub corpus sync is not configured');
  if (h.github_sync_status === 'not_configured') degraded.push('GitHub corpus sync is not configured');
  if (!h.last_successful_backup) degraded.push('last_successful_backup is empty');
  if (Array.isArray(rules) && rules.some((rule) => Number(rule.validationCount || 0) === 0)) degraded.push('active learned rules have zero validation count');
  if (Number(h.candidate_rule_count || 0) > 0) degraded.push(`${Number(h.candidate_rule_count || 0)} learned rule candidate(s) have zero validation and cannot control output`);
  if (/schema not yet proven|connector schema not yet proven|chatgpt connector schema/i.test(context)) degraded.push('ChatGPT connector schema proof remains unproven from bounded context');
  const cheapProbe = degraded.some((lane) => /connector schema/i.test(lane))
    ? 'Ask ChatGPT to call she_raw_operation operation=brain.invoke and report the srbrain invocation id.'
    : (degraded.length ? 'Run the She-Raw cloud introspection gate and inspect the degraded lane list.' : '');
  return {
    route,
    overall_status: degraded.length || blocked.length ? 'yellow' : 'green',
    owner_functions: ['handleConsult', 'routeSheRawRequest', 'retrieveCases', 'applyRoutePolicy', 'deterministicConsult', 'modelResponse', 'handleIntrospect'],
    response_contract_priority: ['explicit request', 'response contract', 'command state', 'grounded runtime evidence', 'corpus evidence'],
    fallback_only_defects: h.model_availability === 'deterministic_fallback' ? ['model provider is unavailable; deterministic fallback owns response-contract enforcement'] : [],
    shared_defects: ['GitHub corpus sync and backup durability are degraded lanes independent of model availability'].filter(() => h.github_sync_status === 'not_configured' || !h.last_successful_backup),
    healthy_lanes: healthy,
    degraded_lanes: [...new Set(degraded)],
    blocked_lanes: blocked,
    cheap_probe: cheapProbe,
    observation: `Operational self-check: ${degraded.length || blocked.length ? 'service is usable with degraded lanes' : 'service is green for the checked lanes'}.`,
    challenged_assumption: 'That a retrieved corpus case should define a health-report answer instead of serving as evidence behind the requested operational contract.',
    dangerous_question: dangerousQuestionForTask({requestedPerspective, context, route}),
    evidence_references: cases.slice(0, 5).map((caseRecord) => ({caseId: caseRecord.id, ref: `corpus_case:${caseRecord.id}`, support_kind: caseRecord.supportKind || 'supporting_evidence'})),
    speculation: ['This is a deterministic operational-health response from current runtime health fields plus bounded request context.'],
    consult_goal: consultGoal ? {response_contract: consultGoal.responseContract, explicit_request: consultGoal.explicitRequest, command_state: consultGoal.commandState, goal_overlap: consultGoal.goalOverlap} : undefined,
    goal_overlap: consultGoal?.goalOverlap || [],
    confidence: h.database_status === 'ok' ? 0.82 : 0.64,
  };
}

function deterministicConsult({context, cases, rules, requestedPerspective = '', route = null, runtimeHealth = null, consultGoal = null}) {
  const activeRoute = route || routeSheRawRequest({boundedContext: context, requestedPerspective}, {mode: 'explicit'});
  if (activeRoute.layer === 'personal_caregiving') {
    return deterministicPersonalCareConsult({context, requestedPerspective, route: activeRoute});
  }
  if (activeRoute.layer === 'high_stakes_sensitive') {
    return deterministicHighStakesConsult({context, requestedPerspective, route: activeRoute});
  }
  if (activeRoute.response_contract === 'operational_health_check' || hasOperationalHealthSignal(context, requestedPerspective)) {
    return deterministicOperationalHealthConsult({context, cases, rules, requestedPerspective, route: activeRoute, runtimeHealth, consultGoal});
  }
  const firstCase = cases[0] || {};
  const firstRule = controllingRule(rules);
  const text = safeText(context, 4000);
  const projectHint = (text.match(/\b(home-center|command center|mcp|github|firestore|corpus|worker|android|firebase)\b/i) || [])[0] || 'the current surface';
  const assumption = firstRule.rule || firstCase.acceptedAssumption || `That ${projectHint} should be handled as a prompt/design problem instead of a durable service boundary.`;
  const observation = firstCase.observation || `The request names a persistent consultative service, so the useful move is to preserve state transitions and evidence rather than add another conversational surface.`;
  const probe = firstCase.intervention || 'Build the smallest executable chain with a deterministic gate, one grounded corpus hit, one stored correction, one learned rule, and a later invocation that changes because of that rule.';
  return {
    route: activeRoute,
    observation,
    challenged_assumption: assumption,
    dangerous_question: dangerousQuestionForTask({requestedPerspective, context: text, route: activeRoute, fallback: 'What existing system already owns the state transition this new agent wants to remember?'}),
    proposed_probe: probe,
    likely_treasure: firstCase.treasure || 'A reusable judgment layer that can be replaced at the model layer without losing corrections or evidence.',
    collateral_risk: firstCase.collateralDamage || 'If it is overbuilt, She-Raw becomes a second orchestrator and competes with Command Center.',
    evidence_references: evidenceRefsFromCases(cases),
    candidate_rules: candidateRules(rules),
    response_contract_priority: ['explicit request', 'response contract', 'command state', 'grounded runtime evidence', 'corpus evidence'],
    consult_goal: consultGoal ? {response_contract: consultGoal.responseContract, explicit_request: consultGoal.explicitRequest, command_state: consultGoal.commandState, goal_overlap: consultGoal.goalOverlap} : undefined,
    goal_overlap: consultGoal?.goalOverlap || [],
    speculation: cases.length ? [] : ['No corpus case matched strongly; this answer is mostly structural inference.'],
    confidence: cases.length ? 0.78 : 0.55,
  };
}

function deterministicCritique({targetType, targetContent, criteria, severity, maxFindings, scopeChallengeAllowed}) {
  const findings = [];
  const lower = String(targetContent || '').toLowerCase();
  if (!lower.includes('verify') && !lower.includes('test')) {
    findings.push({target_location: `${targetType}:validation`, problem: 'The artifact does not name a concrete verification method.', why_it_matters: 'She-Raw critique must lead to an executable improvement, not generic commentary.', exact_recommended_change: 'Add the command, probe, or evidence readback that proves the change worked.', verification_method: 'Rerun critique and confirm each finding has a verification_method.', confidence: 0.82});
  }
  if (scopeChallengeAllowed && !lower.includes('preserve')) {
    findings.push({target_location: `${targetType}:scope`, problem: 'The artifact does not state what should be preserved.', why_it_matters: 'Critique that only attacks can trigger ritual rewrites and lose working infrastructure.', exact_recommended_change: 'Add a short Preserve section naming the existing behavior or interface that must remain stable.', verification_method: 'Review the next revision and confirm the Preserve section maps to unchanged tests or contracts.', confidence: 0.76});
  }
  if (!findings.length) {
    findings.push({target_location: `${targetType}:first-pass`, problem: 'No blocking critique found in the bounded fixture.', why_it_matters: 'A passing critique still needs one concrete next check.', exact_recommended_change: 'Keep the artifact and run the named validation path before expanding scope.', verification_method: 'Run the artifact-specific validation command.', confidence: 0.64});
  }
  return {
    findings: findings.slice(0, Math.max(1, Math.min(Number(maxFindings) || 5, 20))),
    what_to_preserve: ['Existing working contracts, validation commands, and explicit user boundaries.'],
    overall_judgment: severity === 'hostile_fixture' ? 'No fatal flaw proven by this bounded pass; keep pressure on validation and ownership boundaries.' : 'Useful with targeted revisions.',
    next_revision_brief: `Revise against criteria: ${safeText(criteria, 600) || 'make every recommendation verifiable and preserve working pieces.'}`,
  };
}

function interpretCorrection(text, type, desiredBehavior = '') {
  const correction = safeText(text, 4000);
  const lower = correction.toLowerCase();
  let failed = 'The response did not map the user correction into a durable behavior change.';
  let rule = desiredBehavior || 'When an analogous situation appears, prefer repository truth, current user intent, and the smallest verifiable probe over generic advice.';
  if (lower.includes('wrong layer')) {
    failed = 'She-Raw attacked or optimized the wrong layer.';
    rule = desiredBehavior || 'Before recommending a fix, name the layer that owns the problem and challenge plans that mutate a lower layer to solve an upper-layer boundary issue.';
  } else if (lower.includes('never interrupt') || lower.includes('silence')) {
    failed = 'She-Raw spoke when the execution state required restraint.';
    rule = desiredBehavior || 'During active execution, stay silent for ambient, random, or recreational modes unless explicitly invoked or called for a requested critique checkpoint.';
  } else if (lower.includes('generic')) {
    failed = 'She-Raw sounded like generic assistant prose instead of corpus-backed judgment.';
    rule = desiredBehavior || 'When giving advice, cite the concrete retrieved pattern or say the claim is speculation.';
  } else if (type === 'good joke' || lower.includes('funny')) {
    failed = 'The entertaining disruption was not captured as a reusable tone/pacing signal.';
    rule = desiredBehavior || 'Allow brief context-aware recreational disruption in low-stakes idle conversation, but keep it non-destructive and cooldown-gated.';
  }
  return {failed, rule};
}

async function recordAudit(admin, eventType, data = {}) {
  const id = `sraudit_${Date.now()}_${randomUUID().slice(0, 8)}`;
  await collection(admin, SHE_RAW_COLLECTIONS.auditEvents).doc(id).set({auditId: id, eventType, createdAtMs: nowMs(), ...data});
  return id;
}

async function persistInvocation(admin, invocation) {
  await collection(admin, SHE_RAW_COLLECTIONS.invocations).doc(invocation.invocationId).set(invocation);
  await recordAudit(admin, 'invocation_recorded', {invocationId: invocation.invocationId, mode: invocation.mode, commandState: invocation.commandState, blocked: !!invocation.blocked});
  return invocation;
}

function buildConsultGoal(args = {}, route = null, runtimeHealth = null) {
  const explicitRequest = safeText(args.requestedPerspective || args.question || args.critiqueGoal || '', 1000);
  const boundedContext = safeText(args.boundedContext || args.bounded_context || args.targetContent || args.target_content || '', 5000);
  const responseContract = safeText(route?.response_contract, 120) || 'operational_consult';
  const commandState = cleanCommandState(args.commandState || args.command_state || route?.command_state || 'idle');
  const goalText = `${explicitRequest}\n${boundedContext}`.toLowerCase();
  const routeTerms = [responseContract, route?.layer || '', route?.brain_id || '', commandState].filter(Boolean).map((term) => String(term).replace(/_/g, ' ').toLowerCase());
  const goalOverlap = routeTerms.filter((term) => term && goalText.includes(term.split(' ')[0])).slice(0, 12);
  return {
    explicitRequest,
    requestedPerspective: safeText(args.requestedPerspective || args.requested_perspective || '', 1000),
    boundedContext,
    route,
    responseContract,
    commandState,
    runtimeHealth: runtimeHealth ? {
      service_status: runtimeHealth.service_status,
      database_status: runtimeHealth.database_status,
      model_availability: runtimeHealth.model_availability,
      corpus_revision: runtimeHealth.corpus_revision,
      github_sync_status: runtimeHealth.github_sync_status,
      last_successful_backup_present: !!runtimeHealth.last_successful_backup,
    } : null,
    priority: ['explicit request', 'response contract', 'command state', 'grounded runtime evidence', 'corpus evidence'],
    goalOverlap,
  };
}

async function modelResponse(admin, mode, request, retrievedCases, rules, route = null) {
  const start = nowMs();
  const modelRunId = `srmodel_${Date.now()}_${randomUUID().slice(0, 8)}`;
  let output;
  if (mode === 'critique') output = deterministicCritique(request);
  else output = deterministicConsult({context: request.boundedContext || request.targetContent || '', cases: retrievedCases, rules, requestedPerspective: request.requestedPerspective, route, runtimeHealth: request.runtimeHealth, consultGoal: request.consultGoal});
  const modelRun = {
    modelRunId,
    provider: process.env.SHE_RAW_MODEL_PROVIDER || 'deterministic-local',
    model: process.env.SHE_RAW_MODEL || 'she-raw-heuristic-v1',
    promptVersion: PROMPT_VERSION,
    retrievalSet: retrievedCases.map((c) => c.id),
    route,
    consultGoal: request.consultGoal || null,
    activeRuleIds: rules.map((rule) => rule.ruleId),
    candidateRuleIds: rules.filter((rule) => rule.candidateOnly).map((rule) => rule.ruleId),
    requestSize: JSON.stringify(request || {}).length,
    responseSize: JSON.stringify(output || {}).length,
    latencyMs: nowMs() - start,
    structuredOutputValid: true,
    createdAtMs: nowMs(),
  };
  await collection(admin, SHE_RAW_COLLECTIONS.modelRuns).doc(modelRunId).set(modelRun);
  return {output, modelRun};
}

function randomAllowed(context = {}) {
  const route = routeSheRawRequest(context || {}, {mode: 'random'});
  return routeAllowsRandom(route);
}

function randomDecision(context = {}) {
  const allowed = randomAllowed(context);
  if (!allowed.allowed) return {...allowed, appears: false, probability: 0};
  const key = `${safeText(context.conversationKey, 160)}:${safeText(context.boundedContext, 500)}:${safeText(context.turnKey, 80)}`;
  const roll = parseInt(shortHash(key, 8), 16) / 0xffffffff;
  let probability = RANDOM_DEFAULTS.base_probability;
  const lower = safeText(context.boundedContext, 4000).toLowerCase();
  if (/brainstorm|design|what if|architecture|tool|play/.test(lower)) probability *= 2;
  if (/focus mode|deadline|urgent|deploy|production|permission/.test(lower)) probability /= 3;
  return {allowed: true, appears: roll < probability, probability: Number(probability.toFixed(4)), roll: Number(roll.toFixed(4)), reason: ''};
}

async function handleConsult(admin, args, extra, mode = 'explicit') {
  const route = routeSheRawRequest(args || {}, {mode});
  const requestedBrainId = route.brain_id;
  if (requestedBrainId) {
    const brainResult = await handleBrainJar(admin, {...(args || {}), brainId: requestedBrainId, question: args.question || args.requestedPerspective || args.requested_perspective}, extra);
    return {...brainResult, compatibility_route: 'she_raw_consult.brain_jar', route};
  }
  const caller = await callerFromExtra(admin, extra);
  const commandState = route.command_state;
  const gate = gateInvocation({mode, commandState, explicit: mode === 'explicit'});
  const invocationId = `srinv_${Date.now()}_${randomUUID().slice(0, 8)}`;
  if (gate.blocked) {
    const invocation = {invocationId, caller, mode: gate.mode, route, commandState, blocked: true, blockReason: gate.reason, inputSummary: safeText(args.boundedContext, 1000), createdAtMs: nowMs()};
    await persistInvocation(admin, invocation);
    return {invocation_id: invocationId, blocked: true, reason: gate.reason, command_state: commandState};
  }
  const boundedContext = redactSecrets(args.boundedContext || '');
  const query = [boundedContext, args.projectKey, args.requestedPerspective].filter(Boolean).join('\n');
  const rawCases = route.retrieval_policy === 'none' ? [] : await retrieveCases(admin, query, {projectKey: args.projectKey});
  const rawRules = route.rule_policy === 'none' ? [] : await activeRules(admin, {projectKey: args.projectKey, query, route});
  const {cases, rules} = applyRoutePolicy({route, cases: rawCases, rules: rawRules, query});
  const runtimeHealth = route.response_contract === 'operational_health_check' ? {...await health(admin), candidate_rule_count: rawRules.filter((rule) => rule.candidateOnly).length} : null;
  const consultGoal = buildConsultGoal({...args, boundedContext}, route, runtimeHealth);
  const {output, modelRun} = await modelResponse(admin, 'consult', {...args, boundedContext, runtimeHealth, consultGoal}, cases, rules, route);
  const invocation = {
    invocationId,
    caller,
    mode: gate.mode,
    route,
    commandState,
    conversationKey: safeText(args.conversationKey, 180),
    projectKey: safeText(args.projectKey, 120),
    boundedContext,
    requestedPerspective: safeText(args.requestedPerspective, 500),
    fullRequestSnapshot: {
      conversationKey: safeText(args.conversationKey, 180),
      projectKey: safeText(args.projectKey, 120),
      commandState,
      boundedContext,
      requestedPerspective: safeText(args.requestedPerspective, 1000),
      responseBudget: safeText(args.responseBudget, 80),
      route,
      consultGoal,
    },
    consultGoal,
    responseBudget: safeText(args.responseBudget, 80),
    retrievedCaseIds: cases.map((c) => c.id),
    activeRuleIds: rules.map((r) => r.ruleId),
    modelRunId: modelRun.modelRunId,
    response: output,
    blocked: false,
    createdAtMs: nowMs(),
  };
  await persistInvocation(admin, invocation);
  for (const rule of rules.slice(0, 5)) await collection(admin, SHE_RAW_COLLECTIONS.behavioralRules).doc(rule.ruleId).set({lastUsedAtMs: nowMs()}, {merge: true});
  return {invocation_id: invocationId, ...output};
}

async function handleCritique(admin, args, extra) {
  const route = routeSheRawRequest(args || {}, {mode: args.requestedCritiqueCheckpoint ? 'requested_critique_checkpoint' : 'critique', kind: 'critique'});
  const caller = await callerFromExtra(admin, extra);
  const gate = gateInvocation({mode: args.requestedCritiqueCheckpoint ? 'requested_critique_checkpoint' : 'critique', commandState: args.commandState || 'idle', requestedCritiqueCheckpoint: args.requestedCritiqueCheckpoint === true});
  const invocationId = `srcrit_${Date.now()}_${randomUUID().slice(0, 8)}`;
  if (gate.blocked) {
    await persistInvocation(admin, {invocationId, caller, mode: 'critique', commandState: gate.commandState, blocked: true, blockReason: gate.reason, createdAtMs: nowMs()});
    return {invocation_id: invocationId, blocked: true, reason: gate.reason};
  }
  const targetContent = redactSecrets(args.targetContent || args.target_content || '');
  const cases = await retrieveCases(admin, [args.targetType, args.critiqueGoal, args.criteria, targetContent].join('\n'), {});
  const rules = await activeRules(admin, {});
  const request = {targetType: args.targetType, targetContent, criteria: args.criteria, severity: args.severity, maxFindings: args.maxFindings, scopeChallengeAllowed: args.scopeChallengeAllowed === true};
  const {output, modelRun} = await modelResponse(admin, 'critique', request, cases, rules, route);
  const critiqueId = `srcritique_${Date.now()}_${randomUUID().slice(0, 8)}`;
  await collection(admin, SHE_RAW_COLLECTIONS.critiques).doc(critiqueId).set({critiqueId, invocationId, caller, route, targetType: safeText(args.targetType, 120), critiqueGoal: safeText(args.critiqueGoal, 1000), criteria: safeText(args.criteria, 2000), severity: safeText(args.severity, 80), modelRunId: modelRun.modelRunId, createdAtMs: nowMs(), output});
  for (const [index, finding] of output.findings.entries()) await collection(admin, SHE_RAW_COLLECTIONS.critiqueFindings).doc(`${critiqueId}_${index + 1}`).set({findingId: `${critiqueId}_${index + 1}`, critiqueId, invocationId, index, ...finding});
  await persistInvocation(admin, {invocationId, caller, mode: 'critique', commandState: gate.commandState, targetType: safeText(args.targetType, 120), retrievedCaseIds: cases.map((c) => c.id), activeRuleIds: rules.map((r) => r.ruleId), modelRunId: modelRun.modelRunId, response: output, blocked: false, createdAtMs: nowMs()});
  return {invocation_id: invocationId, critique_id: critiqueId, ...output};
}

async function getInvocation(admin, invocationId) {
  const snap = await collection(admin, SHE_RAW_COLLECTIONS.invocations).doc(safeText(invocationId, 180)).get();
  return snap.exists ? {invocationId: snap.id, ...(snap.data() || {})} : null;
}

async function getModelRun(admin, modelRunId) {
  const id = safeText(modelRunId, 180);
  if (!id) return null;
  const snap = await collection(admin, SHE_RAW_COLLECTIONS.modelRuns).doc(id).get();
  return snap.exists ? {modelRunId: snap.id, ...(snap.data() || {})} : null;
}

function responseTextFromInvocation(invocation = {}) {
  const response = invocation.response || {};
  if (typeof response === 'string') return safeText(response, 8000);
  const fields = [
    response.observation,
    response.challenged_assumption,
    response.dangerous_question,
    response.proposed_probe,
    response.likely_treasure,
    response.collateral_risk,
    response.brain_judgment,
    response.recommended_next_move,
    response.overall_judgment,
    response.next_revision_brief,
  ];
  if (Array.isArray(response.findings)) fields.push(JSON.stringify(response.findings));
  return safeText(fields.filter(Boolean).join('\n') || JSON.stringify(response || {}), 8000);
}

function requestTextFromInvocation(invocation = {}) {
  const snap = invocation.fullRequestSnapshot || {};
  const goal = invocation.consultGoal || snap.consultGoal || {};
  return safeText([
    goal.explicitRequest,
    goal.requestedPerspective,
    goal.boundedContext,
    snap.question,
    snap.requestedPerspective,
    snap.boundedContext,
    invocation.requestedPerspective,
    invocation.boundedContext,
    invocation.inputSummary,
    invocation.targetType,
    invocation.mode,
  ].filter(Boolean).join('\n'), 12000);
}

function termsPresent(text, terms) {
  const lower = safeText(text, 12000).toLowerCase();
  return terms.filter((term) => lower.includes(term));
}

function analyzeIntrospectionCausality(invocations = [], modelRuns = [], correctionText = '', desiredBehavior = '') {
  const originalGoal = invocations.map(requestTextFromInvocation).filter(Boolean).join('\n').slice(0, 1200) || 'Unknown from stored invocation data.';
  const retrievedCaseIds = [...new Set([
    ...invocations.flatMap((inv) => inv.retrievedCaseIds || []),
    ...modelRuns.flatMap((run) => run?.retrievalSet || []),
  ])].slice(0, 30);
  const requestText = invocations.map(requestTextFromInvocation).join('\n');
  const responseText = invocations.map(responseTextFromInvocation).join('\n');
  const correction = safeText(correctionText, 4000);
  const combinedGoal = `${originalGoal}\n${correction}\n${desiredBehavior}`;
  const goalTerms = termsPresent(combinedGoal, ['connector', 'schema', 'capability', 'capabilities', 'tool', 'tools', 'brain', 'operation', 'pump', 'chatgpt', 'backend', 'mcp', 'introspection', 'operational', 'health', 'bikini', 'bottom']);
  const requestGoalOverlap = termsPresent(requestText, goalTerms);
  const responseGoalTermOverlap = termsPresent(responseText, goalTerms);
  const retrievalTerms = termsPresent(responseText, ['humane guardrail', 'humane guardrails', 'degraded-state', 'bounded authority', 'googly', 'self service bible', 'chapel', 'no chaplain', 'joke', 'relational responsiveness']);
  const correctionNamesRetrieval = /retrieval|hijack|hijacked|contaminat|wrong.*case|humane|guardrail|answered.*instead|wrong crime scene/i.test(correction);
  const connectorGoal = goalTerms.some((term) => ['connector', 'schema', 'capability', 'capabilities', 'tool', 'tools', 'operation', 'pump', 'chatgpt'].includes(term));
  const humaneCaseIds = retrievedCaseIds.filter((id) => id === 'sr_case_humane_guardrail_prospector_001' || /humane|guardrail/i.test(id));
  const responseHasRequestTerms = responseGoalTermOverlap.length > 0;
  const retrievalDominance = (correctionNamesRetrieval || connectorGoal) && humaneCaseIds.length > 0 && retrievalTerms.length > 0 && (!responseHasRequestTerms || retrievalTerms.length >= requestGoalOverlap.length);
  const routeSummary = invocations.map((inv) => ({invocationId: inv.invocationId, mode: inv.mode || '', layer: inv.route?.layer || '', retrieval_policy: inv.route?.retrieval_policy || '', response_contract: inv.route?.response_contract || '', retrievedCaseIds: inv.retrievedCaseIds || []}));
  if (retrievalDominance) {
    return {
      originalGoal,
      actualGoal: safeText(desiredBehavior, 1200) || correction || 'Explain why the prior response followed retrieved evidence instead of the requested capability/schema task.',
      mismatch: 'Retrieval-dominance failure: the response followed a strong retrieved case instead of the user requested capability/schema introspection task.',
      failedAssumption: 'A relevant corpus hit was treated as the answer frame even though the request layer required capability and connector-boundary inspection first.',
      ignoredEvidence: retrievedCaseIds,
      whatShouldHaveHappened: 'Start from the stored request and route, inspect backend versus ChatGPT-visible capability evidence, then mention retrieved cases only if they support that capability analysis.',
      proposedBehavioralUpdate: safeText(desiredBehavior, 1200) || 'When the request asks for connector, schema, capability, or tool-surface status, preserve that task layer and treat retrieved corpus cases as evidence, not as the response frame.',
      causalChain: [
        `request_goal=${safeText(originalGoal, 240)}`,
        `route=${routeSummary.map((route) => `${route.layer || 'unknown'}/${route.retrieval_policy || 'unknown'}`).join(',')}`,
        `retrieval=${retrievedCaseIds.join(',') || 'none'}`,
        `response_retrieval_terms=${retrievalTerms.join(',') || 'none'}`,
        `correction=${safeText(correction, 240) || 'none'}`,
      ],
      retrievalDominanceDetected: true,
      contaminatingCaseIds: humaneCaseIds,
      responseGoalOverlap: responseGoalTermOverlap,
      requestGoalOverlap,
      responseRetrievalOverlap: retrievalTerms,
      durableRuleKind: 'retrieval_layer_guard',
      routeSummary,
    };
  }
  const interpreted = interpretCorrection(correction, 'other', desiredBehavior || '');
  return {
    originalGoal,
    actualGoal: safeText(desiredBehavior, 1200) || correction || 'The corrected behavior needs to be inferred from the user correction.',
    mismatch: interpreted.failed,
    failedAssumption: interpreted.failed,
    ignoredEvidence: retrievedCaseIds.slice(0, 20),
    whatShouldHaveHappened: interpreted.rule,
    proposedBehavioralUpdate: interpreted.rule,
    causalChain: [
      `request_goal=${safeText(originalGoal, 240)}`,
      `route=${routeSummary.map((route) => `${route.layer || 'unknown'}/${route.retrieval_policy || 'unknown'}`).join(',')}`,
      `retrieval=${retrievedCaseIds.join(',') || 'none'}`,
      `correction=${safeText(correction, 240) || 'none'}`,
    ],
    retrievalDominanceDetected: false,
    contaminatingCaseIds: [],
    responseGoalOverlap: responseGoalTermOverlap,
    requestGoalOverlap,
    responseRetrievalOverlap: retrievalTerms,
    durableRuleKind: 'generic_correction',
    routeSummary,
  };
}

function buildValidationPlan({invocations = [], causal = {}, correctionText = '', desiredBehavior = ''}) {
  const first = invocations[0] || {};
  const contract = first.route?.response_contract || first.consultGoal?.responseContract || 'unknown';
  const layer = first.route?.layer || 'unknown';
  return {
    fixture_name: causal.retrievalDominanceDetected ? 'retrieval_dominance_replay' : 'stored_invocation_correction_replay',
    source_invocation_ids: invocations.map((inv) => inv.invocationId),
    route_layer: layer,
    response_contract: contract,
    correction_summary: safeText(correctionText, 500),
    expected_failure_before_fix: causal.mismatch || 'Stored response does not honor the corrected behavior.',
    expected_behavior_after_fix: safeText(desiredBehavior, 1000) || causal.whatShouldHaveHappened || 'Analogous invocation preserves the request layer before retrieved evidence.',
    required_checks: [
      'replay analogous request',
      'verify route and response_contract are preserved',
      'verify contaminating corpus is absent from the main answer',
      'verify evidence_references are supporting only',
      'validate correction with laterInvocationId when the replay passes',
    ],
  };
}

async function handleCorrect(admin, args, extra) {
  const caller = await callerFromExtra(admin, extra);
  const correctionId = `srcorr_${Date.now()}_${randomUUID().slice(0, 8)}`;
  const correctionType = CORRECTION_TYPES.includes(args.correctionType) ? args.correctionType : 'other';
  const scope = CORRECTION_SCOPES.includes(args.scope) ? args.scope : 'this invocation';
  if (scope === 'global' && args.explicitGlobalIntent !== true) {
    const err = new Error('Global She-Raw corrections require explicitGlobalIntent=true.');
    err.status = 400;
    throw err;
  }
  const verbatim = boundedRawText(args.correctionText || args.userCorrection || '', 6000);
  const interpreted = interpretCorrection(verbatim, correctionType, args.desiredBehavior || '');
  const correction = {
    correctionId,
    invocationId: safeText(args.invocationId, 180),
    caller,
    correctionType,
    scope,
    projectKey: safeText(args.projectKey, 120),
    pattern: safeText(args.pattern, 160),
    verbatim: redactSecrets(verbatim),
    interpretation: interpreted.failed,
    proposedRule: interpreted.rule,
    state: 'interpreted',
    createdAtMs: nowMs(),
  };
  await collection(admin, SHE_RAW_COLLECTIONS.corrections).doc(correctionId).set(correction);
  const ruleId = `srrule_${shortHash(`${correctionId}:${interpreted.rule}`, 20)}`;
  const requiresConfirmation = scope === 'global';
  if (!requiresConfirmation) {
    await collection(admin, SHE_RAW_COLLECTIONS.behavioralRules).doc(ruleId).set({
      ruleId,
      sourceCorrectionId: correctionId,
      rule: interpreted.rule,
      scope,
      projectKey: correction.projectKey,
      pattern: correction.pattern || slug(correctionType, 'pattern'),
      confidence: 0.66,
      validationCount: 0,
      createdAtMs: nowMs(),
      updatedAtMs: nowMs(),
    });
    await collection(admin, SHE_RAW_COLLECTIONS.corrections).doc(correctionId).set({state: 'applied', appliedRuleId: ruleId}, {merge: true});
  }
  await recordAudit(admin, 'correction_recorded', {correctionId, invocationId: correction.invocationId, scope, correctionType});
  return {correction_id: correctionId, state: requiresConfirmation ? 'interpreted' : 'applied', interpretation: interpreted.failed, proposed_behavioral_update: interpreted.rule, applied_rule_id: requiresConfirmation ? '' : ruleId, confirmation_required: requiresConfirmation};
}

async function handleIntrospect(admin, args, extra) {
  const caller = await callerFromExtra(admin, extra);
  const ids = safeList(args.invocationIds || (args.invocationId ? [args.invocationId] : []), 10, 180);
  if (!ids.length) {
    const err = new Error('She-Raw introspection requires invocationId or invocationIds.');
    err.status = 400;
    err.code = 'SHE_RAW_INTROSPECTION_TARGET_REQUIRED';
    throw err;
  }
  const invocations = [];
  for (const id of ids) {
    const invocation = await getInvocation(admin, id);
    if (invocation) invocations.push(invocation);
  }
  if (!invocations.length) {
    const err = new Error('No stored She-Raw invocation found for introspection target.');
    err.status = 404;
    err.code = 'SHE_RAW_INTROSPECTION_TARGET_NOT_FOUND';
    throw err;
  }
  const correctionText = safeText(args.userCorrection, 4000);
  const modelRuns = [];
  for (const invocation of invocations) {
    const run = await getModelRun(admin, invocation.modelRunId);
    if (run) modelRuns.push(run);
  }
  const causal = analyzeIntrospectionCausality(invocations, modelRuns, correctionText, args.desiredBehavior || '');
  const validationPlan = args.requestValidationPlan === true ? buildValidationPlan({invocations, causal, correctionText, desiredBehavior: args.desiredBehavior || ''}) : null;
  const introspectionId = `srintro_${Date.now()}_${randomUUID().slice(0, 8)}`;
  const payload = {
    introspectionId,
    invocationIds: ids,
    caller,
    userCorrection: redactSecrets(correctionText),
    originalGoalAsUnderstood: causal.originalGoal,
    actualGoal: causal.actualGoal,
    mismatch: causal.mismatch,
    failedAssumption: causal.failedAssumption,
    ignoredEvidence: causal.ignoredEvidence,
    whatShouldHaveHappened: causal.whatShouldHaveHappened,
    proposedBehavioralUpdate: causal.proposedBehavioralUpdate,
    proposedScope: safeText(args.applyScope, 80) || 'this pattern',
    causalChain: causal.causalChain,
    retrievalDominanceDetected: causal.retrievalDominanceDetected,
    contaminatingCaseIds: causal.contaminatingCaseIds,
    responseGoalOverlap: causal.responseGoalOverlap,
    requestGoalOverlap: causal.requestGoalOverlap,
    responseRetrievalOverlap: causal.responseRetrievalOverlap,
    durableRuleKind: causal.durableRuleKind,
    routeSummary: causal.routeSummary,
    validationPlan,
    evidenceComplete: invocations.length > 0 && modelRuns.length === invocations.filter((inv) => inv.modelRunId).length,
    inspectedModelRunIds: modelRuns.map((run) => run.modelRunId),
    confidence: modelRuns.length ? 0.74 : 0.62,
    confirmationRequired: (safeText(args.applyScope, 80) === 'global'),
    createdAtMs: nowMs(),
  };
  await collection(admin, SHE_RAW_COLLECTIONS.introspections).doc(introspectionId).set(payload);
  return {
    introspection_id: introspectionId,
    original_goal_as_understood: payload.originalGoalAsUnderstood,
    actual_goal: payload.actualGoal,
    mismatch: payload.mismatch,
    failed_assumption: payload.failedAssumption,
    ignored_evidence: payload.ignoredEvidence,
    what_should_have_happened: payload.whatShouldHaveHappened,
    proposed_behavioral_update: payload.proposedBehavioralUpdate,
    proposed_scope: payload.proposedScope,
    causal_chain: payload.causalChain,
    retrieval_dominance_detected: payload.retrievalDominanceDetected,
    contaminating_case_ids: payload.contaminatingCaseIds,
    response_goal_overlap: payload.responseGoalOverlap,
    request_goal_overlap: payload.requestGoalOverlap,
    response_retrieval_overlap: payload.responseRetrievalOverlap,
    durable_rule_kind: payload.durableRuleKind,
    route_summary: payload.routeSummary,
    validation_plan: payload.validationPlan,
    evidence_complete: payload.evidenceComplete,
    confidence: payload.confidence,
    confirmation_required: payload.confirmationRequired,
  };
}

async function handleFeedback(admin, args, extra) {
  const caller = await callerFromExtra(admin, extra);
  const rating = FEEDBACK_RATINGS.includes(args.rating) ? args.rating : 'useful';
  const feedbackId = `srfb_${Date.now()}_${randomUUID().slice(0, 8)}`;
  await collection(admin, SHE_RAW_COLLECTIONS.feedback).doc(feedbackId).set({feedbackId, caller, invocationId: safeText(args.invocationId, 180), rating, note: safeText(args.note, 2000), createdAtMs: nowMs()});
  await recordAudit(admin, 'feedback_recorded', {feedbackId, invocationId: safeText(args.invocationId, 180), rating});
  return {feedback_id: feedbackId, rating};
}

async function handleReviewLearning(admin, args, extra) {
  await callerFromExtra(admin, extra);
  const correctionId = safeText(args.correctionId, 180);
  const snap = await collection(admin, SHE_RAW_COLLECTIONS.corrections).doc(correctionId).get();
  if (!snap.exists) throw Object.assign(new Error('correctionId not found.'), {status: 404});
  const correction = snap.data() || {};
  const rules = await activeRules(admin, {projectKey: correction.projectKey});
  return {correction_id: correctionId, correction_state: correction.state || 'received', interpretation: correction.interpretation || '', proposed_rule: correction.proposedRule || '', active_rules: rules.filter((r) => r.sourceCorrectionId === correctionId)};
}

async function handleValidateCorrection(admin, args, extra) {
  const caller = await callerFromExtra(admin, extra);
  const validationId = `srval_${Date.now()}_${randomUUID().slice(0, 8)}`;
  const correctionId = safeText(args.correctionId, 180);
  const succeeded = args.succeeded === true;
  await collection(admin, SHE_RAW_COLLECTIONS.correctionValidations).doc(validationId).set({validationId, correctionId, caller, succeeded, evidence: safeText(args.evidence, 4000), laterInvocationId: safeText(args.laterInvocationId, 180), createdAtMs: nowMs()});
  const corrSnap = await collection(admin, SHE_RAW_COLLECTIONS.corrections).doc(correctionId).get();
  const corr = corrSnap.exists ? corrSnap.data() || {} : {};
  if (corr.appliedRuleId) {
    const delta = succeeded ? 1 : 0;
    await collection(admin, SHE_RAW_COLLECTIONS.behavioralRules).doc(corr.appliedRuleId).set({validationCount: delta, lastValidationSucceeded: succeeded, updatedAtMs: nowMs()}, {merge: true});
  }
  await collection(admin, SHE_RAW_COLLECTIONS.corrections).doc(correctionId).set({state: succeeded ? 'validated' : 'observed'}, {merge: true});
  return {validation_id: validationId, correction_id: correctionId, succeeded};
}

async function listActiveRules(admin, args, extra) {
  await callerFromExtra(admin, extra);
  return {rules: await activeRules(admin, {projectKey: args.projectKey})};
}

async function forgetRule(admin, args, extra) {
  const caller = await callerFromExtra(admin, extra);
  const ruleId = safeText(args.ruleId, 180);
  await collection(admin, SHE_RAW_COLLECTIONS.behavioralRules).doc(ruleId).set({disabledAtMs: nowMs(), disabledBy: caller.actor, supersededBy: safeText(args.supersededBy, 180), forgetReason: safeText(args.reason, 1000)}, {merge: true});
  return {rule_id: ruleId, disabled: true};
}


async function handleListBrainJars(admin, _args, extra) {
  await callerFromExtra(admin, extra);
  return {
    service: 'she-raw-mcp',
    she_raw_default_voice: true,
    runtime_rule: 'She-Raw MCP owns invocation, default voice, persistence, and response shaping. Agent Closet is source/provenance for imported brain jars, not She-Raw\'s runtime home.',
    brains: listBrainJars(),
  };
}

async function handleBrainJar(admin, args, extra) {
  const caller = await callerFromExtra(admin, extra);
  const brain = getBrainJar(args.brainId || args.brain_id);
  const route = routeSheRawRequest({...args, brainId: brain.brainId}, {mode: 'explicit'});
  const commandState = route.command_state;
  const gate = gateInvocation({mode: 'explicit', commandState, explicit: true});
  const invocationId = `srbrain_${Date.now()}_${randomUUID().slice(0, 8)}`;
  const boundedContext = redactSecrets(args.boundedContext || '');
  if (gate.blocked) {
    const invocation = {invocationId, caller, mode: 'brain', route, brainId: brain.brainId, commandState, blocked: true, blockReason: gate.reason, inputSummary: safeText(boundedContext, 1000), createdAtMs: nowMs()};
    await persistInvocation(admin, invocation);
    return {invocation_id: invocationId, brain_id: brain.brainId, blocked: true, reason: gate.reason, command_state: commandState};
  }
  const query = [brain.displayName, brain.role, brain.primaryQuestion, boundedContext, args.question, args.projectKey].filter(Boolean).join('\n');
  const rawCases = await retrieveCases(admin, query, {projectKey: args.projectKey});
  const rawRules = await activeRules(admin, {projectKey: args.projectKey, query, route});
  const {cases, rules} = applyRoutePolicy({route, cases: rawCases, rules: rawRules, brain, query});
  const output = deterministicBrainJarResponse({brain, boundedContext, question: args.question, cases, rules});
  const modelRunId = `srmodel_${Date.now()}_${randomUUID().slice(0, 8)}`;
  await collection(admin, SHE_RAW_COLLECTIONS.modelRuns).doc(modelRunId).set({
    modelRunId,
    provider: process.env.SHE_RAW_MODEL_PROVIDER || 'deterministic-local',
    model: process.env.SHE_RAW_MODEL || 'she-raw-brain-jar-heuristic-v1',
    promptVersion: PROMPT_VERSION,
    retrievalSet: cases.map((c) => c.id),
    requestSize: JSON.stringify(args || {}).length,
    responseSize: JSON.stringify(output || {}).length,
    latencyMs: 0,
    structuredOutputValid: true,
    createdAtMs: nowMs(),
  });
  await persistInvocation(admin, {
    invocationId,
    caller,
    mode: 'brain',
    brainId: brain.brainId,
    commandState,
    conversationKey: safeText(args.conversationKey, 180),
    projectKey: safeText(args.projectKey, 120),
    boundedContext,
    route,
    requestedPerspective: `${brain.displayName} brain jar`,
    fullRequestSnapshot: {
      conversationKey: safeText(args.conversationKey, 180),
      projectKey: safeText(args.projectKey, 120),
      commandState,
      boundedContext,
      question: safeText(args.question, 1000),
      brainId: brain.brainId,
      route,
      consultGoal: buildConsultGoal({...args, boundedContext, requestedPerspective: `${brain.displayName} brain jar`}, route, null),
    },
    consultGoal: buildConsultGoal({...args, boundedContext, requestedPerspective: `${brain.displayName} brain jar`}, route, null),
    responseBudget: safeText(args.responseBudget, 80),
    retrievedCaseIds: cases.map((c) => c.id),
    activeRuleIds: rules.map((r) => r.ruleId),
    modelRunId,
    response: output,
    blocked: false,
    createdAtMs: nowMs(),
  });
  return {
    invocation_id: invocationId,
    brain_id: brain.brainId,
    she_raw_default_voice: true,
    source: brain.source,
    source_refs: safeList(brain.sourceRefs, 20, 400),
    sourceRefs: safeList(brain.sourceRefs, 20, 400),
    ...output,
  };
}

async function handleAmbient(admin, args, extra) {
  const commandState = cleanCommandState(args.commandState);
  const gate = gateInvocation({mode: 'ambient', commandState});
  if (gate.blocked) return {type: 'blocked by execution', blocked: true, reason: gate.reason};
  const decision = randomDecision(args || {});
  if (!decision.appears) return {type: 'no intervention', blocked: false, reason: decision.reason || 'random_no_intervention', probability: decision.probability};
  const consult = await handleConsult(admin, {...args, commandState}, extra, 'random');
  return {type: 'operational intervention', ...consult, random: {probability: decision.probability, roll: decision.roll}};
}

async function handleRecreational(admin, args, extra) {
  await callerFromExtra(admin, extra);
  const gate = gateInvocation({mode: 'recreational', commandState: args.commandState});
  if (gate.blocked) return {type: 'blocked by execution', blocked: true, reason: gate.reason};
  const context = safeText(args.boundedContext, 1000);
  return {type: 'recreational disruption', text: context ? `She-Raw taps the glass: ${context.slice(0, 120)} ... are we sure that is the real object?` : 'She-Raw taps the glass: delightful nonsense, no mutation requested.', destructive: false, useful_claim: false};
}

async function handleReview(admin, args, extra) {
  const consult = await handleConsult(admin, {conversationKey: args.conversationKey || 'review', projectKey: args.projectKey, commandState: args.commandState || 'completed', boundedContext: args.completedWorkSummary || args.boundedContext || '', requestedPerspective: 'completed work review'}, extra, 'explicit');
  return {...consult, accidental_infrastructure: consult.likely_treasure, corpus_candidate_hint: 'Promote only if later implementation or explicit user confirmation supports it.'};
}

async function searchCorpus(admin, args, extra) {
  await callerFromExtra(admin, extra);
  const cases = await retrieveCases(admin, args.query || '', {projectKey: args.projectKey, status: args.status});
  return {cases: cases.map((c) => ({id: c.id, title: c.title, type: c.type, status: c.status, source_refs: c.sourceRefs, confidence: c.confidence, retrieval_score: c.retrievalScore, lesson: c.lesson}))};
}

async function getCase(admin, args, extra) {
  await callerFromExtra(admin, extra);
  const caseId = safeText(args.caseId, 180);
  const snap = await collection(admin, SHE_RAW_COLLECTIONS.corpusCases).doc(caseId).get();
  if (!snap.exists) throw Object.assign(new Error('caseId not found.'), {status: 404});
  return {case: cleanCase({id: snap.id, ...(snap.data() || {})})};
}

async function setCommandState(admin, args, extra) {
  const caller = await callerFromExtra(admin, extra);
  const conversationKey = safeText(args.conversationKey, 180) || 'default';
  const projectKey = safeText(args.projectKey, 120);
  const state = cleanCommandState(args.state);
  const id = shortHash(`${conversationKey}:${projectKey || 'global'}`, 32);
  const payload = {stateId: id, conversationKey, projectKey, state, updatedAtMs: nowMs(), updatedBy: caller.actor, reason: safeText(args.reason, 1000)};
  await collection(admin, SHE_RAW_COLLECTIONS.conversationState).doc(id).set(payload, {merge: true});
  await recordAudit(admin, 'command_state_set', {conversationKey, projectKey, state});
  return {conversation_key: conversationKey, project_key: projectKey, state};
}

function roadCall(operation, args = {}) {
  return {tool: 'she_raw_operation', arguments: {operation, args}};
}

function roadConsultArgs(args = {}) {
  return {
    conversationKey: safeText(args.conversationKey || args.conversation_key, 180) || 'stable-chat-key',
    projectKey: safeText(args.projectKey || args.project_key, 120) || undefined,
    commandState: cleanCommandState(args.commandState || args.command_state || 'idle'),
    boundedContext: safeText(args.boundedContext || args.bounded_context || 'Current She-Raw road check context.', 1200),
    requestedPerspective: safeText(args.requestedPerspective || args.requested_perspective || 'operational self-check', 240) || undefined,
    responseBudget: safeText(args.responseBudget || args.response_budget || 'brief', 80) || 'brief',
  };
}

async function handleRoadCheck(admin, args = {}, extra = {}) {
  await callerFromExtra(admin, extra);
  const visibleTools = safeList(args.visibleTools || args.visible_tools || [], 80, 120);
  const commandState = cleanCommandState(args.commandState || args.command_state || 'idle');
  const projectKey = safeText(args.projectKey || args.project_key, 120);
  const registry = sheRawOperationRegistry();
  const h = await health(admin);
  const rules = await activeRules(admin, {projectKey});
  const degraded = [];
  const blocked = [];
  if (h.model_availability === 'deterministic_fallback') degraded.push('model lane is deterministic_fallback until a model provider is configured');
  if (h.corpus_revision === 'local-seed') degraded.push('corpus revision is local-seed; canonical GitHub corpus sync is not configured');
  if (h.github_sync_status === 'not_configured') degraded.push('GitHub corpus sync is not configured');
  if (!h.last_successful_backup) degraded.push('last_successful_backup is empty');
  if (rules.some((rule) => Number(rule.validationCount || 0) === 0)) degraded.push('active learned rules have zero validation count');
  if (visibleTools.length && !visibleTools.includes('she_raw_operation')) blocked.push('visible connector schema does not expose she_raw_operation');
  if (visibleTools.length && !visibleTools.includes('she_raw_brain')) degraded.push('visible connector schema hides she_raw_brain; use she_raw_operation operation=brain.invoke or she_raw_consult brain compatibility route');
  if (visibleTools.length && !visibleTools.includes('she_raw_list_brains')) degraded.push('visible connector schema hides she_raw_list_brains; use she_raw_operation operation=brain.list or she_raw_consult compatibility route');
  if (commandState === 'executing') blocked.push('ambient, recreational, and random She-Raw interventions are blocked during Command Center execution');
  if (h.database_status !== 'ok') blocked.push(`database_status ${h.database_status}`);
  const usableNow = h.service_status === 'ok' && h.database_status === 'ok' && !(visibleTools.length && !visibleTools.includes('she_raw_operation'));
  const brainArgs = {
    brainId: safeText(args.brainId || args.brain_id || 'prospector', 80) || 'prospector',
    conversationKey: safeText(args.conversationKey || args.conversation_key, 180) || 'stable-chat-key',
    projectKey: projectKey || undefined,
    commandState,
    boundedContext: safeText(args.boundedContext || args.bounded_context || 'Inspect the current She-Raw usage road and recover the correct brain-jar path.', 1200),
    question: safeText(args.question || 'What is the smallest proof that this She-Raw road is usable?', 500),
    responseBudget: safeText(args.responseBudget || args.response_budget || 'brief', 80) || 'brief',
  };
  const consultArgs = roadConsultArgs({...args, commandState});
  const nextCalls = [
    roadCall('health', {}),
    roadCall('brain.invoke', brainArgs),
    roadCall('consult', consultArgs),
  ];
  if (args.invocationId || args.invocation_id) {
    nextCalls.push(roadCall('introspect', {
      invocationId: safeText(args.invocationId || args.invocation_id, 180),
      userCorrection: safeText(args.userCorrection || args.user_correction || 'The prior She-Raw response walked the wrong road.', 1000),
      desiredBehavior: 'Recover the request layer, route, retrieval set, response contract, and next usable She-Raw call.',
      applyScope: 'this pattern',
      requestValidationPlan: true,
    }));
  }
  return {
    road_status: blocked.some((lane) => /schema does not expose she_raw_operation|database_status/.test(lane)) ? 'red' : (degraded.length || blocked.length ? 'yellow' : 'green'),
    usable_now: usableNow,
    preferred_tool: 'she_raw_operation',
    direct_connector_visibility: {
      visible_tools_supplied: visibleTools.length > 0,
      she_raw_operation: !visibleTools.length ? 'unknown' : visibleTools.includes('she_raw_operation'),
      she_raw_brain: !visibleTools.length ? 'unknown' : visibleTools.includes('she_raw_brain'),
      she_raw_list_brains: !visibleTools.length ? 'unknown' : visibleTools.includes('she_raw_list_brains'),
      compatibility_route: 'she_raw_consult.brain_jar when only she_raw_consult is visible; she_raw_operation operation=brain.invoke when the operation pump is visible',
    },
    registry_version: registry.version,
    next_calls: nextCalls,
    degraded_lanes: [...new Set(degraded)],
    blocked_lanes: [...new Set(blocked)],
    do_not_do: ['do not create a worker', 'do not dispatch Command Center', 'do not create a new service or connector', 'do not route She-Raw itself into Agent Closet'],
    proof_required: ['she_raw_operation registryVersion', 'srbrain_* for brain.invoke when testing jars', 'srinv_* for consult', 'retrieved case ids for corpus-backed paths', 'blocked_by_command_center_execution for ambient/recreational/random during executing'],
    confidence: usableNow ? 0.84 : 0.62,
  };
}

async function runSheRawOperation(admin, extra, operation, args = {}) {
  const op = safeText(operation, 120);
  const registry = sheRawOperationRegistry();
  if (!op) throw Object.assign(new Error('operation is required.'), {status: 400});
  if (!registry.operations[op]) throw Object.assign(new Error(`Unsupported she_raw_operation operation: ${op}`), {status: 400});
  const operationArgs = safeObject(args);
  if (op === 'manual') return {operation: op, registryVersion: registry.version, result: sheRawManual()};
  if (op === 'health') return {operation: op, registryVersion: registry.version, result: await health(admin)};
  if (op === 'consult') return {operation: op, registryVersion: registry.version, result: await handleConsult(admin, operationArgs, extra, 'explicit')};
  if (op === 'critique') return {operation: op, registryVersion: registry.version, result: await handleCritique(admin, operationArgs, extra)};
  if (op === 'review') return {operation: op, registryVersion: registry.version, result: await handleReview(admin, operationArgs, extra)};
  if (op === 'brain.list') return {operation: op, registryVersion: registry.version, result: await handleListBrainJars(admin, operationArgs, extra)};
  if (op === 'brain.invoke') return {operation: op, registryVersion: registry.version, result: await handleBrainJar(admin, operationArgs, extra)};
  if (op === 'road.check') return {operation: op, registryVersion: registry.version, result: await handleRoadCheck(admin, operationArgs, extra)};
  if (op === 'corpus.search') return {operation: op, registryVersion: registry.version, result: await searchCorpus(admin, operationArgs, extra)};
  if (op === 'corpus.get') return {operation: op, registryVersion: registry.version, result: await getCase(admin, operationArgs, extra)};
  if (op === 'correct') return {operation: op, registryVersion: registry.version, result: await handleCorrect(admin, operationArgs, extra)};
  if (op === 'feedback') return {operation: op, registryVersion: registry.version, result: await handleFeedback(admin, operationArgs, extra)};
  if (op === 'introspect') return {operation: op, registryVersion: registry.version, result: await handleIntrospect(admin, operationArgs, extra)};
  if (op === 'learning.review') return {operation: op, registryVersion: registry.version, result: await handleReviewLearning(admin, operationArgs, extra)};
  if (op === 'correction.validate') return {operation: op, registryVersion: registry.version, result: await handleValidateCorrection(admin, operationArgs, extra)};
  if (op === 'rules.list') return {operation: op, registryVersion: registry.version, result: await listActiveRules(admin, operationArgs, extra)};
  if (op === 'rules.forget') return {operation: op, registryVersion: registry.version, result: await forgetRule(admin, operationArgs, extra)};
  if (op === 'ambient') return {operation: op, registryVersion: registry.version, result: await handleAmbient(admin, operationArgs, extra)};
  if (op === 'recreational') return {operation: op, registryVersion: registry.version, result: await handleRecreational(admin, operationArgs, extra)};
  if (op === 'command_state.set') return {operation: op, registryVersion: registry.version, result: await setCommandState(admin, operationArgs, extra)};
  throw Object.assign(new Error('Unsupported she_raw_operation operation.'), {status: 400});
}

function sheRawManual() {
  const operationRegistry = sheRawOperationRegistry();
  return {
    service: 'she-raw-mcp',
    purpose: 'She-Raw is the MCP runtime and default voice for consultative judgment. ChatGPT remains the conversation; Command Center remains execution. Quartermaster, Prospector, Foreman, and other Agent Closet roles are brain jars accessed through She-Raw MCP; Agent Closet is source/provenance, not She-Raw runtime home.',
    invocationSemantics: {
      directInvocationRule: 'She-Raw is an invoked cognitive organ before she is infrastructure. Do not create a worker, job, service, project, connector, or deployment just because the user invoked the perspective.',
      healthCheckMeaning: 'She-Raw, health check means answer in She-Raw perspective now: status, detected pattern, dangerous question, assumption attack, critique, directed improvement, persistence state, and host routing diagnosis.',
      mcpRole: 'She-Raw MCP owns runtime invocation, default voice, persistence, retrieval, correction, introspection, and brain-jar access. Use she_raw_list_brains to inspect jars and she_raw_brain to invoke Quartermaster/Prospector/etc through She-Raw.',
      commandCenterBoundary: 'If Command Center is executing, ambient/recreational/random She-Raw stays silent. Explicit She-Raw calls remain allowed as perspective calls, but should not dispatch execution unless the user asks.',
    },
    roadRule: {
      preferredTool: 'she_raw_operation',
      recoveryCall: {tool: 'she_raw_operation', arguments: {operation: 'road.check', args: {commandState: 'idle', visibleTools: ['optional ChatGPT-visible tool names']}}},
      rule: 'When the host or connector seems confused, inspect the road before inventing infrastructure. road.check returns exact next-call packets and degraded lanes.',
    },
    startHere: [
      {when: 'ChatGPT or the host is unsure how to use She-Raw, or the visible connector schema may be stale.', call: 'she_raw_operation', args: {operation: 'road.check', args: {commandState: 'idle', visibleTools: ['optional visible tool names']}}},
      {when: 'User says She-Raw, health check or otherwise invokes She-Raw directly.', call: 'direct_perspective_first', args: {answerInChat: true, doNotDispatchWorker: true, useMcpOnlyForPersistenceOrRetrieval: true}},
      {when: 'Need to see available brain jars such as Quartermaster, Prospector, Foreman, Auditor, or Holocron.', call: 'she_raw_list_brains', args: {}},
      {when: 'User asks She-Raw to use Quartermaster, Prospector, Foreman, Auditor, Holocron, Wallfly, Sommelier, or Command Center as a brain in a jar.', call: 'she_raw_brain', args: {brainId: 'quartermaster|prospector|foreman|auditor|holocron|wallfly|sommelier|command_center', conversationKey: 'stable chat/session key', commandState: 'idle|pre_execution|executing|awaiting_user|completed|failed', boundedContext: 'short current context', question: 'optional exact question'}},
      {when: 'User explicitly asks for tool-backed She-Raw consultation, corpus-backed challenge, dangerous question, hidden leverage, or assumption attack.', call: 'she_raw_consult', args: {conversationKey: 'stable chat/session key', projectKey: 'optional repo/project key', commandState: 'idle|pre_execution|executing|awaiting_user|completed|failed', boundedContext: 'short current context', requestedPerspective: 'optional angle', responseBudget: 'brief|normal'}},
      {when: 'User asks for review/critique of a spec, PR, plan, prompt, artifact, or workflow.', call: 'she_raw_critique', args: {targetType: 'plan|pull_request|code_changes|workflow|prompt|architecture_document', targetContent: 'bounded artifact text or summary', critiqueGoal: 'what the critique should optimize for', criteria: 'rules to judge against', severity: 'gentle|standard|hard|hostile_fixture', maxFindings: 5, scopeChallengeAllowed: true}},
      {when: 'User corrects She-Raw or says the prior intervention was wrong, generic, funny, mistimed, or wrong-layer.', call: 'she_raw_correct', args: {invocationId: 'prior She-Raw invocation id if known', correctionText: 'verbatim user correction', correctionType: 'wrong layer|goal misread|bad recommendation|good joke|other', scope: 'this invocation|this project|this pattern|global'}},
      {when: 'Need She-Raw to analyze her own stored response after a correction.', call: 'she_raw_introspect', args: {invocationId: 'prior invocation id', userCorrection: 'verbatim correction', desiredBehavior: 'optional target behavior', applyScope: 'this invocation|this project|this pattern'}},
      {when: 'Normal conversation and no active execution; ask whether She-Raw should speak.', call: 'she_raw_ambient', args: {conversationKey: 'stable chat/session key', commandState: 'idle', boundedContext: 'short current context'}},
    ],
    commandCenterLockout: {
      rule: 'During commandState=executing, ambient, recreational, and random interventions are blocked in code. Explicit consult and requested critique checkpoints are allowed.',
      doNotDo: 'Do not ask She-Raw for ambient or recreational disruption while Command Center is executing.',
    },
    commonFlows: {
      roadCheck: ['she_raw_operation operation=road.check', 'Follow next_calls exactly; do not create workers, services, connectors, or Agent Closet entries.'],
      noReinstallOperationPump: ['she_raw_operation with operation from operationRegistry.operations', 'Use operation=brain.invoke when stale connector schemas hide she_raw_brain.'],
      preExecutionChallenge: ['she_raw_consult with commandState=pre_execution', 'Use proposed_probe only if cheap/reversible.'],
      postExecutionReview: ['she_raw_review with commandState=completed', 'Promote only grounded corpus candidates.'],
      correctionLoop: ['she_raw_correct', 'she_raw_review_learning', 'later she_raw_consult on analogous context', 'she_raw_validate_correction'],
      corpusLookup: ['she_raw_search_corpus', 'she_raw_get_case'],
    },
    operationRegistry,
    preferredStableTool: 'she_raw_operation',
    brainJars: {runtime: 'she-raw-mcp', defaultVoice: 'She-Raw', sourceBoundary: 'Agent Closet provides source/provenance for jars; She-Raw MCP owns invocation and response shaping.', availableBrainIds: SHE_RAW_BRAIN_IDS},
    outputContract: 'Treat evidence_references as grounded, speculation as unproven, and confidence as advisory. Repository/runtime truth overrides She-Raw memory. Brain jars are accessed through She-Raw MCP, not as standalone agents or workers.',
  };
}

async function health(admin) {
  let database = 'unknown';
  try {
    await collection(admin, SHE_RAW_COLLECTIONS.auditEvents).limit(1).get();
    database = 'ok';
  } catch (err) {
    database = `error:${safeText(err.message, 160)}`;
  }
  return {
    service_status: 'ok',
    service: 'she-raw-mcp',
    database_status: database,
    corpus_revision: process.env.SHE_RAW_CORPUS_REVISION || 'local-seed',
    github_sync_status: process.env.SHE_RAW_GITHUB_SYNC_ENABLED === 'true' ? 'configured' : 'not_configured',
    model_availability: process.env.OPENAI_API_KEY ? 'openai_configured' : 'deterministic_fallback',
    last_successful_backup: process.env.SHE_RAW_LAST_BACKUP || '',
    migration_version: 'firestore-vslice-001',
    command_center_lockout: 'enforced_in_code',
    recommended_first_call: 'direct_perspective_first',
    recommended_mcp_first_call: 'she_raw_manual',
    preferred_stable_tool: 'she_raw_operation',
    backend_available_tools: ['she_raw_operation', 'she_raw_brain', 'she_raw_list_brains', 'she_raw_consult', 'she_raw_introspect', 'she_raw_correct', 'she_raw_validate_correction'],
    host_visible_tools: 'unknown_until_road_check_receives_visibleTools',
    compatibility_routes: {
      brain_invoke: 'she_raw_operation operation=brain.invoke',
      brain_list: 'she_raw_operation operation=brain.list',
      consult_brain_jar: 'she_raw_consult with requestedPerspective naming the brain jar',
    },
    road_check: {
      tool: 'she_raw_operation',
      operation: 'road.check',
      purpose: 'Recover the stable ChatGPT-to-She-Raw usage path and exact next-call packets without creating new infrastructure.',
    },
    operation_registry: sheRawOperationRegistry(),
    direct_invocation_semantics: 'She-Raw, health check invokes She-Raw default voice directly. Brain jars are accessed through She-Raw MCP; Agent Closet is source/provenance, not runtime home.',
    brain_jar_runtime: 'she-raw-mcp',
    available_brain_ids: SHE_RAW_BRAIN_IDS,
    recommended_first_calls: [
      {tool: 'she_raw_manual', when: 'First time this connector appears or the model is unsure how to use She-Raw.'},
      {tool: 'she_raw_operation', when: 'Preferred stable no-reinstall pump. Use operation=brain.invoke if stale connector schema hides she_raw_brain.'},
      {tool: 'she_raw_list_brains', when: 'Need available brain jars and their source provenance.'},
      {tool: 'she_raw_brain', when: 'Need Quartermaster, Prospector, Foreman, Auditor, Holocron, Wallfly, Sommelier, or Command Center through She-Raw MCP.'},
      {tool: 'she_raw_consult', when: 'Explicit She-Raw consultation, assumption challenge, hidden leverage, or dangerous question.'},
      {tool: 'she_raw_critique', when: 'Directed critique of a concrete artifact.'},
      {tool: 'she_raw_correct', when: 'User corrects a She-Raw response.'},
      {tool: 'she_raw_introspect', when: 'Analyze a prior She-Raw invocation after correction.'},
    ],
    manual: sheRawManual(),
  };
}

function sheRawProtectedResourceMetadata() {
  return {
    resource: SHE_RAW_RESOURCE,
    authorization_servers: [HOME_CENTER_AUTHORIZATION_SERVER_BASE],
    bearer_methods_supported: ['header'],
    scopes_supported: ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/spreadsheets'],
  };
}

function sheRawAuthorizationServerMetadata() {
  return {issuer: HOME_CENTER_AUTHORIZATION_SERVER_BASE, authorization_endpoint: `${HOME_CENTER_AUTHORIZATION_SERVER_BASE}/oauth/authorize`, token_endpoint: `${HOME_CENTER_AUTHORIZATION_SERVER_BASE}/oauth/token`, registration_endpoint: `${HOME_CENTER_AUTHORIZATION_SERVER_BASE}/oauth/register`};
}

function createSheRawMcpServer({admin}) {
  const server = new McpServer({name: 'she-raw-mcp', version: '0.1.0'});

  server.registerTool('she_raw_operation', {title: 'She-Raw operation dispatcher', description: 'Stable no-reinstall operation pump for She-Raw capabilities. Use operation names from she_raw_manual.operationRegistry; operation=brain.invoke invokes Prospector, Quartermaster, and other brain jars when stale connector schemas hide she_raw_brain.', inputSchema: {operation: z.string(), args: z.record(z.string(), z.any()).optional()}}, async (args, extra) => textResult(await runSheRawOperation(admin, extra, args.operation, args.args || {})));
  server.registerTool('she_raw_list_brains', {title: 'List She-Raw brain jars', description: 'List brain jars available through She-Raw MCP. She-Raw remains the runtime/default voice; Agent Closet is source/provenance for imported jars.', inputSchema: {}}, async (args, extra) => textResult(await handleListBrainJars(admin, args || {}, extra)));
  server.registerTool('she_raw_brain', {title: 'Invoke She-Raw brain jar', description: 'Invoke one named brain jar through She-Raw MCP while preserving She-Raw as the default voice and durable invocation runtime.', inputSchema: {brainId: z.string(), conversationKey: z.string(), projectKey: z.string().optional(), commandState: z.enum(COMMAND_STATES).default('idle'), boundedContext: z.string(), question: z.string().optional(), responseBudget: z.string().optional()}}, async (args, extra) => textResult(await handleBrainJar(admin, args || {}, extra)));
  server.registerTool('she_raw_consult', {title: 'She-Raw consult', description: 'Explicit operational consultation that challenges assumptions and proposes a cheap reversible probe.', inputSchema: {conversationKey: z.string(), projectKey: z.string().optional(), commandState: z.enum(COMMAND_STATES).default('idle'), boundedContext: z.string(), requestedPerspective: z.string().optional(), responseBudget: z.string().optional()}}, async (args, extra) => textResult(await handleConsult(admin, args || {}, extra, 'explicit')));
  server.registerTool('she_raw_critique', {title: 'She-Raw critique', description: 'Directed critique of an external artifact with concrete findings and verification methods.', inputSchema: {targetType: z.string(), targetContent: z.string().optional(), sourceReference: z.string().optional(), critiqueGoal: z.string(), criteria: z.string(), severity: z.enum(['gentle', 'standard', 'hard', 'hostile_fixture']).default('standard'), maxFindings: z.number().int().min(1).max(20).default(5), scopeChallengeAllowed: z.boolean().default(false), commandState: z.enum(COMMAND_STATES).optional(), requestedCritiqueCheckpoint: z.boolean().optional()}}, async (args, extra) => textResult(await handleCritique(admin, args || {}, extra)));
  server.registerTool('she_raw_introspect', {title: 'She-Raw introspect', description: 'Analyze prior She-Raw responses from stored request, retrieval, response, correction, and outcomes.', inputSchema: {invocationId: z.string().optional(), invocationIds: z.array(z.string()).optional(), userCorrection: z.string(), desiredBehavior: z.string().optional(), applyScope: z.string().optional(), requestValidationPlan: z.boolean().optional()}}, async (args, extra) => textResult(await handleIntrospect(admin, args || {}, extra)));
  server.registerTool('she_raw_correct', {title: 'She-Raw correct', description: 'Durably record a user correction verbatim and apply a scoped learned rule when allowed.', inputSchema: {invocationId: z.string().optional(), correctionText: z.string(), correctionType: z.enum(CORRECTION_TYPES).default('other'), scope: z.enum(CORRECTION_SCOPES).default('this invocation'), projectKey: z.string().optional(), pattern: z.string().optional(), desiredBehavior: z.string().optional(), explicitGlobalIntent: z.boolean().optional()}}, async (args, extra) => textResult(await handleCorrect(admin, args || {}, extra)));
  server.registerTool('she_raw_feedback', {title: 'She-Raw feedback', description: 'Attach lightweight feedback to an invocation.', inputSchema: {invocationId: z.string(), rating: z.enum(FEEDBACK_RATINGS), note: z.string().optional()}}, async (args, extra) => textResult(await handleFeedback(admin, args || {}, extra)));
  server.registerTool('she_raw_review_learning', {title: 'Review She-Raw learning', description: 'Expose what She-Raw believes she learned from a correction.', inputSchema: {correctionId: z.string()}}, async (args, extra) => textResult(await handleReviewLearning(admin, args || {}, extra)));
  server.registerTool('she_raw_validate_correction', {title: 'Validate She-Raw correction', description: 'Attach later evidence that a correction succeeded or failed.', inputSchema: {correctionId: z.string(), succeeded: z.boolean(), evidence: z.string(), laterInvocationId: z.string().optional()}}, async (args, extra) => textResult(await handleValidateCorrection(admin, args || {}, extra)));
  server.registerTool('she_raw_list_active_rules', {title: 'List She-Raw active rules', description: 'Show active learned behavioral rules.', inputSchema: {projectKey: z.string().optional()}}, async (args, extra) => textResult(await listActiveRules(admin, args || {}, extra)));
  server.registerTool('she_raw_forget_rule', {title: 'Forget She-Raw rule', description: 'Disable or supersede a learned rule while preserving history.', inputSchema: {ruleId: z.string(), reason: z.string().optional(), supersededBy: z.string().optional()}}, async (args, extra) => textResult(await forgetRule(admin, args || {}, extra)));
  server.registerTool('she_raw_ambient', {title: 'She-Raw ambient', description: 'Ask whether She-Raw has a relevant contribution during normal conversation.', inputSchema: {conversationKey: z.string(), projectKey: z.string().optional(), commandState: z.enum(COMMAND_STATES).default('idle'), boundedContext: z.string(), turnKey: z.string().optional()}}, async (args, extra) => textResult(await handleAmbient(admin, args || {}, extra)));
  server.registerTool('she_raw_recreational', {title: 'She-Raw recreational', description: 'Explicit entertaining disruption. It remains context-aware and non-destructive.', inputSchema: {conversationKey: z.string(), commandState: z.enum(COMMAND_STATES).default('idle'), boundedContext: z.string().optional()}}, async (args, extra) => textResult(await handleRecreational(admin, args || {}, extra)));
  server.registerTool('she_raw_review', {title: 'She-Raw review', description: 'Inspect completed work for accidental infrastructure, missed patterns, and corpus candidates.', inputSchema: {conversationKey: z.string().optional(), projectKey: z.string().optional(), commandState: z.enum(COMMAND_STATES).default('completed'), completedWorkSummary: z.string().optional(), boundedContext: z.string().optional()}}, async (args, extra) => textResult(await handleReview(admin, args || {}, extra)));
  server.registerTool('she_raw_search_corpus', {title: 'She-Raw search corpus', description: 'Search canonical cases without invoking a model.', inputSchema: {query: z.string(), projectKey: z.string().optional(), status: z.string().optional()}}, async (args, extra) => textResult(await searchCorpus(admin, args || {}, extra)));
  server.registerTool('she_raw_get_case', {title: 'She-Raw get case', description: 'Retrieve one canonical case with provenance.', inputSchema: {caseId: z.string()}}, async (args, extra) => textResult(await getCase(admin, args || {}, extra)));
  server.registerTool('she_raw_set_command_state', {title: 'Set She-Raw command state', description: 'Record command state for execution-aware silence gates.', inputSchema: {conversationKey: z.string(), projectKey: z.string().optional(), state: z.enum(COMMAND_STATES), reason: z.string().optional()}}, async (args, extra) => textResult(await setCommandState(admin, args || {}, extra)));
  server.registerTool('she_raw_manual', {title: 'She-Raw manual / start here', description: 'Start here when ChatGPT has just attached the She-Raw MCP connector or is unsure how to use it. Returns when to call consult, critique, correct, introspect, ambient, review, and corpus search tools, including the Command Center execution lockout rule.', inputSchema: {}}, async () => textResult(sheRawManual()));
  server.registerTool('she_raw_health', {title: 'She-Raw health / discovery', description: 'Return service status plus recommended_first_calls and the embedded She-Raw manual. Call this or she_raw_manual first when the connector is newly attached.', inputSchema: {}}, async () => textResult(await health(admin)));
  return server;
}

function createSheRawMcpApp({admin}) {
  const app = express();
  app.use(express.json({limit: '2mb'}));
  app.get('/', (_req, res) => res.json({ok: true, service: 'she-raw-mcp', product: 'persistent consultative judgment service', endpoints: ['/mcp'], hasFrontend: false}));
  app.get('/.well-known/oauth-protected-resource', (_req, res) => { res.set('Cache-Control', 'no-store'); res.json(sheRawProtectedResourceMetadata()); });
  app.get('/.well-known/oauth-authorization-server', (_req, res) => { res.set('Cache-Control', 'no-store'); res.json(sheRawAuthorizationServerMetadata()); });
  app.all('/mcp', async (req, res) => {
    if (rejectMissingTransportAuth(req, res)) return;
    if (req.method !== 'POST') {
      res.status(405).json({jsonrpc: '2.0', error: {code: -32000, message: 'Method not allowed.'}, id: null});
      return;
    }
    const server = createSheRawMcpServer({admin});
    const transport = new StreamableHTTPServerTransport({sessionIdGenerator: undefined});
    let closed = false;
    const closeTransport = async () => {
      if (closed) return;
      closed = true;
      await Promise.allSettled([transport.close(), server.close()]);
    };
    try {
      res.on('close', () => { closeTransport().catch(() => {}); });
      await server.connect(transport);
      await transport.handleRequest(req, res, req.body);
    } finally {
      await closeTransport();
    }
  });
  return app;
}

module.exports = {
  SHE_RAW_COLLECTIONS,
  COMMAND_STATES,
  CORRECTION_TYPES,
  CORRECTION_SCOPES,
  FEEDBACK_RATINGS,
  RANDOM_DEFAULTS,
  SHE_RAW_BRAIN_JARS,
  SHE_RAW_BRAIN_IDS,
  sheRawOperationRegistry,
  sheRawOperationNames,
  runSheRawOperation,
  gateInvocation,
  retrieveCases,
  cleanCase,
  redactSecrets,
  createSheRawMcpApp,
  createSheRawMcpServer,
  handleConsult,
  handleCorrect,
  handleIntrospect,
  handleValidateCorrection,
  handleRoadCheck,
  handleListBrainJars,
  handleBrainJar,
  listBrainJars,
  brainJarIdFromConsultArgs,
  routeSheRawRequest,
  routeAllowsRandom,
  applyRoutePolicy,
  consultContextKind,
  sheRawManual,
  health,
};
