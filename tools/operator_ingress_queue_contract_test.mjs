import fs from 'node:fs';
import assert from 'node:assert/strict';

const read = path => fs.readFileSync(path, 'utf8');

const manifest = read('app/src/main/AndroidManifest.xml');
const application = read('app/src/main/java/com/dclar/homecenter/HomeCenterApplication.java');
const queue = read('app/src/main/java/com/dclar/homecenter/OperatorIngressQueue.java');
const main = read('app/src/main/java/com/dclar/homecenter/MainActivity.java');

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

// Ingress is transport, not interpretation. Preserve exact authored text and FIFO order.
assert.match(queue, /new Item\([\s\S]*exactText,[\s\S]*conversationId/);
assert.match(queue, /items\.add\(item\);/);
assert.match(queue, /Item item = items\.remove\(0\);/);
assert.doesNotMatch(queue, /exactText\.trim\(\).*new Item/);

// Capacity and persistence both fail closed. "Queued" must mean durably queued.
assert.match(queue, /static final int MAX_ITEMS = 64;/);
assert.match(queue, /if \(items\.size\(\) >= MAX_ITEMS\) return null;/);
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
const restoreToHeadCount = (queue.match(/items\.add\(0, inflight\);/g) || []).length;
assert.ok(restoreToHeadCount >= 2, 'retry and process recovery must both restore in-flight input to the head');
assert.match(application, /ingressQueue\.retryInflight\(dispatch\.id\);/);
assert.match(application, /ingressQueue\.completeDispatch\(dispatch\.id\);/);

// If chat accepted dispatch but acknowledgement persistence fails, do not immediately resend.
assert.match(application, /Message submitted, but queue acknowledgement failed\. Recovery may replay it\./);
assert.match(application, /do not re-dispatch immediately/);
assert.match(application, /failed to restore rejected queued dispatch/);

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
