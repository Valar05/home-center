# Walmart Cart Agent

Agent-facing tooling for turning the live Home Center shopping list into a Walmart mapping review queue. This is not checkout automation. The cart boundary is Add to Cart only.

## Build a review queue

```sh
python3 agent-tools/walmart-cart-agent/walmart_cart_agent.py build-review --expect-count 46
python3 agent-tools/walmart-cart-agent/walmart_cart_agent.py report
```

The queue records mapped items, unresolved items, quantity problems, Walmart search links, and a Home Center command phrase to save a confirmed mapping.

## Export for the Home Center app

```sh
python3 agent-tools/walmart-cart-agent/walmart_cart_agent.py export --expect-count 46
```

This writes Android-visible files under `/storage/emulated/0/Download/HomeCenter/cart-review/`:

- `review-latest.json` for the in-app Cart Review importer.
- `review-latest.commands.txt` for terminal/agent review.

The export command requests an Android media scan so Google Files and app pickers can see the bundle promptly.

## Open Walmart handoff links

```sh
python3 agent-tools/walmart-cart-agent/walmart_cart_agent.py open --status needs_choice --surface buy-again
python3 agent-tools/walmart-cart-agent/walmart_cart_agent.py open --key ranch --surface search
```

Use Buy Again in a logged-in Walmart app/browser first. If the account history does not resolve the item, use the search link and save the accepted product back into Home Center using the generated `map ... to walmart target ...` command.

## Agent item-by-item workflow

The script is agent-executable through `python3` and supports a noninteractive loop. Android shared storage may not preserve `chmod +x`, so use `python3` explicitly from this repo:

```sh
python3 agent-tools/walmart-cart-agent/walmart_cart_agent.py next-item --review .tmp/walmart-live-review.json
python3 agent-tools/walmart-cart-agent/walmart_cart_agent.py open --review .tmp/walmart-live-review.json --key ranch --surface buy-again
python3 agent-tools/walmart-cart-agent/walmart_cart_agent.py verify-item --review .tmp/walmart-live-review.json --key ranch --brand "Hidden Valley" --size "24 fl oz" --quantity 1 --sku 12345 --product-url https://www.walmart.com/ip/12345
```

Do not mark an item verified until brand, size, and quantity have all been checked against the Walmart product page or Buy Again result. `verify-item` stores those checks in the review artifact and rewrites the item's Home Center save command.

## Cart event bridge

Home Center emits cart runner and manual-add events to an Android-visible JSONL file:

```text
/storage/emulated/0/Download/HomeCenter/cart-events/YYYY-MM-DD.jsonl
```

Events include `manual_add_pressed`, `armed`, `add_attempted`, `added`, and `blocked` with the verified item key, product URL, brand, size, and quantity when available. The Android app also attempts a Termux `com.termux.RUN_COMMAND` wake that runs:

```sh
python3 agent-tools/walmart-cart-agent/cart_event_wake.py
```

Termux must allow external app commands for the wake path; if Android blocks that intent, the JSONL event file remains the durable command-center handoff.

