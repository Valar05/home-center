# SMS-to-Google Calendar Intake

Status: implementation candidate; June/Eve activation requires explicit setup and acceptance.

Source requirement: `Holocron Intake — Adam and Drew Drop Box`, July 25, 2026.

## Outcome

Home Center can capture high-confidence appointment reminder notifications from Google Messages, preserve their visible sender, timestamp, exact displayed wording, and source hash in a household Firestore intake queue, then expose the queue to Eve through the stable `drive_operation` MCP dispatcher.

Eve may reconcile a candidate against Gmail and Google Calendar, save a structured proposal, dismiss it, or create a Calendar event after explicit confirmation. Delivery, capture, acknowledgment, and proposal state do not promote anything into Holocron canon.

## Privacy Boundary

Home Center does not request `READ_SMS` or `RECEIVE_SMS`, does not become the default SMS app, and does not scan message history.

Android notification access is user-controlled. The listener:

- accepts notifications only from `com.google.android.apps.messaging`;
- ignores group-summary, ongoing, and silent notifications;
- filters locally before any Firestore write;
- rejects ordinary conversation, security codes, and marketing;
- persists only high-confidence reminder candidates;
- logs rejection reasons without logging message bodies;
- stores a telephone sender URI when Google Messages provides one, otherwise the exact displayed sender;
- never deletes intake records.

Because notification text is the capture source, the exact wording means the exact text Google Messages exposed in the notification. A hidden or truncated notification cannot be reconstructed by Home Center.

## Intake State

Firestore path:

`households/{bucketId}/smsCalendarIntake/{messageId}`

States:

- `pending`: captured locally and awaiting review;
- `proposed`: Eve saved a structured event proposal;
- `dismissed`: a reviewer rejected the candidate without deleting it;
- `duplicate`: Calendar reconciliation found a likely existing event;
- `created`: explicit confirmation produced a Google Calendar event.

The Calendar event stores a private extended property containing the Home Center intake ID. Creation checks that property and performs a title/time-window search before inserting, so retries and differently named upstream reminders do not silently duplicate events.

## MCP Operations

All operations use the stable `drive_operation` tool:

- `sms_calendar.inbox`
- `sms_calendar.get`
- `sms_calendar.reconcile`
- `sms_calendar.propose`
- `sms_calendar.dismiss`
- `sms_calendar.create_event`

`reconcile` requires Gmail read-only and Calendar event scopes. `create_event` requires:

- a saved proposal;
- a stable `requestId`;
- `approved: true`;
- `confirmationText: "CREATE EVENT"`;
- no exact or likely duplicate event.

## One-Time Device Setup

1. Install the Home Center `0.2.57` debug APK on June's phone.
2. Sign in to Home Center and join the intended household bucket.
3. Open Android **Notification access** settings.
4. Enable Home Center only after June approves the intake test.
5. Keep Google Messages notification previews enabled; hidden previews cannot be captured.
6. Reconnect Home Center MCP once so its OAuth grant includes Gmail read-only and Google Calendar event access.

No candidate is captured before notification access is enabled.

## Safe Acceptance

1. Send a harmless synthetic reminder from a clearly labeled test sender. Do not use a real medical message.
2. Verify exactly one `pending` intake record appears.
3. Confirm ordinary conversation, a verification code, and a marketing message create no records.
4. Ask Eve to read the candidate and reconcile it against Gmail and Calendar.
5. Verify a proposal does not create an event.
6. Have June explicitly approve event creation.
7. Verify one Calendar event exists with the correct title/time and Home Center source marker.
8. Replay the same create request and verify no second event appears.

## Evidence Boundary

Automated classifier and operation-contract tests prove code behavior only. Android capture is not accepted until a real installed APK receives the synthetic notification. Calendar creation is not accepted until June performs the confirmation step and provider readback shows exactly one event.
