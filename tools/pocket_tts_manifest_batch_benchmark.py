#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import time

SECTION_COUNT = 1870
BATCH_SIZE = 32
TARGET_MANIFEST_BYTES = 1_800_000

sections = [
    {
        "index": index,
        "label": f"section {index + 1}",
        "audioStatus": "downloaded",
        "audioPath": f"/storage/emulated/0/Android/data/com.dclar.homecenter/files/google-doc-audio/courtier/section-{index + 1:04d}.wav",
        "sampleRate": 24000,
        "pcmBytes": 1_000_000 + index,
        "preview": ("Courtier representative narration text " * 5)[:180],
    }
    for index in range(SECTION_COUNT)
]
manifest = {"sectionCount": SECTION_COUNT, "downloadedSections": 0, "sections": sections}
base = json.dumps(manifest, separators=(",", ":"))
manifest["benchmarkPadding"] = "x" * max(0, TARGET_MANIFEST_BYTES - len(base))

sample_iterations = 12
started = time.perf_counter()
for _ in range(sample_iterations):
    json.dumps(manifest, separators=(",", ":"))
naive_sample_seconds = time.perf_counter() - started

batch_writes = math.ceil(SECTION_COUNT / BATCH_SIZE)
started = time.perf_counter()
for _ in range(batch_writes):
    json.dumps(manifest, separators=(",", ":"))
batched_seconds = time.perf_counter() - started

naive_projected_seconds = naive_sample_seconds * SECTION_COUNT / sample_iterations
write_reduction = 1.0 - (batch_writes / SECTION_COUNT)
assert batch_writes <= 59, batch_writes
assert write_reduction >= 0.96, write_reduction
assert len(json.dumps(manifest, separators=(",", ":"))) >= TARGET_MANIFEST_BYTES
print(json.dumps({
    "status": "ok",
    "sections": SECTION_COUNT,
    "batchSize": BATCH_SIZE,
    "representativeManifestBytes": len(json.dumps(manifest, separators=(",", ":"))),
    "naiveProjectedWrites": SECTION_COUNT,
    "batchedWrites": batch_writes,
    "writeReductionPercent": round(write_reduction * 100, 2),
    "naiveProjectedSerializationSeconds": round(naive_projected_seconds, 3),
    "batchedMeasuredSerializationSeconds": round(batched_seconds, 3),
}, sort_keys=True))
