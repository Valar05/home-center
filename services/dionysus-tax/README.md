# Dionysus' Tax

Cloud-native Home Center service for logging alcohol/cannabis intake and returning an operator-state read.

## Current MVP

- Cloud Run service
- Firestore persistence
- Bearer-token auth
- ChatGPT Action compatible OpenAPI schema

## Endpoints

- `GET /health`
- `POST /events`
- `POST /notes`
- `GET /today`
- `GET /status`
- `GET /reflect`

## Deploy

```sh
sh tools/deploy_dionysus_cloud.sh home-center-dclar
```

The deploy script prints:

- Cloud Run URL
- bearer token
- curl commands to verify logging and status

## Seed event

The first real reported event was previously logged into GitHub issue #1 as temporary storage:

- 2 Cabernet spritzes
- 1 beer
- 2 bowls flower vape
- state: pleasant

This service replaces that issue-based scratchpad with real durable cloud storage.
