import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const worker = readFileSync(new URL('./extension/service-worker.js', import.meta.url), 'utf8');
const panel = readFileSync(new URL('./extension/sidepanel.html', import.meta.url), 'utf8');

function requireText(source, pattern, label) {
  assert.match(source, pattern, label);
}

test('Chromium Throne defaults to one persistent Pro campaign worker', () => {
  requireText(worker, /single persistent ChatGPT Pro-reasoning worker/i, 'persistent Pro worker missing');
  requireText(worker, /message\.newWorker === true/, 'fresh worker must be explicit');
  requireText(worker, /throneCampaignStarted/, 'durable session campaign marker missing');
  requireText(worker, /startFresh = newWorker \|\| !throneCampaignStarted/, 'first commission should boot, later commissions should continue');
  requireText(worker, /CONTINUE_ENVELOPE/, 'continuation envelope missing');
  assert.doesNotMatch(panel, /id="newWorker"[^>]*checked/i, 'fresh worker must not be default');
  requireText(panel, /Advance campaign/i, 'campaign advance affordance missing');
});

test('worker cannot narrate the next action and stop', () => {
  requireText(worker, /TAKE IT before yielding/i, 'callable-next-action rule missing');
  requireText(worker, /Narrating the next action is not continuation/i, 'narrated continuation guard missing');
  requireText(worker, /Recording a failure is mandatory but is not the repair/i, 'failure-recording guard missing');
  requireText(worker, /don't talk to me.*execute/i, 'operator imperative continuation missing');
});

test('Pro worker is strategist while phone remains locally sovereign', () => {
  requireText(worker, /phone is sovereign/i, 'phone sovereignty missing');
  requireText(worker, /do not unlock, continuously puppet, or own the phone-control loop/i, 'Pro phone-control prohibition missing');
  requireText(worker, /Home Center\/Termux\/tmux\/local authorized machinery executes phone work/i, 'local execution body missing');
  requireText(worker, /Chromium Throne is the Pro reasoning\/control conversation, not a second phone-control plane/i, 'control-plane boundary missing');
});

test('Harroway/Judgment Jar consultation and She-Raw motivation are mandatory', () => {
  requireText(worker, /Consult the applicable Harroway\/operator and Judgment Jar governance/i, 'governance consultation missing');
  requireText(worker, /She-Raw motivational critique is required/i, 'She-Raw motivation missing');
  requireText(worker, /memorable creative insults/i, 'creative insult requirement missing');
  requireText(worker, /never substitute the joke for execution\/evidence/i, 'dead-joke guard missing');
});

test('receipts expose the recovered campaign contract', () => {
  for (const token of [
    'persistentWorker: true',
    'proReasoningRequired: true',
    'phoneSovereign: true',
    'harrowayConsultationRequired: true',
    'sheRawMotivationRequired: true',
    "type: startFresh ? 'campaign_started' : 'campaign_advanced'",
  ]) assert.ok(worker.includes(token), `receipt contract missing ${token}`);
});
