# HARROWAY CAMPAIGN — Home Center Text Inbox Orchestration

Status: CONTINUE_REQUIRED
Campaign: Harroway × Home Center — The Cord Must Come Out
Owner/operator: Adam as router/operator; Home Center is authoritative
Date: 2026-08-13

## Commission

Build a Home Center first-class text-message organ so Drew can talk to the Adam CLI and have Adam inspect and orchestrate the text-message inbox. The same Home Center Android package must be installable on June's phone without any terminal action. The Android experience is blind-first and must remain usable with TalkBack and zero visual information.

SMS-as-command-ingress is a possible secondary descendant. It is not the commissioned primary product and may not replace inbox orchestration.

## Non-negotiable boundaries

1. Home Center owns orchestration, identity, durable state, deployment, and acceptance evidence.
2. No Termux, rish, Shizuku, adb, copied shell command, or developer-mode action is required on June's phone.
3. Existing Google Messages notification-listener capture is the transport ancestor. Do not add READ_SMS, RECEIVE_SMS, or SEND_SMS merely to satisfy this feature.
4. Raw message content is owner-scoped. Household membership alone does not grant another household member a raw inbox.
5. Outbound messaging is a separate mutation authority. Read/search/triage/draft access never implies send authority.
6. A send, delete, block, archive, or other external mutation requires action-time explicit approval and a durable receipt.
7. Disconnect is functional and visible. Revoking notification access or disabling Text Inbox stops future capture without punishment or hidden fallback.
8. Missing permissions, identity, or evidence fail closed and report the exact unavailable state.
9. Repository presence is implementation evidence only. Deployment requires deployed Home Center revision evidence. Acceptance requires commissioned-device runtime evidence.

## Judgment stack

### Harroway

Crossings must produce useful consequence without containment, confiscation, false proof, or loss of the right to disconnect. The inbox is a crossing, not custody of the person.

### Punnett — required

Inheritance ruling:

- MENDEL: inherit the proven Google Messages notification transport, Home Center identity, source hashing, and durable evidence patterns.
- DARWIN: vary the interpretation layer into a general text inbox because calendar-only interpretation is too narrow for the actual pressure.
- CROSS: transport and interpretation must predict the same preserved source identity. No duplicate source-of-truth collections unless evidence proves separation is necessary.
- FALSIFIER: if the same notification can appear as two unrelated message identities, or if disabling the inbox leaves capture active, REVISE.
- UPDATE PATH: source schema and interpretation version are explicit so the model can evolve without rewriting evidence.

### Rene QA — required, exact jar

- Passing the intended path is insufficient; reachable failure states are product states.
- Requested, intended, implemented, tested, deployed, callable, delivered, and accepted remain distinct.
- Evidence must be current, attributable, and read back from the commissioned surface.
- Passing an adjacent SMS/calendar feature is not evidence that the generic text inbox exists.

### Venice — required

- CUT THE CAM must work: withdrawal cannot be delayed or bypassed.
- Consent cannot cross organs: enabling inbox read does not authorize send or unrelated capture.
- No unbounded credential authority.
- External messaging requires action-time authority.
- Failure closes toward autonomy instead of improvising.

## Architecture

### Android transport

The existing `SmsCalendarNotificationListener` is the current proven Google Messages notification transport. The target architecture extracts its preservation responsibility into a general text source envelope while retaining calendar interpretation as one descendant consumer.

Target envelope: `home-center.text-inbox.v1`

Required immutable source fields:

- messageId
- owner UID/email
- recipient device identity
- sender display name and normalized address when available
- body
- received timestamp
- source transport
- raw source reference/hash
- immutable source hash
- ingestion idempotency key

Derived interpretation fields may change without mutating the source envelope.

### Home Center operations

Required final read surface:

- `text_inbox.status`
- `text_inbox.inbox`
- `text_inbox.get`
- `text_inbox.search`
- `text_inbox.thread`

Useful orchestration descendants may include triage labels, reminders, calendar proposal creation, contact lookup, and reply drafting. They must preserve source identity and owner scope.

Outbound mutation is deliberately absent from the first read/orchestration slice. A future send surface must be separately named, explicitly approved, idempotent, receipted, and incapable of being inferred from read permission.

### Adam CLI

Adam receives a bounded typed `text_inbox` primitive backed by Home Center. The model can ask for inbox/search/thread evidence and then summarize, classify, route, or draft. The primitive never exposes Home Center bearer credentials to model output.

A compatibility adapter may temporarily read the already-deployed `sms_calendar.inbox` operation for Drew's existing captured messages. Such a result must be labeled compatibility evidence and must not be reported as completion of the generic `text_inbox.*` contract.

## Blind-first Android setup

The Home Center APK owns setup. No terminal.

A dedicated Text Inbox setup surface must:

- expose a stable launcher/deep-link target within the Home Center package;
- state whether Google sign-in, household enrollment, and notification access are ready;
- use native semantic controls with explicit content descriptions;
- use at least 48dp interactive targets, with primary controls larger;
- support TalkBack linear navigation with a sensible focus order;
- never require drag, swipe, long-press, timing, color interpretation, or unlabeled icon recognition;
- present state in text, accessibility announcements, and optional speech/haptics without making speech mandatory;
- provide one obvious action to open Android Notification Access settings;
- provide one obvious action to re-check state after returning;
- provide one obvious explanation of what is captured and what is not;
- explain how to disconnect and verify that capture stopped;
- avoid auto-advancing dialogs or moving focus while TalkBack is reading;
- preserve font scaling and high-contrast system settings;
- avoid horizontal scrolling and side-by-side critical controls;
- never expose raw message content on the setup screen.

## Accessibility acceptance matrix

Minimum acceptance is not a visual screenshot.

1. TalkBack can discover the Text Inbox launcher/surface by label.
2. Initial focus announces purpose and current state.
3. Every actionable control has role, name, state, and consequence.
4. The entire setup can be completed with TalkBack gestures alone.
5. The entire setup can be completed with keyboard/switch sequential focus and activation.
6. 200% font scale does not clip required instructions or controls.
7. High contrast / color correction does not remove meaning.
8. Permission denial returns to a stable, understandable state.
9. Revoked notification access is detected and announced on resume.
10. No state is communicated by color alone.
11. A blind user can determine whether capture is on without opening a log or terminal.
12. Disconnect instructions are reachable from the same surface.

## Privacy acceptance matrix

1. Drew's OAuth identity cannot retrieve June's raw body solely because both are household members.
2. June's OAuth identity cannot retrieve Drew's raw body solely because both are household members.
3. Owner can retrieve their own preserved body and source metadata through `text_inbox.*`.
4. Redacted household-level derivatives may exist only when the producing feature has its own explicit contract.
5. Notification capture remains user-controlled at Android OS level.
6. No SMS send permission exists in the read/orchestration slice.

## Deployment and acceptance gates

Implementation requires source, deterministic contracts, Android build, and cloud tests.

Deployment requires:

- exact source SHA deployed to Home Center MCP for `text_inbox.*`;
- exact Home Center Android APK revision built and delivered through the Home Center release/install lane;
- no terminal step on June's device.

Acceptance requires fresh runtime evidence:

- commissioned phone opens the Text Inbox setup surface;
- notification access state is read correctly;
- one test Google Messages notification is preserved with exact source identity;
- the matching owner can read it through Home Center `text_inbox.get`;
- a different household identity is denied raw-body access;
- Adam CLI reads the same message through its typed Home Center primitive;
- notification access is revoked and a subsequent test message is not ingested;
- Rene QA passes reachable failure states;
- Venice returns STOP_ALLOWED only after the above evidence exists.

Until those receipts exist, status remains CONTINUE_REQUIRED.
