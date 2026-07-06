# Home Center Data Model

Firestore root:

```text
households/{bucketId}
households/{bucketId}/members/{uid}
households/{bucketId}/groups/{groupId}
households/{bucketId}/groups/{groupId}/members/{uid}
households/{bucketId}/lists/{listId}
households/{bucketId}/lists/{listId}/tasks/{taskId}
usageEvents/{eventId}
usageDaily/{yyyyMMdd}_{uid}_{provider}
usagePricing/{provider_sku}
```

## Household

```json
{
  "name": "family bucket code",
  "createdBy": "firebase uid",
  "createdAt": "server timestamp",
  "updatedAt": "server timestamp"
}
```

## Member

```json
{
  "email": "person@example.com",
  "displayName": "Person",
  "role": "member",
  "joinedAt": "server timestamp"
}
```

## Group

Groups are Home Center sharing groups inside a household bucket. They are not Google Family Link groups.

```json
{
  "name": "kids",
  "createdBy": "firebase uid",
  "createdAt": "server timestamp",
  "updatedAt": "server timestamp"
}
```

Each group has `members/{uid}` documents. Group list visibility is allowed only for users with a matching group member document.

## List

```json
{
  "name": "shopping",
  "visibility": "household",
  "ownerUid": "firebase uid",
  "groupId": "",
  "groupName": "",
  "itemPreferences": {
    "eggs": {
      "canonicalName": "eggs",
      "preferredLabel": "18 count",
      "updatedBy": "firebase uid"
    }
  },
  "storeTargets": {
    "eggs": {
      "store": "walmart",
      "sku": "12345",
      "productName": "Great Value Large White Eggs, 18 Count",
      "productUrl": "https://www.walmart.com/ip/12345",
      "quantity": 1,
      "unitPreference": "",
      "source": "buy_again",
      "confidence": "confirmed",
      "canonicalName": "eggs",
      "confirmedAt": "server timestamp",
      "updatedBy": "firebase uid"
    }
  },
  "createdAt": "server timestamp",
  "updatedAt": "server timestamp"
}
```

## Task

```json
{
  "name": "eggs",
  "description": "",
  "json": {},
  "jsonText": "",
  "dueAt": null,
  "status": "active",
  "createdAt": "server timestamp",
  "updatedAt": "server timestamp",
  "createdBy": "firebase uid",
  "completedAt": null,
  "completedBy": null,
  "removedAt": null,
  "removedBy": null
}
```

Lists and bucket ids are normalized to lowercase. Leading articles and trailing `list`/`lists` are stripped, so `the shopping list`, `shopping list`, and `shopping` all map to `shopping`. `grocery` and `groceries` also map to `shopping`.

List-level grocery preferences live on the list document as `itemPreferences`. Store-specific Walmart SKU mappings live separately as `storeTargets` so a human-friendly grocery label and a purchase target can evolve independently. Walmart cart-agent review artifacts should feed accepted mappings back into `storeTargets`; unresolved review queues stay local under ignored `agent-tools/walmart-cart-agent/data/` files.

## Fuzzy removal

Voice removal commands match active tasks by normalized item name. Matching handles simple singular/plural differences, substring matches, token overlap, and edit distance. If two active tasks are similarly close matches, the app asks for a more specific command instead of removing either one.

## Local diagnostics

Diagnostics are local files only and are not part of the Firestore data model. On Android 10+ daily log files are written through the Downloads provider under `/storage/emulated/0/Download/HomeCenter/logs/YYYY-MM-DD.txt`.

## Usage telemetry

Usage telemetry is server-owned metadata for the owner/admin spend dashboard. It must not store prompts, document contents, email bodies, OAuth tokens, API keys, Authorization headers, or raw tool arguments.

`usageEvents/{eventId}` stores one safe metadata event per OpenAI Responses call or local Android tool execution:

```json
{
  "eventType": "openai_response",
  "provider": "openai",
  "source": "agentToolTurn",
  "sku": "gpt-5.5",
  "uid": "firebase uid",
  "email": "person@example.com",
  "day": "20260706",
  "month": "202607",
  "inputTokens": 1234,
  "outputTokens": 250,
  "totalTokens": 1484,
  "latencyMs": 1200,
  "status": "ok",
  "costUsd": 0.0,
  "unpriced": true
}
```

Tool events use `eventType: "tool_call"` and include `toolName`, `write`, `destructive`, `bucketId`, `conversationId`, `resultCount`, and `resultBytes`. Content and raw arguments are intentionally omitted.

`usageDaily/{yyyyMMdd}_{uid}_{provider}` stores dashboard aggregates:

```json
{
  "day": "20260706",
  "month": "202607",
  "uid": "firebase uid",
  "email": "person@example.com",
  "provider": "openai",
  "totalCostUsd": 0.0,
  "calls": 12,
  "inputTokens": 12000,
  "outputTokens": 2000,
  "totalTokens": 14000,
  "toolCalls": 0,
  "unpricedEvents": 12,
  "updatedAt": "server timestamp"
}
```

`usagePricing/{provider_sku}` stores configurable pricing with effective dates/active flags. Missing pricing records make dashboard rows show unpriced counts instead of invented dollar costs.
