# ASCII Kinesis corpus retrieval

This is the compact retrieval layer for the long-running ASCII Kinesis specimen collection.

It exists so the scheduler can keep producing motion evidence without requiring a human or model to load every tween, contact sheet, HTML player, or video into context.

## Authority ladder

The corpus follows the same source discipline used by Thunder Brainstorm and Story Brainstorm:

1. **Specimen**: committed `manifest.json`, `motion.json`, receipt, ASCII/contact-sheet, HTML/video, and exact hashes remain authoritative.
2. **Observation record**: deterministic facts are extracted from committed JSON. No generated interpretation is allowed here.
3. **Authored semantic terms**: only strings already authored in the specimen are indexed, including primitive, lane, role, key names, causal roles, contact states, support states, timing classes, and events.
4. **Retrieval surfaces**: compact query output, optional JSONL snapshots, summary, and Markdown report help humans and agents find a small number of specimens.

The retrieval layer never promotes, retimes, redraws, or replaces an animation. If a compact record and the specimen disagree, the specimen wins.

## Context rule

> Retrieval expands resolution. Context never starts at full specimen resolution.

Normal lookup should consume one-line records first. Open a compact record second. Open `motion.json` or the rendered specimen only when the compact evidence is insufficient.

Do not load a directory of ASCII frames merely to answer a search question.

## Query the current corpus

Default `inventory`, `search`, and `show` calls scan the committed V2 manifest/motion JSON **at call time**. They do not silently prefer an older generated index. This matters because the scheduler keeps adding specimens.

```sh
python3 tools/ascii_kinesis_corpus.py inventory
python3 tools/ascii_kinesis_corpus.py search "landing debt"
python3 tools/ascii_kinesis_corpus.py search "support transfer" --lane contact
python3 tools/ascii_kinesis_corpus.py show v2-airborne-003-apex-spacing-window
python3 tools/ascii_kinesis_corpus.py show v2-airborne-003-apex-spacing-window --json
```

`inventory` returns only corpus counts and lane/gate summaries. `search` emits compact one-line records. `show` emits one deterministic observation record and pointers back to the exact specimen. None of them dumps the raw ASCII body.

## Persist an explicit snapshot/report

From the repository root:

```sh
python3 tools/ascii_kinesis_corpus.py build
```

This scans `experiments/ascii-kinesis/**/manifest.json` and accepts only manifests with schema `ascii-kinesis.swarm-manifest.v2`, format version 2, a path-matching experiment ID, a matching `motion.json`, and at least one authored key/pose.

Outputs:

```text
generated/ascii-kinesis-corpus/
  motion_source_refs.jsonl
  motion_index_summary.json
  motion_index_report.md
  rejected_v2_records.jsonl
```

These files are a reproducible **snapshot**, not a global-latest pointer. If a caller deliberately wants that frozen snapshot instead of current source, pass it explicitly:

```sh
python3 tools/ascii_kinesis_corpus.py search "landing debt" \
  --index generated/ascii-kinesis-corpus/motion_source_refs.jsonl
```

`rejected_v2_records.jsonl` is deliberate. A malformed V2 specimen is excluded from the usable index and recorded with its reason instead of being guessed into completeness.

Legacy and non-V2 material remains readable in place but is not silently upgraded into this index.

## Determinism and staleness

The snapshot files are reproducible from committed specimens:

```sh
python3 tools/ascii_kinesis_corpus.py verify
```

`verify` exits nonzero if the persisted snapshot does not exactly match a fresh deterministic rebuild. This detects stale reports while keeping normal queries immune to stale-snapshot blindness.

Structural regression test:

```sh
python3 tools/test_ascii_kinesis_corpus.py
```

The test covers deterministic regeneration, exact authored semantic-term retention, nested support-state extraction, specimen provenance, raw-ASCII exclusion, current-source query behavior, explicit reproducible snapshots, and fail-closed malformed or empty V2 handling. It does **not** claim that any motion is artistically good.

## Relationship to the other systems

- **Motion Dungeon** owns the actual moving/rendered artifact and visual acceptance.
- **ASCII Kinesis** owns the source-backed text-native motion specimens.
- **Thunder Brainstorm** provides the precedent for compact provenance-bearing source refs and corpus indexes.
- **Story Brainstorm** provides the evidence -> observation -> abstraction firewall.
- **This corpus layer** applies those retrieval laws to motion without creating a new animation authority.

The scheduler may generate indefinitely. The corpus may grow on disk while normal model context stays small.

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

Lineage, deduplication, preference pairs, and richer derived motion primitives can be added later only after this source-backed observation layer is exercised on the real corpus.
