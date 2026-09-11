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

// Capacity must fail closed rather than silently dropping an older or newer thought.
assert.match(queue, /static final int MAX_ITEMS = 64;/);
assert.match(queue, /if \(items\.size\(\) >= MAX_ITEMS\) return null;/);
assert.match(application, /Queue is full\. Nothing was dropped\./);

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

// Semantic invariant learned from the failure: queue != interrupt.
assert.doesNotMatch(application, /busy_turn_interrupt/);
assert.match(application, /"operator_ingress_queue"/);
assert.match(application, /Queue without interrupting/);
assert.match(application, /Current work continues/);

// Accessibility is part of the feature, not garnish.
assert.match(application, /setAccessibilityLiveRegion\(View\.ACCESSIBILITY_LIVE_REGION_POLITE\)/);
assert.match(application, /setContentDescription\("Queue another Home Center message without interrupting current work"\)/);
assert.match(application, /queueButton\.setMinimumHeight\(dp\(activity, 48\)\)/);
assert.match(application, /input\.setMinimumHeight\(dp\(activity, 48\)\)/);

console.log('operator ingress queue contract: OK');
