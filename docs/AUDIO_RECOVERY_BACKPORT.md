# Fast verified audio recovery

Drive-hosted accepted audio is recovered through `audio.ingest_drive`: one server-side Drive stream into staged GCS, source/stage/destination SHA-256 verification, canonical promotion, and immutable indexes. Chat-sized binary chunk reconstruction is an emergency inspection fallback, not the production recovery lane.

Deployment branches must preserve the monotonic operation registry. A deployment that drops a previously live operation is a regression even when its new feature passes independently.
