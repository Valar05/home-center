# TIME NOW — FULL SKILL CENSUS SWARM CAMPAIGN

Status: DISPATCHED
Owner: local worker swarm, not chat narrator
Operator: Drew; never command transport

## Mission
Enumerate EVERY recoverable skill/doctrine/organ/jar/operator pattern across the authorized durable surfaces and build a chronology-aware index that Time Now can recover deterministically. This includes, without limitation, Hunger, Thirst, Hair Away Operator / Airway Operator variants, Aggregated Synthesis, Time Now, jars, organs, judgment engines, worker contracts, Library skills, repo skills, Drive skills, archived skills, and named procedural doctrines.

Do not infer completeness from semantic search. Inventory first; classify second; inspect content third; merge aliases only with evidence.

## Swarm lanes
Run concurrently under tmux/local workers. Every lane writes append-only receipts and may not declare global completion.

1. REPO CENSUS — enumerate every SKILL.md, skill-like markdown, doctrine, organ, jar, campaign contract, AGENTS/worker contract, and named operator pattern in the repository and relevant branches.
2. LIBRARY CENSUS — enumerate Library metadata recursively, newest-first and then complete traversal; inspect likely skill/doctrine/organ/jar artifacts. Preserve file_id, name, path if available, created/modified timestamps, and evidence excerpts.
3. DRIVE CENSUS — enumerate authoritative Drive skill/doctrine surfaces and indexes. Preserve document IDs/paths and timestamps where available.
4. THREAD/RECEIPT MINER — mine durable thread exports/receipts/context dumps for named skills and variants that may not yet exist as standalone artifacts. Mark these REQUESTED/MENTIONED until artifact evidence exists.
5. ALIAS/JUDGMENT — reconcile names such as Airway/Hair Away, variants, renamed skills, superseded doctrine, and collisions. Never silently merge uncertain identities.
6. TIME NOW INDEXER — produce one machine-readable chronological index with newest authoritative receipt first, plus semantic tags only as secondary retrieval.
7. CANARY — test known fixtures: query 'concept organization skill made today' must recover Aggregated Synthesis before older Guinness Sense Synthesis; query Hunger must locate its actual indexed authority; query Thirst and Hair Away/Airway must either recover evidence or explicitly report the evidence gap without guessing.

## Required index record
- canonical_name
- aliases[]
- kind: skill|doctrine|organ|jar|operator|campaign|unknown
- authority_state: requested|mentioned|artifact|tested|deployed|superseded|rejected
- source_surface
- source_id/path/ref
- created_at
- modified_at
- observed_at
- evidence_excerpt/hash where available
- supersedes / superseded_by
- tags[]
- retrieval_priority
- unresolved_questions[]

## Time Now retrieval order
1. Interpret temporal phrase using current time.
2. Enumerate artifacts/receipts in that window.
3. Rank direct names + chronology + authority state.
4. Inspect candidate artifact itself.
5. Only then use semantic similarity as fallback.
6. Return evidence and distinguish artifact from mention/request/deployment.

## Completeness gate
NOT COMPLETE until each census lane emits a receipt, the merged index records coverage counts by surface, alias conflicts are explicit, and the canary suite passes. 'I searched for several likely terms' is failure.

## Operator gate
Do not ask Drew to enumerate names, paste commands, inspect logs, or remember where a skill lives while an authorized durable surface can answer it.

## Joy gate
The swarm may preserve characterful names and weird provenance. It must not flatten memorable skills into generic enterprise taxonomy. Retrieval should bring the treasure home, not sterilize it.
