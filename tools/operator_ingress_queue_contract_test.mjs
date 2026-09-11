import fs from 'node:fs';
import assert from 'node:assert/strict';

const read = path => fs.readFileSync(path, 'utf8');

const manifest = read('app/src/main/AndroidManifest.xml');
const application = read('app/src/main/java/com/dclar/homecenter/HomeCenterApplication.java');
const queue = read('app/src/main/java/com/dclar/homecenter/OperatorIngressQueue.java');
const main = read('app/src/main/java/com/dclar/homecenter/MainActivity.java');
const gradle = read('app/build.gradle');

// The queue must actually be installed into the Android process, not merely exist as dead source.
assert.match(manifest, /android:name="\.HomeCenterApplication"/);
assert.match(application, /ingressQueue = new OperatorIngressQueue\(this\);/);
assert.match(application, /ingressQueue\.recoverInflight\(\);/);

// Pin the deliberately small compatibility seam into the current MainActivity monolith.
for (const field of [
  'busy',
  'pendingToolConfirmation',
  'pendingAgentTurnAfterGoogleReconnect',
  'activeConversationId',
]) {
  assert.match(application, new RegExp(`declaredField\\(type, "${field}"\\)`));
}
assert.match(application, /getDeclaredMethod\("submitMessage", String\.class, boolean\.class\)/);
assert.match(main, /private boolean busy = false;/);
assert.match(main, /private volatile JSONObject pendingToolConfirmation;/);
assert.match(main, /private String pendingAgentTurnAfterGoogleReconnect = "";/);
assert.match(main, /private String activeConversationId = "";/);
assert.match(main, /private void submitMessage\(String\s+\w+,\s*boolean\s+\w+\)/);

// Reflection is a compatibility seam, so release name minification may not silently invalidate it.
assert.doesNotMatch(gradle, /minifyEnabled\s+true/);

// Ingress is transport, not interpretation. Preserve exact authored text and FIFO order.
assert.match(queue, /new Item\([\s\S]*exactText,[\s\S]*ownerConversation/);
assert.match(queue, /items\.add\(item\);/);
assert.match(queue, /Item item = items\.remove\(0\);/);
assert.doesNotMatch(queue, /exactText\.trim\(\).*new Item/);

// Capacity and persistence both fail closed. Waiting + in-flight is one bounded ownership pool.
assert.match(queue, /static final int MAX_ITEMS = 64;/);
assert.match(queue, /int occupied = items\.size\(\) \+ \(readInflight\(\) == null \? 0 : 1\);/);
assert.match(queue, /if \(occupied >= MAX_ITEMS\) return null;/);
assert.match(queue, /operator ingress cannot restore in-flight item: queue is at capacity/);
assert.match(queue, /restoreInflightToHead\(inflight, "retry_inflight"\)/);
assert.match(queue, /restoreInflightToHead\(inflight, "recover_inflight"\)/);
assert.match(queue, /requireCommit\(/);
assert.match(queue, /operator ingress persistence failed during/);
assert.match(queue, /operator ingress queue state is unreadable/);
assert.match(queue, /operator ingress queue contains an invalid item at index/);
assert.match(queue, /operator ingress queue contains duplicate id/);
assert.match(queue, /operator ingress in-flight state is unreadable/);
assert.doesNotMatch(queue, /private void writeQueue/);
assert.match(application, /Queue is full\. Your text is still in the composer\./);
assert.match(application, /Queue unavailable\. Your text is still in the composer\./);
assert.match(application, /Queued durably\. Current work continues\./);
assert.match(application, /startup queue recovery failed closed/);
assert.match(application, /queueButton\.setEnabled\(false\)/);

// A not-yet-queued thought survives app switches and stays attached to its owning conversation,
// including an in-activity conversation switch that does not fire lifecycle pause/resume.
assert.match(queue, /private static final String KEY_DRAFT_PREFIX = "draft_text:";/);
assert.match(queue, /synchronized String draft\(String conversationId\)/);
assert.match(queue, /synchronized void saveDraft\(String exactText, String conversationId\)/);
assert.match(queue, /remove\(draftKey\(ownerConversation\)\)[\s\S]*\.commit\(\)/);
assert.match(queue, /return KEY_DRAFT_PREFIX \+ \(owner\.isEmpty\(\) \? "_unbound" : owner\);/);
assert.match(application, /private String panelConversationId = "";/);
assert.match(application, /panelConversationId = currentConversationId\(\);/);
assert.match(application, /String restoredDraft = ingressQueue\.draft\(panelConversationId\);/);
assert.match(application, /persistDraftBeforePanelRemoval\(\);/);
assert.match(application, /ingressQueue\.saveDraft\(exact, panelConversationId\);/);
assert.match(application, /rebindDraftIfConversationChanged\(\);/);
assert.match(application, /if \(current\.equals\(panelConversationId\)\) return;/);
assert.match(application, /panelConversationId = current;/);
assert.match(application, /queue draft rebound to conversation/);
assert.match(application, /queue draft persistence failed closed/);
assert.match(application, /exact,[\s\S]*panelConversationId,[\s\S]*"operator_ingress_queue"/);

// A queued thought must not mutate the currently running turn. It waits for busy and barriers.
assert.match(application, /if \(busy \|\| barrier \|\| queued <= 0\) return;/);
assert.doesNotMatch(application, /busyField\.set/);
assert.match(application, /submitMessageMethod\.invoke\(active, dispatch\.text, false\);/);
assert.match(application, /pendingConfirmation != null/);
assert.match(application, /pendingReconnect\.trim\(\)\.isEmpty\(\)/);

// Conversation ownership survives background work. A message cannot leak into another thread.
assert.match(application, /!head\.conversationId\.equals\(currentConversation\)/);
assert.match(application, /Return there to continue\./);

// Dispatch is crash-aware: move to in-flight first; retry/recovery restores the same item to head.
assert.match(queue, /putString\(KEY_INFLIGHT, item\.toJson\(\)\.toString\(\)\)/);
assert.match(queue, /void retryInflight\(String id\)/);
assert.match(queue, /void recoverInflight\(\)/);
assert.match(queue, /items\.add\(0, inflight\);/);
assert.match(application, /ingressQueue\.retryInflight\(dispatch\.id\);/);

// Submission acceptance is not queue acknowledgement. Retain the durable in-flight copy until
// the submitted turn settles, or until a local turn has had a bounded persistence settle window.
assert.match(application, /private static final long MIN_LOCAL_SETTLE_MS = 1200L;/);
assert.match(application, /private String dispatchedItemId = "";/);
assert.match(application, /dispatchedItemId = dispatch\.id;/);
assert.match(application, /dispatchedSawBusy = busyField\.getBoolean\(active\);/);
assert.match(application, /acknowledgeDispatchedItemIfSettled\(busy, barrier\)/);
assert.match(application, /if \(busy \|\| barrier\) return false;/);
assert.match(application, /if \(!dispatchedSawBusy && ageMs < MIN_LOCAL_SETTLE_MS\) return false;/);
assert.match(application, /ingressQueue\.completeDispatch\(dispatchedItemId\);/);
assert.doesNotMatch(application, /submitMessageMethod\.invoke\(active, dispatch\.text, false\);\s*ingressQueue\.completeDispatch/);
assert.match(application, /Message settled, but queue acknowledgement failed\. Recovery may replay it\./);
assert.match(application, /Process recovery may conservatively replay it/);
assert.match(application, /failed to restore rejected queued dispatch/);

// MainActivity records the user turn before it starts the asynchronous network turn. The queue's
// delayed acknowledgement therefore keeps its own durable copy through the dangerous interval.
assert.match(main, /appendUserMessage\(clean, fromVoice\);[\s\S]*recordTranscriptTurn\("user", clean\);[\s\S]*sendAgentTurn\(clean\);/);
assert.match(main, /private void recordTranscriptTurn\(String role, String text\)[\s\S]*persistChatHistory\(\);/);

// Semantic invariant learned from the failure: queue != interrupt.
assert.doesNotMatch(application, /busy_turn_interrupt/);
assert.match(application, /"operator_ingress_queue"/);
assert.match(application, /Queue without interrupting/);
assert.match(application, /Current work continues/);

// Accessibility is part of the feature, not garnish; unchanged liveness text is not re-announced every poll.
assert.match(application, /setAccessibilityLiveRegion\(View\.ACCESSIBILITY_LIVE_REGION_POLITE\)/);
assert.match(application, /setContentDescription\("Queue another Home Center message without interrupting current work"\)/);
assert.match(application, /queueButton\.setMinimumHeight\(dp\(activity, 48\)\)/);
assert.match(application, /input\.setMinimumHeight\(dp\(activity, 48\)\)/);
assert.match(application, /safe\.contentEquals\(current\)/);

console.log('operator ingress queue contract: OK');
