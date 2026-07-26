# Household Evidence Spine

Status: inert architecture and fixture contract
Version: household-evidence-envelope/v1

## Existing Owner

Home Center already owns the evidence-backed life operations layer. This spine belongs under that owner, not a parallel intake system.

Existing systems it reuses conceptually:

- Android app: native Home Center shell under app/src/main/java/com/dclar/homecenter.
- Firebase/Firestore household state: households, members, groups, lists, tasks, Command Center collections, action audit, and Drive Bridge audit patterns.
- Provider clients: GoogleCalendarClient, GoogleGmailClient, GoogleDriveClient, GoogleContactsClient, GoogleSheetsClient.
- Accessibility surfaces: NarrationForegroundService, speech/readback behavior, LocalLog, and WalmartCartAccessibilityService.
- MCP and Drive operations: Home Center MCP, drive_operation, command_center_operation, audited request ids, and explicit write gates.
- Queue precedent: Walmart cart review queue keeps candidate mappings separate from checkout or final actions.

The envelope is a shared inert evidence packet that future SMS, Gmail, Calendar, Google Home, Home Assistant, manual notes, and spoken observations can all emit into the same queue.

## Envelope Contract

A HouseholdEvidenceEnvelope preserves:

- exact source text or observation;
- source type and stable source reference;
- captured timestamp;
- inferred owner;
- extracted facts;
- confidence per inference;
- possible duplicate references;
- verification state;
- final disposition;
- consent and scope metadata;
- feature flags proving live ingestion, calendar mutation, and automatic playback are off.

Intake is not canon. A fact extracted from a message or observation remains evidence until a separate verification path promotes it. Low-confidence or conflicting facts stay unresolved.

## Calendar Briefing Compiler

The current compiler is fixture-driven and inert. It consumes envelopes and emits:

- screen-reader-friendly plain text;
- structured JSON;
- unresolved uncertainty;
- conflicts;
- proof that no live ingestion, calendar mutation, or automatic playback occurred.

It never creates, updates, deletes, or reads a live calendar event. It does not call Gmail, Calendar, Home Assistant, SMS, Android device APIs, Drive, MCP, or Firebase.

## Feature Flags

All activation flags default to false:

- liveSmsIngestion
- liveDeviceIngestion
- liveGmailIngestion
- liveCalendarRead
- liveCalendarMutation
- homeAssistantIngestion
- automaticPlayback

A future live lane must keep June veto and an obvious off switch before any source is enabled.

## Future Shared Source Flow

1. A source adapter captures exact evidence and a stable source reference.
2. The adapter writes a HouseholdEvidenceEnvelope into the existing Home Center state/audit lane.
3. A verifier reviews duplicates, conflicts, owner inference, and consent scope.
4. A briefing compiler surfaces candidate facts and unresolved issues in accessible text.
5. Only after explicit human confirmation may a separate provider tool perform a write.

Candidate source adapters:

- SMS: exact message text, sender reference, device/source account, consent scope.
- Gmail: message id, thread id, exact quoted fragment, sender, recipient scope.
- Calendar: event id and provider snapshot for read-only reconciliation.
- Google Home or Home Assistant: device entity id, observation text, room/scope, timestamp.
- Spoken output: pull-based briefing from verified envelopes; no automatic playback unless explicitly enabled later.

## Decision Ledger Before Activation

June or Eve must decide:

1. Who may create HouseholdEvidenceEnvelope records for House Oakheart.
2. Which source types June permits: SMS, Gmail, Calendar read, Google Home or Home Assistant, manual notes, or spoken observations.
3. Which household members or groups each source may mention.
4. Minimum confidence and verification requirements before a fact can leave intake-only status.
5. How duplicate and conflict review should be presented to June.
6. Whether calendar writes are ever allowed, and what explicit confirmation gesture is required.
7. Whether spoken output is pull-only or may ever play automatically.
8. Where the obvious off switch lives in the Android app and MCP feature flags.
9. Retention limits for exact source evidence and redaction rules for private messages.

## Non-Goals In This Slice

- No live SMS, Gmail, Calendar, Google Home, Home Assistant, or device ingestion.
- No provider writes.
- No calendar mutation.
- No automatic playback.
- No deployment.
- No new MCP tool.
- No Android UI activation.
