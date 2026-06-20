# Home Center Data Model

Firestore root:

```text
households/{bucketId}
households/{bucketId}/members/{uid}
households/{bucketId}/groups/{groupId}
households/{bucketId}/groups/{groupId}/members/{uid}
households/{bucketId}/lists/{listId}
households/{bucketId}/lists/{listId}/tasks/{taskId}
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
