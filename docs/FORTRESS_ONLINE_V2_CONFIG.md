# Fortress Online V2 — Config-First Operation

Fortress V2 is configured in layers on every invocation. Routine operating changes must not require a code deployment.

## Layers
1. Repository defaults: `config/fortress-online.v2.json`
2. Live user override: `~/.config/fortress-online/config.json`
3. Optional explicit override: path in `FORTRESS_CONFIG_PATH`

Later layers deep-merge over earlier layers. Arrays replace arrays. Every merged result is validated before Fortress boots. Invalid config fails closed.

## Configurable without deployment
- mission state sequence, default owner, completion states, and operator-input stop boundaries;
- request-budget / anti-hammer policy;
- learning classifiers, regex patterns, recipes, isolation and promotion requirements;
- core skill inventory, purposes, required flags, Phone Hands operation routes and invariants;
- canonical required `SKILL.md` books;
- skill scan exclusions and boot capsule metadata.

The launcher rereads configuration every time it boots. Updating `~/.config/fortress-online/config.json` therefore changes the next invocation without replacing source, reinstalling Fortress, restarting Phone Hands, or redeploying Home Center.

## What still requires code deployment
Only changes to the configuration schema/validator, execution primitives, security boundary, parser/merge semantics, or genuinely new kernel capability require source deployment. If behavior can be represented safely in the existing config schema, changing code instead is a regression.

## Safety invariant
Config may select and tune bounded existing behavior; it does not create arbitrary new authority. The merged config must retain a valid Phone Hands skill with `phone_hands.devices`, `phone_hands.enqueue`, and `phone_hands.get`, and canonical required skill books must still be present. Invalid overrides fail boot rather than silently falling back.

## Evidence
Acceptance requires a live test that boots once with defaults, writes a temporary user override, boots again without changing source or reinstalling, observes a changed config version/hash/layer set, and restores the previous override. This proves the hot-config path rather than merely documenting it.
