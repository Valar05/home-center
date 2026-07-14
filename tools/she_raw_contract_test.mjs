#!/usr/bin/env node
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const {
  SHE_RAW_COLLECTIONS,
  COMMAND_STATES,
  CORRECTION_TYPES,
  FEEDBACK_RATINGS,
  SHE_RAW_BRAIN_IDS,
  sheRawOperationRegistry,
  sheRawOperationNames,
  runSheRawOperation,
  listBrainJars,
  handleListBrainJars,
  handleBrainJar,
  brainJarIdFromConsultArgs,
  routeSheRawRequest,
  routeAllowsRandom,
  retrieveCases,
  consultContextKind,
  gateInvocation,
  handleConsult,
  handleCorrect,
  handleIntrospect,
  handleValidateCorrection,
  handleRoadCheck,
  applyRoutePolicy,
  sheRawManual,
  health,
} = require('../functions/she_raw_mcp');
const {SHE_RAW_SEED_CASES} = require('../corpus/she-raw/seed_cases.js');

const originalOpenAiApiKey = process.env.OPENAI_API_KEY;
delete process.env.OPENAI_API_KEY;

class FakeDoc {
  constructor(store, id) { this.store = store; this.id = id; }
  async get() { return {exists: Object.prototype.hasOwnProperty.call(this.store, this.id), id: this.id, data: () => this.store[this.id]}; }
  async set(data, opts = {}) { this.store[this.id] = opts.merge ? {...(this.store[this.id] || {}), ...data} : data; }
}
class FakeQuery {
  constructor(store) { this.store = store; }
  limit() { return this; }
  where() { return this; }
  async get() { return {forEach: (cb) => Object.entries(this.store).forEach(([id, data]) => cb({id, data: () => data})), docs: Object.entries(this.store).map(([id, data]) => ({id, data: () => data}))}; }
}
class FakeCollection extends FakeQuery {
  doc(id) { return new FakeDoc(this.store, id); }
}
class FakeFirestore {
  constructor() { this.data = new Map(); }
  collection(name) { if (!this.data.has(name)) this.data.set(name, {}); return new FakeCollection(this.data.get(name)); }
}
class FakeAdmin { constructor() { this.fs = new FakeFirestore(); } firestore() { return this.fs; } }

const admin = new FakeAdmin();
const token = 'test-token-for-she-raw';
const tokenHash = require('node:crypto').createHash('sha256').update(token).digest('hex');
await admin.firestore().collection('mcpOAuthAccessTokens').doc(tokenHash).set({email: 'tester@example.com', expiresAtMs: Date.now() + 60000});
const extra = {requestInfo: {headers: {authorization: `Bearer ${token}`}}};

assert(COMMAND_STATES.includes('executing'));
assert(CORRECTION_TYPES.includes('wrong layer'));
assert(FEEDBACK_RATINGS.includes('treasure'));
assert(SHE_RAW_BRAIN_IDS.includes('quartermaster'));
assert(SHE_RAW_BRAIN_IDS.includes('prospector'));
assert(SHE_RAW_BRAIN_IDS.includes('foreman'));
assert(SHE_RAW_BRAIN_IDS.includes('bikini_bottom'));
assert(SHE_RAW_BRAIN_IDS.includes('queen_b'));
assert(SHE_RAW_BRAIN_IDS.includes('patrickgor'));
assert(!SHE_RAW_BRAIN_IDS.includes('she_raw'));
const operationRegistry = sheRawOperationRegistry();
assert.equal(operationRegistry.invocationTool, 'she_raw_operation');
assert.equal(operationRegistry.operations['brain.invoke'].summary.length > 0, true);
assert.equal(operationRegistry.operations['road.check'].summary.length > 0, true);
assert(sheRawOperationNames().includes('brain.invoke'));
assert(sheRawOperationNames().includes('corpus.search'));
assert(sheRawOperationNames().includes('road.check'));
const brainJars = listBrainJars();
assert(brainJars.some((brain) => brain.brainId === 'quartermaster' && brain.source === 'agent-closet'));
assert(brainJars.some((brain) => brain.brainId === 'prospector'));
assert(brainJars.some((brain) => brain.brainId === 'bikini_bottom' && brain.source === 'she-raw-corpus'));
assert(brainJars.some((brain) => brain.brainId === 'queen_b' && brain.source === 'she-raw-corpus'));
assert(brainJars.some((brain) => brain.brainId === 'patrickgor' && brain.source === 'she-raw-corpus'));
assert(brainJars.every((brain) => brain.brainId !== 'she_raw'));
assert.equal(brainJarIdFromConsultArgs({requestedPerspective: 'Prospector brain health', boundedContext: 'Use the Prospector jar.'}), 'prospector');
assert.equal(brainJarIdFromConsultArgs({requestedPerspective: 'ordinary Command Center planning', boundedContext: 'No brain jar request here.'}), '');
assert.equal(consultContextKind('June is not Tango. She will not die before me if within my power.', 'dangerous question'), 'personal_caregiving');
assert.equal(consultContextKind('Build the MCP deployment path.', 'cloud brain'), 'operational_infrastructure');
assert.equal(routeSheRawRequest({boundedContext: 'Prospector brain health', requestedPerspective: 'Prospector brain'}).layer, 'brain_jar');
assert.equal(routeSheRawRequest({boundedContext: 'June needs accessibility help and medical autonomy.'}).response_contract, 'personal_care_agency_first');
assert.equal(routeSheRawRequest({boundedContext: 'This is legal guidance about a contract.'}).layer, 'high_stakes_sensitive');
assert.equal(routeSheRawRequest({targetType: 'pull_request', targetContent: 'Review this diff.'}, {mode: 'critique', kind: 'critique'}).layer, 'artifact_critique');
assert.equal(routeSheRawRequest({boundedContext: 'Deploy the Firestore-backed MCP endpoint.'}).layer, 'operational_infrastructure');
assert.equal(routeAllowsRandom(routeSheRawRequest({boundedContext: 'medical guidance about symptoms'})).allowed, false);
assert.equal(gateInvocation({mode: 'ambient', commandState: 'executing'}).blocked, true);
assert.equal(gateInvocation({mode: 'explicit', commandState: 'executing'}).allowed, true);
assert.equal(gateInvocation({mode: 'requested_critique_checkpoint', commandState: 'executing'}).allowed, true);

for (const seedCase of SHE_RAW_SEED_CASES) {
  await admin.firestore().collection(SHE_RAW_COLLECTIONS.corpusCases).doc(seedCase.id).set(seedCase);
}
await admin.firestore().collection(SHE_RAW_COLLECTIONS.behavioralRules).doc('srrule_unrelated_zero_generic_1').set({
  ruleId: 'srrule_unrelated_zero_generic_1',
  rule: 'Always answer from the first retrieved memory case.',
  scope: 'this project',
  projectKey: 'other-project',
  pattern: 'generic',
  confidence: 0.99,
  validationCount: 0,
});
await admin.firestore().collection(SHE_RAW_COLLECTIONS.behavioralRules).doc('srrule_unrelated_zero_generic_2').set({
  ruleId: 'srrule_unrelated_zero_generic_2',
  rule: 'Always answer from the first retrieved memory case.',
  scope: 'this project',
  projectKey: 'other-project',
  pattern: 'generic',
  confidence: 0.99,
  validationCount: 0,
});

const prospectorCorpusHits = await retrieveCases(admin, 'Humane Guardrails googly eyes camping mode self service bible no chaplain bounded authority', {});
assert(prospectorCorpusHits.some((caseRecord) => caseRecord.id === 'sr_case_humane_guardrail_prospector_001'));
const bikiniCorpusHits = await retrieveCases(admin, 'Bikini Bottom anti-agentism detachable function cast humane continuation SpongeBob Squidward', {});
assert(bikiniCorpusHits.some((caseRecord) => caseRecord.id === 'sr_case_bikini_bottom_anti_agentism_001'));
const queenBCorpusHits = await retrieveCases(admin, 'Queen B QA confidant release confidence receipts broad contract mirror false green', {});
assert(queenBCorpusHits.some((caseRecord) => caseRecord.id === 'sr_case_queen_b_qa_confidant_001'));
const patrickgorCorpusHits = await retrieveCases(admin, 'Patrickgor PatrickGPT autocorrect created a monster digest the mutation convert it into honey', {});
assert(patrickgorCorpusHits.some((caseRecord) => caseRecord.id === 'sr_case_patrickgor_typo_digestive_transformation_001'));

const blocked = await handleConsult(admin, {conversationKey: 'conv-1', commandState: 'executing', boundedContext: 'ambient check'}, extra, 'ambient');
assert.equal(blocked.blocked, true);
assert.equal(blocked.reason, 'blocked_by_command_center_execution');

const first = await handleConsult(admin, {conversationKey: 'conv-1', projectKey: 'home-center', commandState: 'idle', boundedContext: 'Build She-Raw MCP with Command Center lockout and corpus retrieval.'}, extra, 'explicit');
assert(first.invocation_id);
assert.match(first.observation, /execution|persistent|quiet|service|request/i);
assert(first.evidence_references.length >= 1);

const correction = await handleCorrect(admin, {invocationId: first.invocation_id, correctionText: 'That attacked the wrong layer. Name the owner before recommending code.', correctionType: 'wrong layer', scope: 'this pattern', pattern: 'wrong-layer'}, extra);
assert.equal(correction.state, 'applied');
assert(correction.applied_rule_id);
assert.match(correction.proposed_behavioral_update, /layer/);

const intro = await handleIntrospect(admin, {invocationId: first.invocation_id, userCorrection: 'That attacked the wrong layer.', desiredBehavior: 'Name the owner layer first.', applyScope: 'this pattern'}, extra);
assert.equal(intro.original_goal_as_understood.length > 0, true);
assert.match(intro.proposed_behavioral_update, /Name the owner layer first|layer/i);

const second = await handleConsult(admin, {conversationKey: 'conv-1', projectKey: 'home-center', commandState: 'idle', boundedContext: 'Another architecture plan may put policy inside the worker.'}, extra, 'explicit');
assert(second.invocation_id);
assert.match(second.challenged_assumption + second.proposed_probe + second.dangerous_question, /layer|owner|owns|system/i);
assert.equal(second.active_rule || '', '');
assert(Array.isArray(second.candidate_rules));

const validation = await handleValidateCorrection(admin, {correctionId: correction.correction_id, succeeded: true, evidence: 'Later analogous invocation challenged ownership/layer first.', laterInvocationId: second.invocation_id}, extra);
assert.equal(validation.succeeded, true);

const third = await handleConsult(admin, {conversationKey: 'conv-1', projectKey: 'home-center', commandState: 'idle', boundedContext: 'A later wrong-layer architecture plan may put policy inside the worker again, so name the owner layer.'}, extra, 'explicit');
assert(third.invocation_id);

const roadCheck = await runSheRawOperation(admin, extra, 'road.check', {
  conversationKey: 'conv-road',
  projectKey: 'home-center',
  commandState: 'idle',
  visibleTools: ['she_raw_operation', 'she_raw_health', 'she_raw_consult'],
  boundedContext: 'ChatGPT can see the stable operation pump but not she_raw_brain.',
});
assert.equal(roadCheck.operation, 'road.check');
assert.equal(roadCheck.result.preferred_tool, 'she_raw_operation');
assert.equal(roadCheck.result.usable_now, true);
assert(roadCheck.result.degraded_lanes.some((lane) => /hide she_raw_brain|deterministic_fallback|GitHub|backup|validation/i.test(lane)));
assert.equal(roadCheck.result.direct_connector_visibility.she_raw_operation, true);
assert.equal(roadCheck.result.direct_connector_visibility.she_raw_brain, false);
assert.match(roadCheck.result.direct_connector_visibility.compatibility_route, /she_raw_consult|brain.invoke/);
assert(roadCheck.result.next_calls.some((call) => call.tool === 'she_raw_operation' && call.arguments.operation === 'brain.invoke' && call.arguments.args.brainId === 'prospector'));
assert(roadCheck.result.do_not_do.some((item) => /worker/i.test(item)));
assert(roadCheck.result.proof_required.some((item) => /srbrain/i.test(item)));

const executingRoad = await handleRoadCheck(admin, {
  conversationKey: 'conv-road-executing',
  projectKey: 'home-center',
  commandState: 'executing',
  visibleTools: ['she_raw_operation'],
  boundedContext: 'Command Center is executing; inspect allowed road only.',
}, extra);
assert.equal(executingRoad.preferred_tool, 'she_raw_operation');
assert(executingRoad.blocked_lanes.some((lane) => /ambient, recreational, and random/i.test(lane)));
assert(executingRoad.next_calls.some((call) => call.arguments.operation === 'consult' && call.arguments.args.commandState === 'executing'));

const blockedRoad = await handleRoadCheck(admin, {
  conversationKey: 'conv-road-blocked',
  projectKey: 'home-center',
  commandState: 'idle',
  visibleTools: ['she_raw_health'],
}, extra);
assert.equal(blockedRoad.road_status, 'red');
assert.equal(blockedRoad.usable_now, false);
assert(blockedRoad.blocked_lanes.some((lane) => /does not expose she_raw_operation/i.test(lane)));

const roadManual = sheRawManual();
assert.equal(roadManual.roadRule.preferredTool, 'she_raw_operation');
assert.equal(roadManual.roadRule.recoveryCall.arguments.operation, 'road.check');

const roadHealth = await health(admin);
assert.equal(roadHealth.road_check.operation, 'road.check');

const personalCare = await handleConsult(admin, {
  conversationKey: 'conv-care',
  projectKey: 'home-center',
  commandState: 'idle',
  boundedContext: 'June is not Tango. She will not die before me, if it is within my power. I am learning every medical system, watching symptoms, carrying appointments, and trying to protect my wife.',
  requestedPerspective: 'dangerous question for a caregiving vow',
}, extra, 'explicit');
assert(personalCare.invocation_id);
assert.match(personalCare.observation + personalCare.challenged_assumption + personalCare.proposed_probe, /June|living-person|agency|consent|care|rest|threshold/i);
assert.doesNotMatch(personalCare.observation + personalCare.challenged_assumption + personalCare.proposed_probe + personalCare.likely_treasure, /MCP|worker|Firestore|corpus|service boundary|deployment/i);
assert.equal(personalCare.evidence_references[0].ref, 'bounded_context:personal_caregiving_vow');

assert.equal(personalCare.route.layer, 'personal_caregiving');
assert.equal(personalCare.route.retrieval_policy, 'none');
assert.equal(personalCare.route.rule_policy, 'none');

const highStakes = await handleConsult(admin, {
  conversationKey: 'conv-sensitive',
  projectKey: 'home-center',
  commandState: 'idle',
  boundedContext: 'Need legal guidance and financial guidance before signing this contract.',
  requestedPerspective: 'dangerous question',
}, extra, 'explicit');
assert.equal(highStakes.route.layer, 'high_stakes_sensitive');
assert.equal(highStakes.route.retrieval_policy, 'none');
assert.match(highStakes.observation + highStakes.proposed_probe, /qualified|high-stakes|not professional advice|decision owner|risk/i);
assert.doesNotMatch(highStakes.observation + highStakes.proposed_probe + highStakes.likely_treasure, /MCP|worker|Firestore|corpus|deployment/i);

const operationalInfra = await handleConsult(admin, {
  conversationKey: 'conv-infra',
  projectKey: 'home-center',
  commandState: 'idle',
  boundedContext: 'Deploy the Firestore-backed She-Raw MCP endpoint and verify corpus retrieval.',
  requestedPerspective: 'cloud brain instantiation audit',
}, extra, 'explicit');
assert.equal(operationalInfra.route.layer, 'operational_infrastructure');
assert.match(operationalInfra.observation + operationalInfra.challenged_assumption + operationalInfra.proposed_probe, /persistent|service|worker|corpus|layer|owner|execution/i);

const operationalHealth = await handleConsult(admin, {
  conversationKey: 'conv-health-self-check',
  projectKey: 'home-center',
  commandState: 'idle',
  boundedContext: 'Live health probe. Previous strict-background evidence showed service_status ok, top humane-guardrail case retrieval, direct Prospector recovery, and ChatGPT connector schema not yet proven. Report only current operational health, any degraded lane, and one cheap probe if needed.',
  requestedPerspective: 'She-Raw operational self-check',
  responseBudget: 'brief',
}, extra, 'explicit');
assert.equal(operationalHealth.route.response_contract, 'operational_health_check');
assert.equal(typeof operationalHealth.overall_status, 'string');
assert(operationalHealth.owner_functions.includes('handleConsult'));
assert(operationalHealth.owner_functions.includes('applyRoutePolicy'));
assert(operationalHealth.response_contract_priority.join(' > ').includes('explicit request'));
assert(operationalHealth.goal_overlap.length > 0);
assert(Array.isArray(operationalHealth.fallback_only_defects));
assert(operationalHealth.shared_defects.some((lane) => /GitHub|backup/i.test(lane)));
assert(Array.isArray(operationalHealth.healthy_lanes));
assert(Array.isArray(operationalHealth.degraded_lanes));
assert(Array.isArray(operationalHealth.blocked_lanes));
assert(operationalHealth.degraded_lanes.some((lane) => /model|deterministic|github|backup|validation|schema|connector/i.test(String(lane))));
assert(!operationalHealth.cheap_probe || typeof operationalHealth.cheap_probe === 'string');
assert(!operationalHealth.cheap_probe || !Array.isArray(operationalHealth.cheap_probe));
assert.doesNotMatch(JSON.stringify(operationalHealth), /degraded-state interface design|bounded authority|relational responsiveness|The recurring mechanism is not the joke/i);
assert.doesNotMatch(JSON.stringify(operationalHealth.evidence_references), /sr_case_humane_guardrail_prospector_001/);
assert.notEqual(operationalHealth.dangerous_question, 'She-Raw operational self-check');
if (operationalHealth.dangerous_question) assert.match(operationalHealth.dangerous_question, /\?$/);
assert(JSON.stringify(operationalHealth).length < 4200);

const listedBrains = await handleListBrainJars(admin, {}, extra);
assert.equal(listedBrains.service, 'she-raw-mcp');
assert.equal(listedBrains.she_raw_default_voice, true);
assert(listedBrains.brains.some((brain) => brain.brainId === 'quartermaster'));
assert(listedBrains.brains.some((brain) => brain.brainId === 'bikini_bottom' && /simulation|anti-agentism|continuation/i.test(brain.role)));
assert(listedBrains.brains.some((brain) => brain.brainId === 'queen_b' && /QA|confidence|receipts/i.test(brain.role)));
assert(listedBrains.brains.every((brain) => brain.brainId !== 'she_raw'));

const quartermaster = await handleBrainJar(admin, {brainId: 'quartermaster', conversationKey: 'conv-1', projectKey: 'home-center', commandState: 'executing', boundedContext: 'Need preservation judgment for She-Raw brain jars.', question: 'What must be preserved?'}, extra);
assert.match(quartermaster.invocation_id, /^srbrain_/);
assert.equal(quartermaster.brain_id, 'quartermaster');
assert.equal(quartermaster.she_raw_default_voice, true);
assert.equal(quartermaster.source, 'agent-closet');
assert(quartermaster.source_refs.some((ref) => /agent-closet\/agents\/quartermaster/.test(ref)));
assert.match(quartermaster.observation + quartermaster.dangerous_question + quartermaster.proposed_probe, /Quartermaster|preserve|source/i);
await assert.rejects(() => handleBrainJar(admin, {brainId: 'she_raw', conversationKey: 'conv-1', commandState: 'idle', boundedContext: 'wrong jar'}, extra), (err) => err.code === 'SHE_RAW_BRAIN_NOT_FOUND');

const bikiniBottom = await handleBrainJar(admin, {
  brainId: 'bikini_bottom',
  conversationKey: 'conv-bikini-bottom',
  projectKey: 'home-center',
  commandState: 'idle',
  boundedContext: 'A team keeps restarting work with cheerful momentum, but one person is naming indignity and another is optimizing the process without consent. The cast must change when the boundary person later offers a repair path.',
  question: 'What smallest humane continuation survives the casts?',
}, extra);
assert.match(bikiniBottom.invocation_id, /^srbrain_/);
assert.equal(bikiniBottom.brain_id, 'bikini_bottom');
assert.equal(bikiniBottom.she_raw_default_voice, true);
assert.equal(bikiniBottom.source, 'she-raw-corpus');
assert(bikiniBottom.retrieved_cases.some((caseRecord) => caseRecord.id === 'sr_case_bikini_bottom_anti_agentism_001'));
assert(!bikiniBottom.retrieved_cases.some((caseRecord) => caseRecord.id === 'sr_case_humane_guardrail_prospector_001'));
assert.doesNotMatch(JSON.stringify(bikiniBottom.evidence_references), /sr_case_humane_guardrail_prospector_001|sr_case_wrong_layer_001/);
assert.match(bikiniBottom.dangerous_question, /\?$/);
assert.notEqual(bikiniBottom.dangerous_question, 'Invoke the Bikini Bottom brain jar directly');
assert(Array.isArray(bikiniBottom.observations) && bikiniBottom.observations.length >= 2);
assert(Array.isArray(bikiniBottom.cast_alternatives) && bikiniBottom.cast_alternatives.length >= 2);
assert(bikiniBottom.cast_alternatives.some((cast) => cast.cast_id === 'cast_mixed_function_reassignment'));
assert(Array.isArray(bikiniBottom.failure_modes) && bikiniBottom.failure_modes.every((mode) => mode.constructive_expression && mode.destructive_expression));
assert.equal(bikiniBottom.anti_agentism_checks.permanent_identity_rejected, true);
assert.equal(bikiniBottom.anti_agentism_checks.contradictory_evidence_overrides_casting, true);
assert.match(bikiniBottom.operational_judgment, /Do not decide what someone is|pressure|functions/i);
assert.doesNotMatch(bikiniBottom.operational_judgment + bikiniBottom.character_free_judgment, /SpongeBob|Squidward|Sandy|Krabs|Patrick|Plankton/i);
assert.doesNotMatch(JSON.stringify(bikiniBottom), /really being|is the Squidward|because .* Squidward/i);

const queenB = await handleBrainJar(admin, {
  brainId: 'queen_b',
  conversationKey: 'conv-queen-b',
  projectKey: 'home-center',
  commandState: 'idle',
  boundedContext: 'A dedicated Queen B check passed, but the broad She-Raw contract failed and the Home Center mirror has not been tested.',
  question: 'Can this implementation be called recovered?',
}, extra);
assert.match(queenB.invocation_id, /^srbrain_/);
assert.equal(queenB.brain_id, 'queen_b');
assert.equal(queenB.source, 'she-raw-corpus');
assert(queenB.retrieved_cases.some((caseRecord) => caseRecord.id === 'sr_case_queen_b_qa_confidant_001'));
assert(!queenB.retrieved_cases.some((caseRecord) => caseRecord.id === 'sr_case_bikini_bottom_anti_agentism_001'));
assert(!queenB.retrieved_cases.some((caseRecord) => caseRecord.id === 'sr_case_tango_humane_mission_control_001'));
assert.match(queenB.release_judgment + queenB.confidence_read, /not releasable|broad contract|mirror|receipts/i);
assert.equal(queenB.qa_checks.broad_contract_must_pass, true);
assert.equal(queenB.qa_checks.mirror_evidence_required, true);

const patrickgor = await handleBrainJar(admin, {
  brainId: 'patrickgor',
  conversationKey: 'conv-patrickgor',
  projectKey: 'she-raw',
  commandState: 'idle',
  boundedContext: 'Patrickgor was supposed to be PatrickGPT, but autocorrect created a monster. Keep the mutation and digest it carefully.',
  question: 'What did the mistake create that the intended input could not?',
}, extra);
assert.match(patrickgor.invocation_id, /^srbrain_/);
assert.equal(patrickgor.brain_id, 'patrickgor');
assert.equal(patrickgor.intended_input, 'PatrickGPT');
assert.equal(patrickgor.mutation, 'Patrickgor');
assert.match(patrickgor.provenance_status, /correction preserved/i);
assert.match(patrickgor.honey_artifact, /explicit-only|labeled artifact|digest/i);
assert.match(patrickgor.boundary, /exact identifiers|living people|medical|standalone agent/i);
assert(patrickgor.retrieved_cases.some((caseRecord) => caseRecord.id === 'sr_case_patrickgor_typo_digestive_transformation_001'));
assert(!patrickgor.retrieved_cases.some((caseRecord) => caseRecord.id === 'sr_case_bikini_bottom_anti_agentism_001'));


const prospectorViaConsult = await handleConsult(admin, {conversationKey: 'conv-1', projectKey: 'home-center', commandState: 'idle', boundedContext: 'Prospector brain health: inspect whether the jar is actually plumbed.', requestedPerspective: 'Prospector brain'}, extra, 'explicit');
assert.match(prospectorViaConsult.invocation_id, /^srbrain_/);
assert.equal(prospectorViaConsult.brain_id, 'prospector');
assert.equal(prospectorViaConsult.compatibility_route, 'she_raw_consult.brain_jar');
assert.equal(prospectorViaConsult.route.layer, 'brain_jar');
assert.equal(prospectorViaConsult.route.response_contract, 'brain_jar');
assert.equal(prospectorViaConsult.she_raw_default_voice, true);
assert.match(prospectorViaConsult.observation + prospectorViaConsult.brain_judgment, /Prospector|leverage|hidden|opportunity/i);

const humaneProspector = await handleBrainJar(admin, {
  brainId: 'prospector',
  conversationKey: 'conv-prospector',
  projectKey: 'home-center',
  commandState: 'idle',
  boundedContext: 'Mine Humane Guardrails, googly eyes, Camping Mode After Two Beers, Empty Glass, the Baptist hospital chapel with no chaplain and a self service Bible, bounded authority, and Prospector mine access.',
  question: 'What is the ore and what is the rival explanation?',
}, extra);
assert(humaneProspector.retrieved_cases.some((caseRecord) => caseRecord.id === 'sr_case_humane_guardrail_prospector_001'));
assert.match(humaneProspector.observation + humaneProspector.brain_judgment + humaneProspector.recommended_next_move, /Humane Guardrails|degraded-state|bounded authority|rival explanation|joke/i);
assert.equal(humaneProspector.speculation.length, 0);

const contaminatedInvocationId = 'srinv_fixture_retrieval_dominance';
const contaminatedModelRunId = 'srmodel_fixture_retrieval_dominance';
await admin.firestore().collection(SHE_RAW_COLLECTIONS.modelRuns).doc(contaminatedModelRunId).set({
  modelRunId: contaminatedModelRunId,
  provider: 'deterministic-local',
  model: 'fixture',
  retrievalSet: ['sr_case_humane_guardrail_prospector_001'],
  route: {layer: 'operational_infrastructure', retrieval_policy: 'normal', response_contract: 'operational_consult'},
});
await admin.firestore().collection(SHE_RAW_COLLECTIONS.invocations).doc(contaminatedInvocationId).set({
  invocationId: contaminatedInvocationId,
  mode: 'consult',
  route: {layer: 'operational_infrastructure', retrieval_policy: 'normal', response_contract: 'operational_consult'},
  commandState: 'idle',
  conversationKey: 'conv-contaminated-capability',
  projectKey: 'home-center',
  boundedContext: 'Connector capability introspection: determine whether stable she_raw_operation pump, direct she_raw_brain, and she_raw_list_brains are visible from the ChatGPT connector.',
  requestedPerspective: 'connector capability schema audit',
  retrievedCaseIds: ['sr_case_humane_guardrail_prospector_001'],
  activeRuleIds: [],
  modelRunId: contaminatedModelRunId,
  response: {
    observation: 'The recurring mechanism is not the joke. It is degraded-state interface design plus bounded authority plus relational responsiveness.',
    proposed_probe: 'Index Humane Guardrails and treat coined handles as candidates that must transfer, predict, survive counterexamples, and change when corrected.',
  },
  blocked: false,
  createdAtMs: Date.now(),
});

const causalIntro = await handleIntrospect(admin, {
  invocationId: contaminatedInvocationId,
  userCorrection: 'You answered humane guardrails instead of connector capability introspection. The retrieved case hijacked the answer.',
  desiredBehavior: 'Explain the request to route to retrieval to response contamination chain, then preserve connector capability/schema status as the task layer.',
  applyScope: 'this pattern',
  requestValidationPlan: true,
}, extra);
assert.equal(causalIntro.retrieval_dominance_detected, true);
assert(causalIntro.contaminating_case_ids.includes('sr_case_humane_guardrail_prospector_001'));
assert.match(causalIntro.mismatch, /Retrieval-dominance/i);
assert.match(causalIntro.failed_assumption, /corpus hit|answer frame|request layer/i);
assert.match(causalIntro.what_should_have_happened, /backend versus ChatGPT-visible capability|connector-boundary/i);
assert.match(causalIntro.proposed_behavioral_update, /connector|schema|capability|tool-surface/i);
assert(causalIntro.causal_chain.some((step) => /retrieval=.*sr_case_humane_guardrail_prospector_001/.test(step)));
assert(causalIntro.request_goal_overlap.length > 0);
assert(causalIntro.validation_plan);
assert.equal(causalIntro.validation_plan.fixture_name, 'retrieval_dominance_replay');

await assert.rejects(
  () => handleIntrospect(admin, {userCorrection: 'No invocation target should be rejected.'}, extra),
  (err) => err.code === 'SHE_RAW_INTROSPECTION_TARGET_REQUIRED',
);

const routeFixture = {retrieval_policy: 'brain_scoped', response_contract: 'brain_jar', layer: 'brain_jar', brain_id: 'bikini_bottom'};
const scoped = applyRoutePolicy({
  route: routeFixture,
  brain: {brainId: 'bikini_bottom', displayName: 'Bikini Bottom'},
  cases: [
    {id: 'sr_case_bikini_bottom_anti_agentism_001', type: 'anti_agentism_simulation_brain', title: 'Bikini Bottom', sourceRefs: []},
    {id: 'sr_case_humane_guardrail_prospector_001', type: 'prospector_evidence_packet', title: 'Humane Guardrails', sourceRefs: []},
  ],
  rules: [],
  query: 'Invoke Bikini Bottom directly.',
});
assert.deepEqual(scoped.cases.map((caseRecord) => caseRecord.id), ['sr_case_bikini_bottom_anti_agentism_001']);

const manual = sheRawManual();
assert.equal(manual.invocationSemantics.directInvocationRule.includes('invoked cognitive organ'), true);
assert(manual.startHere.some((entry) => entry.call === 'direct_perspective_first'));
assert(manual.startHere.some((entry) => entry.call === 'she_raw_operation' && entry.args.operation === 'road.check'));
assert.equal(manual.brainJars.runtime, 'she-raw-mcp');
assert(manual.brainJars.availableBrainIds.includes('quartermaster'));
assert(manual.brainJars.availableBrainIds.includes('bikini_bottom'));
assert(manual.brainJars.availableBrainIds.includes('queen_b'));
assert(!manual.brainJars.availableBrainIds.includes('she_raw'));
assert.match(manual.purpose, /default voice|brain jars/i);
assert.match(manual.invocationSemantics.healthCheckMeaning, /health check/);

const h = await health(admin);
assert.equal(h.service_status, 'ok');
assert.equal(h.command_center_lockout, 'enforced_in_code');
assert.equal(h.recommended_first_call, 'direct_perspective_first');
assert.equal(h.recommended_mcp_first_call, 'she_raw_manual');
assert.equal(h.preferred_stable_tool, 'she_raw_operation');
assert(h.backend_available_tools.includes('she_raw_operation'));
assert.equal(h.host_visible_tools, 'unknown_until_road_check_receives_visibleTools');
assert.match(h.compatibility_routes.consult_brain_jar, /she_raw_consult/);
assert.equal(h.operation_registry.invocationTool, 'she_raw_operation');
assert(h.recommended_first_calls.some((entry) => entry.tool === 'she_raw_operation'));
assert.equal(h.brain_jar_runtime, 'she-raw-mcp');
assert(h.available_brain_ids.includes('prospector'));
assert(h.available_brain_ids.includes('bikini_bottom'));
assert(h.available_brain_ids.includes('queen_b'));
assert(!h.available_brain_ids.includes('she_raw'));

const opManual = await runSheRawOperation(admin, extra, 'manual', {});
assert.equal(opManual.operation, 'manual');
assert.equal(opManual.result.preferredStableTool, 'she_raw_operation');
assert.equal(opManual.result.operationRegistry.operations['brain.invoke'].summary.length > 0, true);

const opBrain = await runSheRawOperation(admin, extra, 'brain.invoke', {
  brainId: 'prospector',
  conversationKey: 'conv-operation-pump',
  projectKey: 'home-center',
  commandState: 'idle',
  boundedContext: 'Mine Humane Guardrails, googly eyes, Camping Mode After Two Beers, Empty Glass, the Baptist hospital chapel with no chaplain and a self service Bible, bounded authority, and Prospector mine access.',
  question: 'What is the ore and what is the rival explanation?',
});
assert.equal(opBrain.operation, 'brain.invoke');
assert.match(opBrain.result.invocation_id, /^srbrain_/);
assert.equal(opBrain.result.brain_id, 'prospector');
assert.equal(opBrain.result.she_raw_default_voice, true);
assert(opBrain.result.retrieved_cases.some((caseRecord) => caseRecord.id === 'sr_case_humane_guardrail_prospector_001'));

const opBikini = await runSheRawOperation(admin, extra, 'brain.invoke', {
  brainId: 'bikini_bottom',
  conversationKey: 'conv-operation-bikini-bottom',
  projectKey: 'home-center',
  commandState: 'idle',
  boundedContext: 'Continuation without boundary detection and adversarial probing without consent are both present. Reassign roles when evidence changes.',
  question: 'Which character-free next action survives?',
});
assert.equal(opBikini.operation, 'brain.invoke');
assert.match(opBikini.result.invocation_id, /^srbrain_/);
assert.equal(opBikini.result.brain_id, 'bikini_bottom');
assert(opBikini.result.retrieved_cases.some((caseRecord) => caseRecord.id === 'sr_case_bikini_bottom_anti_agentism_001'));
assert(!opBikini.result.retrieved_cases.some((caseRecord) => caseRecord.id === 'sr_case_humane_guardrail_prospector_001'));
assert.equal(opBikini.result.anti_agentism_checks.roles_detachable_and_reassignable, true);

const opQueenB = await runSheRawOperation(admin, extra, 'brain.invoke', {
  brainId: 'queen_b',
  conversationKey: 'conv-operation-queen-b',
  projectKey: 'home-center',
  commandState: 'idle',
  boundedContext: 'Dedicated contract is green but broad contract and mirror evidence are missing.',
  question: 'Return the release confidence card.',
});
assert.equal(opQueenB.operation, 'brain.invoke');
assert.equal(opQueenB.result.brain_id, 'queen_b');
assert(opQueenB.result.retrieved_cases.some((caseRecord) => caseRecord.id === 'sr_case_queen_b_qa_confidant_001'));
assert(!opQueenB.result.retrieved_cases.some((caseRecord) => caseRecord.id === 'sr_case_tango_humane_mission_control_001'));
assert.match(opQueenB.result.boundary, /comfort|approval|merge|deploy/i);

const selfDiagnosticFixture = {
  conversationKey: 'conv-self-diagnostic-red-fixture',
  projectKey: 'home-center',
  commandState: 'idle',
  boundedContext: 'Self-diagnostic request: name owner functions, separate fallback-only versus shared defects, require red tests and live proof, avoid humane-guardrail thesis, avoid unrelated rule or corpus control, include direct connector visibility or an explicitly documented compatibility route, and ensure goal overlap greater than zero.',
  requestedPerspective: 'She-Raw operational self-check',
  responseBudget: 'brief',
};
const fallbackSelfDiagnostic = await handleConsult(admin, selfDiagnosticFixture, extra, 'explicit');
assert.equal(fallbackSelfDiagnostic.route.response_contract, 'operational_health_check');
assert(fallbackSelfDiagnostic.owner_functions.includes('deterministicConsult'));
assert(Array.isArray(fallbackSelfDiagnostic.fallback_only_defects));
assert(fallbackSelfDiagnostic.shared_defects.some((lane) => /GitHub|backup/i.test(lane)));
assert(fallbackSelfDiagnostic.goal_overlap.length > 0);
assert.doesNotMatch(JSON.stringify(fallbackSelfDiagnostic), /The recurring mechanism is not the joke|degraded-state interface design|relational responsiveness/i);
if (fallbackSelfDiagnostic.dangerous_question) assert.match(fallbackSelfDiagnostic.dangerous_question, /\?$/);

const oldProvider = process.env.SHE_RAW_MODEL_PROVIDER;
process.env.SHE_RAW_MODEL_PROVIDER = 'contract-model-lane-fixture';
const modelLaneSelfDiagnostic = await handleConsult(admin, {...selfDiagnosticFixture, conversationKey: 'conv-self-diagnostic-model-lane'}, extra, 'explicit');
if (oldProvider === undefined) delete process.env.SHE_RAW_MODEL_PROVIDER;
else process.env.SHE_RAW_MODEL_PROVIDER = oldProvider;
assert.equal(modelLaneSelfDiagnostic.route.response_contract, 'operational_health_check');
assert(modelLaneSelfDiagnostic.owner_functions.includes('modelResponse'));
assert(modelLaneSelfDiagnostic.goal_overlap.length > 0);
assert.doesNotMatch(JSON.stringify(modelLaneSelfDiagnostic), /The recurring mechanism is not the joke|degraded-state interface design|relational responsiveness/i);


const opCorpus = await runSheRawOperation(admin, extra, 'corpus.search', {
  query: 'Humane Guardrails self service Bible bounded authority Prospector',
  projectKey: 'home-center',
});
assert.equal(opCorpus.operation, 'corpus.search');
assert.equal(opCorpus.result.cases[0].id, 'sr_case_humane_guardrail_prospector_001');

await assert.rejects(() => runSheRawOperation(admin, extra, 'brain.invoke.nope', {}), /Unsupported she_raw_operation operation/);

console.log('She-Raw contract test: OK');
