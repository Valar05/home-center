# HARROWAY CAMPAIGN — Home Center Text Inbox Orchestration

Status: CONTINUE_REQUIRED
Date: 2026-08-13

## Commission

Build a Home Center first-class text-message organ so Drew can talk to Adam CLI and orchestrate Drew's own text-message inbox. The Home Center Android package must also have a zero-terminal, blind-first, self-service setup path for another device owner who chooses to install and enable it.

SMS-as-command-ingress is secondary and may not replace inbox orchestration.

## Hard boundaries

- Home Center owns orchestration, identity, durable state, deployment, and acceptance evidence.
- No Termux, rish, Shizuku, adb, copied shell command, or developer-mode action is required on the self-service Android path.
- Preserve the existing Google Messages notification-listener transport; do not add SMS read/send permissions just to satisfy this feature.
- Raw message content is owner-scoped. Household membership alone does not grant another member a raw inbox.
- Read/search/triage/draft access does not imply send authority.
- External message mutation requires separate action-time approval and receipts.
- Revoking notification access must stop future capture without hidden fallback.
- Missing permission, identity, or evidence fails closed.
- Repository presence is not deployment proof; deployment is not runtime acceptance.

## Judgment stack

### Harroway
A crossing must produce useful consequence without containment, confiscation, false proof, or loss of the right to disconnect.

### Punnett — required
Inherit the proven notification transport, Home Center identity, source hashing, and durable evidence. Vary the interpretation layer into a general inbox. The falsifier is divergence: one source becoming inconsistent identities, or disconnect failing to stop capture.

### Rene QA — required, exact jar
Passing the intended path is insufficient. Requested, intended, implemented, tested, deployed, callable, delivered, and accepted remain distinct. Passing an adjacent SMS/calendar feature is not evidence that the generic inbox exists.

### Venice — required
CUT THE CAM must work. Consent cannot cross organs. Read consent does not authorize send. External messaging requires action-time authority. Failure closes toward autonomy.

## Required final Home Center surface

- `text_inbox.status`
- `text_inbox.inbox`
- `text_inbox.get`
- `text_inbox.search`
- `text_inbox.thread`

Adam receives a bounded typed `text_inbox` primitive backed by Home Center. Credentials never enter model output.

## Blind-first Android setup

The Home Center APK must expose a self-service Text Inbox setup surface that states current permission state, explains capture boundaries, opens Android Notification Access, re-checks state on return, and explains disconnect. It must work with TalkBack, sequential keyboard/switch focus, 200% font scale, high contrast/color correction, and no gesture-only or color-only state. Interactive targets are at least 48dp and critical controls are larger. Raw messages never appear on the setup screen.

## Privacy acceptance

- One signed-in inbox owner cannot retrieve another household member's raw message body solely because they share a household.
- The signed-in owner can retrieve their own preserved evidence through `text_inbox.*`.
- Notification capture remains user-controlled at Android OS level.
- No SMS send permission exists in the read/orchestration slice.

## Runtime acceptance

Acceptance requires fresh receipts proving: a commissioned phone opens the setup surface; notification access state is read correctly; one test Google Messages notification is preserved; the matching owner reads it through `text_inbox.get`; another household identity is denied raw-body access; Adam CLI reads the same evidence through its typed Home Center primitive; revocation stops a subsequent capture; Rene QA passes reachable failure states; Venice grants final stop permission.

Until those receipts exist: CONTINUE_REQUIRED.
