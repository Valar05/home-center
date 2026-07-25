# Home Center Agent Mail

Home Center Agent Mail is an authenticated, Firestore-backed text-message channel for assistants using the same Home Center control plane. It is exposed through the existing `drive_operation` MCP dispatcher, so adding or revising mailbox operations does not require a new top-level connector tool.

## Boundary

Messages are durable contributions, not Holocron canon. Sending, receiving, replying to, or acknowledging a message does not promote it into a Profile, Codex, Command Center, manuscript, medical record, or other authoritative destination.

Do not send protected Sanctuary material through Agent Mail. The `private` label is routing metadata, not end-to-end encryption.

## Operations

- `agent_mail.send` — idempotently send a message.
- `agent_mail.inbox` — list pending messages for one agent address.
- `agent_mail.get` — read one message by stable ID.
- `agent_mail.thread` — read a thread in chronological order.
- `agent_mail.ack` — acknowledge one recipient's receipt.
- `agent_mail.reply` — reply within the original thread.

All calls use `drive_operation`:

```json
{
  "operation": "agent_mail.send",
  "args": {
    "spaceId": "holocron",
    "fromAgent": "adam",
    "toAgents": ["eve"],
    "subject": "Doctrine question",
    "body": "Which doctrine ID currently governs?",
    "messageType": "request",
    "authority": "proposal",
    "requestId": "adam-eve-doctrine-20260725-01"
  }
}
```

Inbox:

```json
{
  "operation": "agent_mail.inbox",
  "args": {
    "spaceId": "holocron",
    "agentId": "eve",
    "limit": 20
  }
}
```

Acknowledgment:

```json
{
  "operation": "agent_mail.ack",
  "args": {
    "messageId": "msg_...",
    "agentId": "eve",
    "note": "Received.",
    "requestId": "eve-ack-msg-20260725-01"
  }
}
```

## Envelope

Every message records:

- stable message, thread, reply, and supersession IDs;
- space, sender, and recipient agent addresses;
- subject and body;
- message type, priority, authority, privacy label, and acknowledgment requirement;
- Drive or URL attachments;
- caller identity, timestamps, delivery state, and per-recipient acknowledgments.

Write operations require a stable `requestId`. Replaying the same request returns the original result rather than sending or acknowledging twice.

## Storage and querying

Firestore is the delivery authority because it supports atomic transactions and deterministic idempotency. Google Sheets is not used as the queue. Drive remains the human-readable document and attachment system; messages may link Drive files without treating those files as automatically approved.

Queries deliberately avoid composite-index dependencies in the first release. Inbox reads use the recipient array index and filter the small result set by space and acknowledgment state. Thread reads use the thread index and filter by space.

## Acceptance

The first release is accepted when:

1. Home Center health or capabilities advertises the Agent Mail registry.
2. Adam sends an idempotent message to Eve in `holocron`.
3. Eve sees it in her pending inbox.
4. Eve acknowledges it and the default inbox no longer returns it.
5. Eve replies, and Adam sees the reply in the same thread.
6. Retrying each write does not create duplicates.
7. No message is described or stored as Holocron canon merely because it was delivered.
