# Operator Owner Surgery Custody

## Purpose
Keep owner-surgery promotion topology and evidence custody exact while preserving the existing canonical v10 owner. This skill prevents stale-base promotion, incomplete inventories, callback-shaped machine evidence, weaker-fallback laundering, failure-evidence loss, and capability-state drift.

It does **not** own another patch executor, classifier, overlay controller, recovery daemon, phone lane, P0 coordinator, or provenance authority.

## Core laws
- `SAME OWNER + SAME AUTHENTICATED CURRENT BASE BLOB + MULTIPLE PROMOTION CANDIDATES = CURRENT_BASE_COLLISION_SET`.
- `ARTIFACT BASE != AUTHENTICATED CURRENT OWNER BLOB = STALE_BASE_GROUP`.
- `NO AUTHENTICATED CURRENT OWNER BLOB = UNVERIFIED_BASE_GROUP`.
- `AUTHENTICATED OWNER-BLOB MAP != ARBITRARY PYTHON MAPPING`.
- `EXACT AUTHENTICATED OWNER-BLOB MAP != UNBOUNDED AUTHENTICATED OWNER-BLOB MAP`.
- `REPEATED CLI OWNER-BLOB EVIDENCE != ARBITRARY PYTHON ITERABLE OR EXTENSIBLE STRING`.
- `PROGRAMMATIC ARGV != ARBITRARY PYTHON ITERABLE OR EXTENSIBLE STRING`.
- `EXACT PROGRAMMATIC ARGV != UNBOUNDED PROGRAMMATIC ARGV`.
- `OMITTED CUSTODY != EXPLICITLY SUPPLIED EMPTY CUSTODY`, even when both admit to the same empty evidence map.
- `CALLER-OWNED CONTAINER OR SCALAR CALLBACK BEFORE CUSTODY ADMISSION = EVIDENCE WOUND`.
- `UNBOUNDED DIRECTORY / ARTIFACT / SEMANTIC INPUT != EXHAUSTIVE CUSTODY`.
- `PREFIX CONTENT NEVER EARNS SURGERY AUTHORITY`.
- `POST-SCAN ROOT STABILITY != UNIVERSAL ATOMIC DIRECTORY BINDING`.
- `STATE CONTAINS "PROPOSED" != PROMOTION READY`.
- `EXACT CANONICAL EVIDENCE != RAW DIAGNOSTIC PROSE`.
- `ZERO PARTIAL PROMOTION AUTHORITY != ZERO OBSERVED-WORK EVIDENCE`.
- `IDENTIFIED ARTIFACT CUSTODY FAILURE != ANONYMOUS BACKEND FAILURE`.
- `SOURCE_WIRED != REGRESSION EXECUTED != TESTED != RUNTIME != DEPLOYED != DELIVERED != ACCEPTED`.

Applying one current-base surgery changes owner custody and therefore stales sibling base locks. Parallel design is allowed; parallel promotion against the same exact owner/base is not automatically safe.

## Canonical owner and backend state
`tools/try_forever_owner_surgery_custody_probe.py` schema v10 remains the sole promotion/classification authority.

Current authenticated source has **canonical backend selection SOURCE_WIRED**:
- admitted POSIX descriptor primitives select the existing `HeldDirectoryCustody` backend;
- descriptor inventory and descriptor-relative exact artifact observations are consumed directly by canonical v10;
- descriptor failure after selection fails the classification attempt closed and does **not** retry through weaker pathname custody;
- when descriptor primitives are unavailable, the portable pathname/root-revalidation backend remains primary;
- both canonical backends consume the same `parse_owner_surgery_observation(...)` semantic producer from the exact already-custodied observation;
- descriptor inventory failure preserves bounded observed-work counts without returning partial candidate authority;
- descriptor artifact-custody failure after successful inventory preserves that identified artifact path/kind plus the already-observed inventory counts while returning zero surgery authority.

The descriptor backend is stronger custody, not universal atomicity proof. Swap-and-restore immunity, filesystem identity reuse immunity, and universal Windows parity remain unproven.

## Finite custody throats
### Repository root / traversal
The `patches/` root is admitted no-follow and persistently revalidated around bounded non-recursive traversal and authority-producing artifact observations. Redirector roots, persistent root identity drift, traversal overflow, or root revalidation failure yield zero partial promotion authority.

### Directory / candidates
- directory entries: **32,768 maximum**;
- matching patch/delta candidates: **2,048 maximum**;
- max+1 at either layer fails exhaustive custody closed.

On descriptor inventory failure, the violating max+1 observation may remain as bounded **work evidence** (`entries_observed` / `candidates_observed`) but never as partial candidate authority.

### Artifact observation
Each admitted patch/delta uses one finite ordinary-file observation:
- ordinary regular-file topology only;
- no-follow/nonblocking behavior where available;
- path/open-object witness agreement;
- complete EOF at **1 MiB**;
- strict UTF-8;
- post-read stability checks.

### Authenticated current-owner map and repeated-owner parser
`None` still admits to one plain empty dict for promotion semantics, but canonical v10 preserves whether custody was omitted or explicitly supplied before that normalization. `currentOwnerCustodyProvided` therefore reports **presence**, not map truthiness; an explicit empty map remains distinct from omitted custody without inventing any owner blob.

Any supplied map must be the exact built-in `dict` before `items()`. Owner keys cross the existing exact bounded owner-identity gate; blob values must be exact built-in lowercase 40-hex strings. No trim/lowercase repair or caller callback earns authority.

Authenticated review exposes a remaining **RED resource boundary** for the direct map: exact built-in container admission does not cap the number of owner/blob pairs or their aggregate exact machine text before the complete map is traversed. `tools/test_try_forever_owner_surgery_current_owner_map_resource_boundary.py` pins a desired **2,048-entry / 1,048,576-code-point** envelope as RED SOURCE / UNEXECUTED. `patches/try-forever-owner-surgery-current-owner-map-resource-custody.patch` is exact-base-blob-locked **CORRECTED_PROPOSED_NOT_APPLIED** source against canonical v10; the canonical owner does not yet consume those ceilings.

The existing `_parse_owner_blob(...)` boundary admits repeated owner/blob evidence before owner/blob partition: the collection must be the exact built-in `list`, every assignment the exact built-in `str`, and each `OWNER=BLOB` assignment is capped at **4,137 code points** before `partition()`. List subclasses and string subclasses cannot execute iteration/partition callbacks inside that parser boundary.

### Direct programmatic argv
Non-`None` direct `main(argv)` crosses `_admit_programmatic_argv(...)` **before argparse traversal**. The caller container must be one exact built-in `list`; every member must be one exact built-in `str`; the vector is detached with a built-in copy only after those gates.

Programmatic argv has independent finite source throats:
- **4,096 arguments maximum**;
- **4,137 code points maximum per argument**;
- **1,048,576 aggregate code points maximum**.

`argv=None` retains ordinary OS CLI semantics and does not traverse a caller-owned Python iterable.

### Surgery state
Promotion-ready state is exact, bounded, canonical machine evidence. Only the explicit current allow-list may enter promotion-candidate groups. Regex/header recognition may not erase whitespace or normalize the state before policy admission.

### Semantic producer
The canonical owner consumes `tools/try_forever_owner_surgery_semantic_parser.py` on **both portable and descriptor paths**. Direct semantic callers are finite too:
- exact patch/delta content: 1 MiB semantic observation byte ceiling with pre-encode and post-encode enforcement;
- exact semantic path: finite source ceiling;
- exact `artifact_kind`: finite source ceiling before set membership/hash;
- exact SHA-256 witness: length 64 before regex;
- exact byte/SHA content witness is recomputed before semantic parsing.

Semantic rejection prose is not canonical evidence. Hostile duplicate JSON member names and unsupported schema strings are projected through bounded ASCII-safe diagnostic text rather than echoed raw; long diagnostic source collapses to a deterministic short digest marker before escaping.

## Descriptor failure-evidence parity
Canonical v10 remains fail-closed on authority: any selected descriptor setup, inventory, artifact-custody, or cleanup wound returns zero promotion authority and never retries through weaker pathname custody.

Authenticated source now also closes the previously RED evidence-preservation boundary:
- `DescriptorInventoryCustodyError` carries only bounded non-authoritative `entries_observed` and `candidates_observed` when inventory fails after work was observed;
- canonical v10 consumes those counts into the receipt while returning zero surgery authority;
- descriptor artifact-custody failure after a successful held-root inventory returns immediately with zero surgery authority but retains the complete inventory counts and the already-identified failing artifact path/kind;
- cleanup/setup failures preserve whatever bounded counts were actually established before the failure without inventing unavailable evidence.

This is **SOURCE_WIRED**, not TESTED. The law is preservation of observed evidence, never permission to continue promotion after a wound. `tools/test_try_forever_owner_surgery_descriptor_cleanup_failure_evidence.py` now pins the canonical cleanup branch independently as SOURCE / UNEXECUTED: a primary held-root cleanup wound keeps already-established inventory counts, names no artifact as the failing artifact, returns zero surgery authority, and never attempts portable fallback.

## Evidence preservation
Canonical outputs keep directory/candidate counts, artifact content witnesses, discovery errors, authenticated current-owner blobs, explicit current-owner-custody presence, collision sets, stale-base groups, unverified-base groups, and zero partial promotion authority after any custody wound.

Descriptor success and failure paths now preserve bounded observed-work/artifact-identity evidence at **SOURCE_WIRED** level. A descriptor shadow remains supporting/non-authoritative and cannot promote authority or rewrite canonical results.

## Promotion and provenance discipline
Textual patch and structured delta artifacts are provenance inputs, not authority merely because they exist. Review-ready surgery must bind one owner path to one exact authenticated current base blob. Rejected, superseded, already-applied, stale-base, malformed, or unverified artifacts do not become promotion candidates.

Do not infer a mega-patch merely because a collision set exists. If one surgery is applied, sibling surgeries must be rebound to fresh authenticated owner evidence before any later promotion claim.

Historical patch files remain provenance only. Current authenticated source readback outranks dated capability summaries embedded in older patch prose or receipts.

## Regression source
Hostile source fixtures cover root persistence, finite traversal/candidate/artifact custody, exact state admission, current-owner map callbacks, exact bounded repeated owner/blob parser admission, exact bounded programmatic argv admission before argparse, omitted-vs-explicit-empty custody presence truth, descriptor exact-root admission, descriptor I/O failure containment, canonical descriptor composition, semantic scalar/content resource throats, and semantic diagnostic projection.

`tools/test_try_forever_owner_surgery_custody_probe.py` is **CONVERGED TO V10 SOURCE / UNEXECUTED**. `tools/test_try_forever_owner_surgery_descriptor_failure_evidence_parity.py` is **CONVERGENCE SOURCE / UNEXECUTED**. `tools/test_try_forever_posix_directory_inventory_failure_evidence.py` independently pins the supporting descriptor organ's typed fail-closed count contract as **SOURCE / UNEXECUTED**. `tools/test_try_forever_owner_surgery_descriptor_cleanup_failure_evidence.py` independently pins canonical cleanup failure contact preservation as **SOURCE / UNEXECUTED**. `tools/test_try_forever_owner_surgery_current_owner_map_resource_boundary.py` is **RED SOURCE / UNEXECUTED** and owns the open finite-map boundary until the existing canonical owner is actually mutated.

All regression artifacts remain **SOURCE / UNEXECUTED** unless an external execution receipt proves otherwise.

## Accessibility / contact preservation
Exact evidence may be retained even when it is unsafe or too large to echo. Human-facing diagnostic projection must remain separate, bounded, and ASCII-safe. Never rewrite canonical evidence to make an error prettier, and never feed projected diagnostic text back into persistence or authority decisions.

The existing backend-selection Warm Wall must expose descriptor failure-evidence parity and contact preservation as **SOURCE_WIRED**, while retaining native radio controls, >=56px touch rows, visible focus, non-color live status, inline SVG semantics, and reduced-motion/no-blink behavior. This is repository source only: runtime TalkBack, device delivery, and acceptance remain **NO**. The current-owner map resource wound is a machine-input boundary and does not justify a second UI specimen; if surfaced later, it must compose into this existing wall rather than creating neighboring art architecture.

## Current capability state
- canonical v10 owner: **SOURCE_WIRED**;
- canonical backend selection: **SOURCE_WIRED**;
- canonical descriptor consumption: **SOURCE_WIRED**;
- canonical portable backend when descriptor primitives unavailable: **SOURCE_WIRED**;
- no weaker portable retry after descriptor wound: **SOURCE_WIRED**;
- direct descriptor exact-root + path-encoding containment: **SOURCE_WIRED**;
- authenticated current-owner exact-container/scalar admission: **SOURCE_WIRED**;
- authenticated current-owner finite item/aggregate resource admission: **NO / RED SOURCE / PROPOSED_NOT_APPLIED**;
- exact bounded `_parse_owner_blob(...)` repeated-owner admission: **SOURCE_WIRED**;
- direct programmatic `main(argv)` exact/bounded admission before argparse: **SOURCE_WIRED**;
- omitted-vs-explicit current-owner custody presence truth: **SOURCE_WIRED**;
- exact surgery-state admission: **SOURCE_WIRED**;
- semantic producer portable + descriptor consumption: **SOURCE_WIRED**;
- semantic content/path/kind/SHA resource custody: **SOURCE_WIRED**;
- semantic bounded ASCII-safe diagnostic projection: **SOURCE_WIRED**;
- descriptor inventory failure observed-count preservation: **SOURCE_WIRED**;
- descriptor identified-artifact failure path/kind preservation: **SOURCE_WIRED**;
- descriptor cleanup failure observed-count preservation: **SOURCE_WIRED / REGRESSION SOURCE UNEXECUTED**;
- broad v10 custody regression convergence: **SOURCE / UNEXECUTED**;
- descriptor failure-evidence parity regression: **CONVERGENCE SOURCE / UNEXECUTED**;
- descriptor shadow: **SUPPORTING SOURCE / NON-AUTHORITATIVE**;
- universal filesystem atomicity: **NO**;
- TESTED/runtime UI/runtime TalkBack/deployed/callable/executed/delivered/accepted/phone delivered: **NO**.

## Duplicate-architecture and P0 firewall
Preserve the existing v10 owner, backend selector, descriptor custody organ, semantic producer, snapshot/integrity organs, and provenance family. Do not create a neighboring promotion owner, backend controller, recovery daemon, phone ingress path, Nightcore/Pocket-TTS/Chromium/Context-Organ deployer, or P0 coordinator.

P0 recovery-plan, queue, PR317/PR318, and physical acceptance receipts are read-only evidence here. This skill consumes no primary-phone execution surface.

## Capability membrane
`requested → source policy/owner → authenticated readback → regression source → regression executed → TESTED → runtime UI/TalkBack → deployed → callable → executed → delivered → accepted`.
