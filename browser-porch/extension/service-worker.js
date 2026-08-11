/* global chrome */
'use strict';

const RELAY = 'http://127.0.0.1:9234/v1';
let pairing = null; // Deliberately memory-only: extension restart revokes authority.
let stopped = false;

chrome.action.onClicked.addListener(async (tab) => {
  stopped = false;
  pairing = null;
  try {
    const intent = await jsonFetch(`${RELAY}/intent`);
    const [probe] = await chrome.scripting.executeScript({target: {tabId: tab.id}, func: probeCurrentTab});
    const observation = probe?.result || {};
    observation.gesture = 'extension_action_click';
    observation.tabId = tab.id;
    observation.tabSessionId = crypto.randomUUID();
    observation.leaseId = crypto.randomUUID();
    if (observation.accountLabel) {
      observation.accountHash = await digest(observation.accountLabel);
      delete observation.accountLabel;
    }
    const result = await jsonFetch(`${RELAY}/pair`, {intent, observation});
    pairing = result.receipt;
    chrome.action.setBadgeText({tabId: tab.id, text: 'ON'});
    chrome.action.setBadgeBackgroundColor({tabId: tab.id, color: '#19723d'});
    poll();
  } catch (error) {
    pairing = null;
    chrome.action.setBadgeText({tabId: tab.id, text: '!'});
    console.warn('Browser Porch pairing refused:', error.message);
  }
});

chrome.tabs.onRemoved.addListener((tabId) => { if (pairing?.tabId === tabId) revoke('tab_closed'); });
chrome.tabs.onUpdated.addListener((tabId, change) => {
  if (pairing?.tabId === tabId && change.url && new URL(change.url).origin !== pairing.origin) revoke('tab_navigated');
});

async function poll() {
  if (!pairing || stopped) return;
  try {
    const command = await jsonFetch(`${RELAY}/command?pairingId=${encodeURIComponent(pairing.pairingId)}`);
    if (command?.command) await execute(command.command);
  } catch (error) {
    if (!/204/.test(error.message)) console.warn('Browser Porch poll:', error.message);
  }
  if (pairing && !stopped) setTimeout(poll, 1500);
}

async function execute(command) {
  const tab = await chrome.tabs.get(pairing.tabId);
  const [probe] = await chrome.scripting.executeScript({target: {tabId: pairing.tabId}, func: probeCurrentTab});
  const current = probe?.result || {};
  const accountHash = current.accountLabel ? await digest(current.accountLabel) : '';
  const envelope = {...command, currentUrl: tab.url, currentAccountHash: accountHash, authenticationState: current.authenticationState};
  const authorization = await jsonFetch(`${RELAY}/authorize`, {pairing, command: envelope});
  if (authorization.mode !== 'observe' || authorization.action !== 'inventory') throw new Error('Extension candidate permits inventory only');
  const result = {ok: true, origin: current.origin, url: current.url, title: current.title, authenticationState: current.authenticationState, accountHash, visibleConversationLinks: current.visibleConversationLinks};
  await jsonFetch(`${RELAY}/complete`, {pairingId: pairing.pairingId, commandId: command.commandId, result});
}

async function revoke(reason) {
  if (!pairing) return;
  const old = pairing;
  pairing = null;
  stopped = true;
  try { await jsonFetch(`${RELAY}/revoke`, {pairingId: old.pairingId, reason}); } catch {}
  try { await chrome.action.setBadgeText({tabId: old.tabId, text: 'OFF'}); } catch {}
}

async function jsonFetch(url, body) {
  const response = await fetch(url, body ? {method: 'POST', headers: {'content-type': 'application/json'}, body: JSON.stringify(body)} : {});
  if (!response.ok) throw new Error(`${response.status} ${(await response.text()).slice(0, 200)}`);
  return response.status === 204 ? null : response.json();
}

async function digest(value) {
  const bytes = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(String(value)));
  return [...new Uint8Array(bytes)].map((byte) => byte.toString(16).padStart(2, '0')).join('');
}

function probeCurrentTab() {
  const loginVisible = [...document.querySelectorAll('button,a')].some((node) => /^(log in|sign up)$/i.test((node.innerText || node.textContent || '').trim()));
  const profile = document.querySelector('[data-testid="profile-button"],button[aria-label*="profile" i],button[aria-label*="account" i]');
  const accountLabel = profile?.getAttribute('aria-label') || profile?.textContent?.trim() || '';
  return {
    origin: location.origin,
    url: location.href,
    title: document.title,
    authenticationState: !loginVisible && accountLabel ? 'dom_verified' : 'unverified',
    accountLabel,
    visibleConversationLinks: [...document.querySelectorAll('a[href*="/c/"]')].slice(0, 200).map((node) => ({href: node.href, title: (node.textContent || '').trim().slice(0, 300)})),
  };
}
