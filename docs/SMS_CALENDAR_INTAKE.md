# SMS-to-Google Calendar Capability

Status: capability truth and implementation contract

Baseline: `main` at `e3a03add1963e016bb23dc4d255c0729d5e8f1c8`

Baseline captured: 2026-07-26 America/Chicago

## Product Boundary

The supported product is narrow:

> A supported SMS message is received, preserved, classified as a possible
> calendar event, converted into a structured proposal, and explicitly approved
> or rejected before anything is written to Google Calendar.

This capability is not a generic assistant, autonomous scheduler, outbound SMS
system, notification framework, or agent-to-agent messaging system.

## Pre-Implementation Capability Truth

Status terms in this document:

- **Verified**: implementation is registered and its relevant contract test or
  live capability probe passed during this baseline.
- **Present but unverified**: source exists, but the real boundary was not
  exercised.
- **Partial**: source exists but does not satisfy the product contract.
- **Absent**: no implementation was found.
- **Out of scope**: intentionally excluded from this slice.

| Capability | Source and public contract | Storage | Authentication boundary | Tests | Deployment binding | Baseline status |
| --- | --- | --- | --- | --- | --- | --- |
| Android inbound transport | `SmsCalendarNotificationListener`; Google Messages notification-listener service declared in `AndroidManifest.xml` | `households/{bucketId}/smsCalendarIntake/{messageId}` | Android notification-access grant, Firebase signed-in user, household bucket membership in Firestore rules | `SmsReminderClassifierHarness` exercises local candidate filtering; no installed-device ingestion test in this baseline | Home Center Android APK, repo version `0.2.58` / code `62`; installed revision not established | **Partial**: only high-confidence candidates are persisted, so preservation happens after interpretation; records use merge writes |
| SMS normalization and preservation | `SmsCalendarNotificationListener.persistCandidate` | Same intake document; visible notification body, sender, timestamp, source hash | Creating Firebase UID must be a household member | Static regression checks only | Android APK | **Partial**: no normalized envelope contract, recipient/device identity, stable transport message ID, exact-input conflict behavior, or immutable create/attach decision |
| SMS classification | `SmsReminderClassifier.classify` | Embedded `classification` map on intake document | Runs locally inside notification listener | Java harness passed | Android APK | **Partial**: bounded candidate score and reasons exist, but no structured event fields, missing fields, ambiguity flags, timezone, inference provenance, or proposal generation |
| SMS sending | No `SEND_SMS`, `SmsManager`, or outbound SMS dispatcher found | None | None | None | None | **Absent** and **out of scope** |
| SMS review operations | `functions/sms_calendar_intake.js` via `drive_operation`: `inbox`, `get`, `reconcile`, `propose`, `dismiss`, `create_event` | Intake document plus top-level `smsCalendarAudit` | Home Center MCP OAuth identity and membership email lookup under `households/*/members` | `tools/sms_calendar_contract_test.mjs` passed; it covers registry and helper validation, not the Firestore/provider path | `homeCenterMcp`; live capability registry exposed all six operations | **Partial**: proposal is supplied manually; no durable approve/reject record, proposal revision binding, or bounded redacted status |
| Google Calendar Android tools | `ToolRegistry` and `GoogleCalendarClient`: search, read, create, update, RSVP, delete | Provider-owned Calendar | Android Google sign-in and `calendar.events` scope; app confirmation gate for writes | Source-contract regression assertions passed; no live provider write in this baseline | Android APK | **Present but unverified** for live Calendar mutation |
| Google Calendar SMS mutation | `functions/sms_calendar_intake.js` calls `calendar.events.list` and `calendar.events.insert` for `primary` | Google Calendar plus intake `createdEvent` summary | Home Center MCP OAuth Google credential, `calendar.events` scope, household membership | Narrow helper contract passed; no provider-double execution test before implementation | `homeCenterMcp` revision `homecentermcp-00124-kal`, ACTIVE, updated `2026-07-27T00:27:27Z` | **Partial**: source-marker duplicate search exists, but approval is a request boolean/phrase, idempotency is request-ID-only, and uncertain provider outcomes are not quarantined |
| Google Calendar read/reconciliation | SMS `reconcile` searches Gmail metadata and Calendar; general Android Calendar search/read also exists | Provider-owned Gmail and Calendar | OAuth plus `gmail.readonly` and `calendar.events` scopes | Registry scope assertion passed | Same MCP revision and Android APK | **Present but unverified** against live Gmail/Calendar in this baseline |
| Audit and idempotency | `smsCalendarAudit` and `auditOnce`; Calendar private extended property `homeCenterSmsIntakeId` | Top-level `smsCalendarAudit`, intake document, Google Calendar event private properties | Server-only audit writes; MCP OAuth caller | Audit document ID namespacing helper test passed | `homeCenterMcp` | **Partial**: same request ID with changed input is not rejected; audit is written only after the side effect; concurrent and ambiguous writes are not durably represented |
| Approval/review | `create_event` requires `approved: true` and `confirmationText: "CREATE EVENT"` | No durable approval record | MCP OAuth caller plus household membership | Registry flag assertion only | `homeCenterMcp` | **Partial**: approval is not durable and does not bind source hash, classifier output, proposal revision, actor, or timestamp |
| Reliable Worker Execution Contract | `docs/RELIABLE_WORKER_EXECUTION_CONTRACT.md` and `ops/worker_execution_contract.v1.json` | Existing worker stores, not SMS intake | Worker-specific | `worker_execution_contract_test.mjs` is part of regression | Existing worker surfaces | **Verified as a repository contract**, but not used by the SMS path; deterministic parsing and one bounded provider call do not justify a new job |
| Household evidence compiler | `functions/household_evidence.js` and `docs/HOUSEHOLD_EVIDENCE_SPINE.md` | Evidence envelopes and generated briefing artifacts | Fixture/compiler boundary | `household_evidence_contract_test.mjs` | No SMS ingestion binding | **Separate, non-mutating evidence path**; it must not be treated as SMS-to-Calendar implementation |

## Applications and Services

1. **Home Center Android app**
   owns Google Messages notification capture, Firebase identity, household
   selection, and general Android Google Calendar tools.
2. **Cloud Firestore**
   stores household membership and SMS intake records. The rules permit members
   to create and read intake records and preserve selected immutable fields on
   update. No SMS-specific composite index exists or is currently required.
3. **Home Center MCP / Firebase Function**
   owns the stable `drive_operation` registry and executes SMS review operations
   under Home Center OAuth. Repository deployment targets project
   `home-center-dclar`, region `us-central1`, Node.js 22.
4. **Google APIs**
   own Gmail reconciliation and Google Calendar read/write state.

The connected live Home Center capability probe reported bridge version `0.2.0`,
SMS registry `2026-07-25.notification-sms-calendar-v1`, and all six baseline SMS
operations. The live function configuration reported revision
`homecentermcp-00124-kal` as ACTIVE. These probes establish registration and
deployment, not successful SMS ingestion or Calendar mutation.

## Baseline State Machine

The pre-implementation states are:

`pending -> proposed | dismissed -> duplicate | created`

This is incomplete. It does not represent preservation before interpretation,
non-calendar classification, durable approval, approval invalidation, failed
write, or uncertain provider outcome.

## Baseline Security and Privacy

- Home Center does not request `READ_SMS`, `RECEIVE_SMS`, or `SEND_SMS`.
- Notification access is user-controlled and capture is limited to Google
  Messages notification content.
- Rejection logs omit message bodies.
- Firestore prevents deletion and protects selected source fields on update.
- MCP operations require a connected Google identity that maps to a household
  member.
- Calendar mutation uses the connected user's Google credential and the
  `calendar.events` scope.

Baseline gaps:

- status returns full message bodies and internal bucket IDs;
- every household member can read raw intake records directly;
- operational audit records do not bind exact normalized input;
- no retention duration is defined;
- no durable approval record exists;
- no provider-ambiguity quarantine exists.

## Dead, Duplicated, and Incomplete Paths

- No outbound SMS implementation was found.
- `SmsReminderClassifier` and `sms_calendar.propose` split interpretation across
  Android candidate filtering and manually supplied cloud proposal fields; no
  end-to-end classifier contract connects them.
- General Android `calendar.create_event` is a separate user-command tool. It
  must not be used to bypass SMS proposal approval.
- The household evidence compiler is read-only briefing infrastructure, not an
  ingestion or Calendar mutation path.
- The existing SMS documentation described intended device acceptance, but
  explicitly marked the capability as an implementation candidate. No committed
  real-device evidence proves that notification access captured a message.

## Baseline Verification

Passed from the clean baseline:

```sh
node tools/sms_calendar_contract_test.mjs
sh tools/run_regression_tests.sh
```

The first regression attempt stopped because the clean worktree had no
Functions dependencies. After `npm --prefix functions ci`, the suite passed.
Node reported an engine warning because the local runtime is Node 26 while the
Functions package declares Node 22; the deployed function uses Node 22.

Not verified in the baseline:

- installed Android notification capture;
- live SMS delivery;
- live Firestore source preservation;
- live Gmail reconciliation;
- live Google Calendar mutation;
- Calendar idempotent replay against the provider.

## Required Implementation Contract

The replacement state flow is:

`received -> preserved -> classified -> proposal_ready -> approved | rejected -> calendar_written | failed`

`calendar_write_ambiguous` is a quarantined blocking state that requires
explicit provider reconciliation.

The implementation must:

- preserve a normalized immutable message before classification;
- attach exact duplicate ingestion and reject changed immutable content under
  the same stable message ID;
- produce a bounded deterministic classification and proposal with explicit
  versus inferred field provenance;
- persist approval or rejection against exact source, classification, proposal
  hash, and proposal revision;
- invalidate approval when a proposal changes;
- permit Calendar write only from the exact approved revision;
- use exact-input idempotency and a provider-stable event key;
- quarantine uncertain provider outcomes and reconcile by provider key without
  automatically repeating the insert;
- expose bounded redacted status without raw message or provider payloads;
- keep raw SMS access narrower than review/status access.

## Intentionally Out of Scope

- outbound confirmation SMS;
- recurring events;
- contact-aware sender policy;
- autonomous scheduling;
- agent-to-agent messaging;
- a new scheduler, job system, audit store, or notification framework;
- a proposal review UI.

## Implemented Vertical Slice

Implementation commits:

- `e1dc838`: pre-implementation capability truth;
- `b841556`: durable SMS Calendar proposal implementation.

The implemented path is:

`received -> classified -> proposal_ready -> approved | rejected -> calendar_written | failed`

`preserved` is an immutable-record guarantee established during the `received`
transition rather than a separately mutable status. An uncertain provider
outcome enters `calendar_write_ambiguous` and can only leave through explicit
reconciliation.

### Ownership and Trust Boundaries

- `SmsCalendarNotificationListener` owns Google Messages notification capture,
  normalization, and preservation before interpretation.
- `SmsReminderClassifier` owns deterministic, bounded interpretation and never
  calls Google Calendar.
- Household Firestore owns the immutable source record, derived classification,
  proposal, approval, write state, and existing audit collection.
- `sms_calendar_intake.js`, reached through the stable `drive_operation`
  surface, owns authorized review and Calendar mutation.
- Home Center MCP OAuth plus household membership gates status, approval,
  rejection, proposal edits, Calendar writes, and reconciliation.
- The connected user's Google OAuth credential performs Calendar writes. No
  service account or autonomous scheduler was added.

Parsing and the single bounded provider operation remain synchronous. No new
worker, queue, lease, scheduler, audit store, or notification system was added.

### Message and Proposal Contracts

The normalized source envelope is `home-center.sms-calendar-intake.v2` and
contains a stable message ID, sender, normalized sender address, recipient device
identifier where available, body, received timestamp, source transport, raw
source reference/hash, immutable source hash, and ingestion idempotency key.

The structured classifier output contains classification, confidence, proposed
title/start/end/duration/timezone/location/notes, bounded source excerpt,
missing fields, ambiguity flags, classifier version and hash, inferred fields,
and field-level provenance. Materially missing dates or times remain blocked.
The documented default duration is 60 minutes and is always marked inferred.

A proposal contains source and classification hashes, revision, proposal hash,
normalized event fields, provenance, missing fields, ambiguity flags, and an
approval-eligibility flag. Editing creates a new revision and clears any prior
approval and write state.

### Idempotency and Approval

- Exact replay is determined by stable message ID plus immutable content hash and
  attaches to the existing record.
- Reuse of a message ID with changed immutable content raises
  `SMS_INTAKE_IDEMPOTENCY_CONFLICT`.
- Review operations bind request IDs to exact normalized input hashes. Reusing a
  request ID with different input raises `REQUEST_ID_CONFLICT`.
- Approval binds source message ID/hash, classification hash, proposal revision
  and hash, actor identity, auth kind, timestamp, and optional reason.
- Calendar execution revalidates that exact binding before any provider call.
- Google Calendar receives a deterministic event ID and private source/proposal
  properties. Replay returns the existing event instead of inserting another.

If an insert times out or returns an uncertain network/provider result after it
may have succeeded, the write enters `calendar_write_ambiguous`. Automatic
insert retry is disabled. `reconcile_write` performs a read-only lookup by the
deterministic provider ID; it never inserts.

### Public Operations

The SMS Calendar registry version is
`2026-07-26.sms-calendar-proposal-v2` and exposes:

- `sms_calendar.inbox`
- `sms_calendar.get`
- `sms_calendar.reconcile`
- `sms_calendar.approve`
- `sms_calendar.reject`
- `sms_calendar.update_proposal`
- `sms_calendar.create_event`
- `sms_calendar.reconcile_write`

`sms_calendar.propose` and `sms_calendar.dismiss` remain compatibility aliases
for update and reject. Request-time `approved: true` is no longer an approval
mechanism.

Status responses are bounded. They expose stable record state, redacted sender,
source hash/reference, classification/proposal summaries, approval/write state,
blocking error or ambiguity, and timestamps. They do not expose raw SMS bodies,
internal household bucket IDs, OAuth credentials, or unbounded provider/audit
payloads.

### Storage and Indexes

The implementation reuses:

- `households/{bucketId}/smsCalendarIntake/{messageId}`;
- top-level `smsCalendarAudit`;
- Google Calendar provider events.

No collection or composite-index change is required. Firestore rules now permit
only the creating household member to read raw intake records and permit Android
updates only for bounded derived fields while preserving immutable source data.
Server-side Admin SDK operations continue through the existing MCP boundary.

No automatic deletion job exists. Raw source retention therefore follows the
household Firestore record lifecycle until an explicit retention policy is
implemented. This limitation is intentional and documented rather than hidden.

### Configuration

Required existing configuration:

- Android Firebase sign-in and selected household bucket;
- user-granted notification-listener access for Home Center;
- Home Center MCP Google OAuth with `calendar.events` and existing identity
  scopes;
- household membership matching the connected Google email;
- the existing production secrets configured by
  `tools/deploy_functions_termux.sh`.

No SMS read/send permission, Calendar service account, model API key, or new
queue configuration is required.

### Verification

Passed against the implementation:

`sh tools/check_no_secrets.sh`

`python3 tools/home_center_regression_tests.py`

`NODE_PATH=/storage/emulated/0/Documents/GodotProjects/home-center/functions/node_modules node tools/home_center_authorization_contract_test.mjs`

`node tools/sms_calendar_contract_test.mjs`

`javac ... SmsCalendarIngestionContract.java SmsReminderClassifier.java SmsReminderClassifierHarness.java`

`java -cp <classes> com.dclar.homecenter.SmsReminderClassifierHarness`

`./gradlew assembleDebug`

The provider-double contract reports 16 passing cases and covers exact duplicate
and conflict ingestion, non-calendar filtering, structured appointment parsing,
relative time, ambiguity, inferred duration, approval and revision binding,
idempotent Calendar write, ambiguity quarantine and reconciliation,
authorization, and bounded redacted status. Firestore rules compiled under the
local Firestore emulator.

The diagnostic message
`Dentist appointment Tuesday at 2:30 PM, 45 minutes, at River Dental.`
produced a proposal with an explicit Tuesday start, explicit 45-minute duration,
and normalized `River Dental` location in the Java classifier contract. The
provider double then exercised approval, one provider insert, replay, and bounded
final status without creating a real Calendar event.

Android `0.2.59` / code `63` built successfully, APK v2 signature
verification passed, the final APK was exported to
`/storage/emulated/0/Download/HomeCenter-debug.apk`, and that exact final build
was installed through Shizuku. Notification-listener access was verified as
disabled and was not granted by automation.

The committed MCP implementation was deployed through the repository-owned
deployment script. Google Cloud reports `homeCenterMcp` ACTIVE on revision
`homecentermcp-00125-jip` with 100% traffic and update time
`2026-07-27T02:30:31.650543824Z`. A subsequent connected Home Center capability
probe reported `2026-07-26.sms-calendar-proposal-v2`, 10 operations, and the
expected write-operation classification. This proves cloud publication and
registry routing; it does not prove a real SMS capture or Calendar insert.

### Deployment

Deploy the existing MCP owner from a reviewed commit:

`sh tools/deploy_functions_termux.sh home-center-dclar homeCenterMcp`

Deploy the reviewed Firestore rules with an authenticated Firebase CLI:

`firebase deploy --only firestore:rules --project home-center-dclar`

Build/install Android with the repository Gradle wrapper and the existing local
Firebase configuration. Enable Home Center notification access manually only on
the intended device and account.

### Rollback

1. Deploy `homeCenterMcp` from the prior known-good commit with the same
   repository deploy script.
2. Deploy the prior `firebase/firestore.rules` with Firebase CLI.
3. Reinstall the prior Android APK/version if notification ingestion was enabled.
4. Do not delete provider events automatically. Reconcile any test event by its
   stored provider event ID and private source/proposal properties before manual
   cleanup.

No live Google Calendar event was created during this implementation pass, so
there is no provider-side rollback item from the automated verification.

### Known Limitations and Final Verification State

- Real SMS capture is not verified because Home Center notification-listener
  access is currently disabled. No device evidence is fabricated.
- The deterministic parser supports the documented narrow appointment grammar;
  unsupported natural language remains non-calendar or blocked for review.
- Live Google Calendar mutation was not authorized for this pass. The complete
  side-effect contract is verified through a provider double.
- Firebase CLI is not authenticated in this environment. The updated Firestore
  rules compile locally but are not deployed. Until they are deployed, the new
  Android v2 intake create is expected to be rejected by production rules.
- The new MCP revision must not be described as end-to-end production-ready
  until the Firestore rules are deployed and a user manually enables notification
  access for a harmless real-message acceptance test.
- There is no proposal review UI; authorized review is through the existing Home
  Center MCP tool surface.
- Raw source retention has no automatic expiry.

The exact next increment is a narrow proposal review UI over the existing
bounded status, approve, reject, and update operations. It must not add another
proposal store or Calendar mutation path.
