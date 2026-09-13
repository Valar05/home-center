# ASCII Kinesis corpus retrieval

This is the compact retrieval layer for the long-running ASCII Kinesis specimen collection.

It exists so the scheduler can keep producing motion evidence without requiring a human or model to load every tween, contact sheet, HTML player, or video into context.

## Authority ladder

The corpus follows the same source discipline used by Thunder Brainstorm and Story Brainstorm:

1. **Specimen**: committed `manifest.json`, `motion.json`, receipt, ASCII/contact-sheet, HTML/video, and exact hashes remain authoritative.
2. **Observation record**: deterministic fields are extracted from committed JSON. No generated interpretation is allowed here.
3. **Explicit abstraction terms**: only authored labels already present in the specimen are indexed: lane, candidate role, motion name, key names, event names, source role, and contract status.
4. **Retrieval surfaces**: JSONL index, summary, and Markdown report help humans and agents find a small number of specimens.

The report never promotes, retimes, redraws, or replaces an animation. If a compact record and the specimen disagree, the specimen wins.

## Context rule

> Retrieval expands resolution. Context never starts at full specimen resolution.

Normal lookup should consume one-line records first. Open a compact record second. Open `motion.json` or the rendered specimen only when the compact evidence is insufficient.

Do not load a directory of ASCII frames merely to answer a search question.

## Build

From the repository root:

```sh
python3 tools/ascii_kinesis_corpus.py build
```

This scans `experiments/ascii-kinesis/**/manifest.json` and accepts only manifests with schema `ascii-kinesis.swarm-manifest.v2` plus a matching `motion.json`.

Outputs:

```text
generated/ascii-kinesis-corpus/
  motion_source_refs.jsonl
  motion_index_summary.json
  motion_index_report.md
  rejected_v2_records.jsonl
```

`rejected_v2_records.jsonl` is deliberate. A malformed V2 specimen is excluded from the usable index and recorded with its reason instead of being guessed into completeness.

Legacy and non-V2 material remains readable in place but is not silently upgraded into this index.

## Query

After a build:

```sh
python3 tools/ascii_kinesis_corpus.py search "landing debt"
python3 tools/ascii_kinesis_corpus.py search "support transfer" --lane contact
python3 tools/ascii_kinesis_corpus.py show v2-airborne-003-apex-spacing-window
python3 tools/ascii_kinesis_corpus.py show v2-airborne-003-apex-spacing-window --json
```

`search` emits compact lines. `show` emits one compact observation record and pointers back to the exact specimen. Neither command dumps the raw ASCII body.

## Determinism and staleness

The generated files are reproducible from committed specimens:

```sh
python3 tools/ascii_kinesis_corpus.py verify
```

`verify` exits nonzero if the committed retrieval outputs do not exactly match a fresh deterministic rebuild.

Structural regression test:

```sh
python3 tools/test_ascii_kinesis_corpus.py
```

The test covers deterministic regeneration, provenance retention, raw-ASCII exclusion from compact records, search behavior, and fail-closed malformed V2 handling. It does **not** claim that any motion is artistically good.

## Relationship to the other systems

- **Motion Dungeon** owns the actual moving/rendered artifact and visual acceptance.
- **ASCII Kinesis** owns the source-backed text-native motion specimens.
- **Thunder Brainstorm** provides the precedent for compact provenance-bearing source refs and corpus indexes.
- **Story Brainstorm** provides the evidence -> observation -> abstraction firewall.
- **This corpus layer** applies those retrieval laws to motion without creating a new animation authority.

The scheduler may generate indefinitely. The retrieval layer should get larger on disk while normal model context stays small.

## Non-goals

This layer does not:

- change the scheduler;
- modify the ASCII Kinesis generator;
- modify Motion Dungeon;
- canonize or artistically accept scheduler output;
- infer semantic labels that were not authored in source metadata;
- train a model;
- deduplicate or mutate specimens yet;
- hide the exact specimen path or hash behind a summary.

Lineage, deduplication, preference pairs, and richer motion primitives can be added later only after the source-backed observation layer is proven useful on the real corpus.
