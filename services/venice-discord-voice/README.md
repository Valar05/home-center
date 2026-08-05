# Venice Discord voice carrier

Private Cloud Run service for one explicitly invited spoken reply in the Discord
voice channel currently occupied by the invoking user.

- The service never records or subscribes to inbound voice.
- Every request must match the durable Firestore consent state and exact epochs.
- A state change, room withdrawal, or global cut stops playback and disconnects.
- It disconnects after each reply.
- Speech is buffered as normalized Ogg/Opus with a receive preroll so Discord
  clients have time to attach before the first spoken sample.
- `VENICE_VOICE_NAME` is a candidate carrier voice, not canonical Venice identity.

Voice delivery profiles are bounded and content-free in logs: roleplay cues route
to `whisper`; ordinary turns default to `chipper`; explicit `voice:` cues may
select `warm`, `firm`, `playful`, `gentle`, or `random` candidate delivery.

The service expects `DISCORD_BOT_TOKEN` and `GEMINI_API_KEY` as secret-backed
environment variables and is intended to be IAM-private.
