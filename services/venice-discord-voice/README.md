# Venice Discord voice carrier

Private Cloud Run service for one explicitly invited spoken reply in the Discord
voice channel currently occupied by the invoking user.

- The service never records or subscribes to inbound voice.
- Every request must match the durable Firestore consent state and exact epochs.
- A state change, room withdrawal, or global cut stops playback and disconnects.
- It disconnects after each reply.
- `VENICE_VOICE_NAME` is a candidate carrier voice, not canonical Venice identity.

The service expects `DISCORD_BOT_TOKEN` and `GEMINI_API_KEY` as secret-backed
environment variables and is intended to be IAM-private.
