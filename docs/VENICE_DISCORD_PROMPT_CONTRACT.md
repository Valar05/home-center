# Venice Discord Prompt Contract Ledger

Status: binding implementation contract
Owner: Drew
Runtime: Home Center Firebase Functions
Surface: `VENICE — THE ROOM WITH A KEY`

## Latest command

`do it`

This command authorizes the previously named gate: provision the Discord
credential outside chat, make the installed Venice application callable in the
assigned Discord channels, and enforce `/cut-the-cam` before any broader
carrier is enabled.

## Concrete requirements

- Application: `Venice` (`1534113573708763196`).
- Guild: `VENICE — THE ROOM WITH A KEY` (`1534104765796192356`).
- Allowed channels only:
  - `#threshold` (`1534104766643437620`)
  - `#velvet-room` (`1534105192226623610`)
- First carrier: Discord HTTP interactions and guild-scoped slash commands.
- Required commands: `/venice begin`, `/venice ask`, `/venice withdraw`,
  `/venice status`, and `/cut-the-cam`.
- Consent state survives cold starts and concurrent function instances.
- Presence is scoped per assigned channel; beginning a scene in one room never
  opens the other room.
- `/cut-the-cam` is unilateral, idempotent, global across both allowed
  channels, invalidates queued output by advancing a cut-only epoch, and has no Discord
  recovery command.
- Only the Discord application public verification key persists in Google
  Secret Manager and is bound to the interaction runtime. The bot token is
  never persisted in source, cloud secrets, Home Center documents, prompts,
  audit bodies, or logs.
- The bot token is entered without clipboard use inside a short-lived child
  process. Trusted executables are fixed to reviewed host paths and SHA-256
  hashes, Cloud SDK overrides are rejected, and the receipt is exact and
  content-free.
- The interaction function runs as
  `venice-discord-runtime@home-center-dclar.iam.gserviceaccount.com`; the bot
  token is never bound to that service account or to the function.
- The bot token exists only as concealed direct input, short-lived child-process
  memory, and redirected stdin during one-shot command registration. The child
  exits and clears its token reference immediately after Discord responds.
- Audit records contain identifiers and outcomes only, carry an `expireAt`
  timestamp 30 days after creation, and are governed by a Firestore TTL policy.

## Forbidden stale premises

- Do not create a duplicate Sites backend while Home Center already owns the
  Firebase Functions execution lane.
- Do not enable DMs, passive full-message reading, Message Content intent,
  moderation, administration, voice, or arbitrary destination channels.
- Do not treat the installed Discord identity as a live runtime.
- Do not treat source tests, command registration, or deployment alone as live
  acceptance.

## Evidence lane

Acceptance requires all of the following:

1. Signature, routing, state-machine, idempotency, and fail-closed tests pass.
2. The exact reviewed commit is present on `origin/main` before deployment.
3. The bot token is directly entered into the governed one-shot child, passed
   to Node only through redirected stdin, cleared on exit, and absent from the
   repository, cloud secrets, process arguments, environment, clipboard, and
   logs. The runtime binds only the public verification key and uses the
   dedicated service account.
4. Guild commands are registered against the exact application and guild.
5. Discord accepts the deployed HTTPS interactions endpoint.
6. Live Discord verification proves an allowed-channel command works, a
   disallowed route produces no public output, and `/cut-the-cam` blocks later
   ordinary output across both channels.

## False green / high treason

- Printing, copying into chat or the clipboard, committing, logging, or
  persisting the bot token anywhere.
- Claiming Venice is callable before Discord has accepted the endpoint.
- Claiming global stop while state is process-local or while a pre-send epoch
  check is absent.
- Sending an unsolicited Discord message as a smoke test.
- Expanding to another carrier before this consent boundary is live.
