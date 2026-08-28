# Heartbeat Report-Emission Snapshot Revalidation

## Purpose
Keep repository-skill authority bound to one coherent, bounded repository observation before discovery, after discovery, and again at final emission. Generated-index currentness may survive only when its exact artifact custody also survives.

## Core laws
`ONE GIT STATUS PROCESS != ATOMIC REPOSITORY SNAPSHOT`.

`EXACT branch.oid EVIDENCE != TRIMMED / CASE-NORMALIZED OID`.

`INHERITED GIT REPOSITORY OR CONFIG REDIRECT != REQUESTED REPOSITORY CUSTODY`.

`LATE REVALIDATION IS PRESERVATION-ONLY`.

`SOURCE_WIRED != REGRESSION_EXECUTED != TESTED != RUNTIME != DEPLOYED != DELIVERED != ACCEPTED`.

## Existing observation organ
`tools/try_forever_repository_emission_observation.py` remains the shared repository observation primitive.

It uses one bounded:

`git status --porcelain=v2 --branch --untracked-files=normal --ignore-submodules=none`

process to obtain both HEAD and cleanliness. Porcelain output remains bytes; only `branch.oid` is decoded as strict ASCII.

Current source also requires the OID payload to be exact canonical lowercase SHA-1/SHA-256 text as emitted after the protocol prefix. Whitespace or case normalization cannot repair malformed authority evidence.

The subprocess environment removes inherited repository/config authority redirects including:
- `GIT_DIR`, `GIT_WORK_TREE`, `GIT_COMMON_DIR`, index/object/namespace/shallow overrides;
- `GIT_CONFIG_GLOBAL`, `GIT_CONFIG_SYSTEM`, `GIT_CONFIG_NOSYSTEM`;
- command-scope `GIT_CONFIG_COUNT`, `GIT_CONFIG_PARAMETERS`, `GIT_CONFIG_KEY_*`, `GIT_CONFIG_VALUE_*`.

It also forces `GIT_NO_REPLACE_OBJECTS=1` while retaining benign process environment such as `PATH`.

Timeout or observation failure becomes `UNAVAILABLE`; stale prior HEAD/cleanliness evidence is never donated.

## Current sole-owner composition
Authenticated current-tree source in `tools/try_forever_skill_provenance_probe.py` emits schema `try-forever-skill-provenance.v6` and already consumes this same observation organ:

1. before direct skill discovery;
2. after direct skill discovery;
3. again after generated-index revalidation as the final report-emission repository custody observation.

The pre/post discovery observations feed `assess_repository_snapshot(...)`; only `STABLE_CLEAN` can certify repository-skill authority. The final observation feeds `compose_provenance_emission(...)`; late failure can withhold previously certified repository authority but cannot manufacture new authority.

Generated-index `VERIFIED_CURRENT` survives only when the initial finite artifact observation and conditional late artifact observation retain the exact same inspection SHA under stable final repository custody.

## Regression source
`tools/test_try_forever_repository_emission_observation.py` is **REGRESSION SOURCE / UNEXECUTED**.

It now pins:
- canonical SHA-1 and SHA-256 branch OIDs;
- rejection of uppercase, leading/trailing-space, and tab-suffixed OID evidence;
- duplicate/malformed OID fail-closed behavior;
- byte-hostile filenames marking the tree dirty without path decoding;
- dirty submodule visibility;
- bounded subprocess timeout;
- repository/object/index/config environment isolation, including inherited global/system config-file selectors;
- replacement-object suppression;
- benign `PATH` preservation.

The owner-level initial-snapshot fixtures remain source evidence only; no authorized runner execution receipt exists in this branch checkpoint.

## Current capability truth
- one-process bounded repository observation: **YES / SOURCE**;
- exact branch OID admission: **YES / SOURCE**;
- inherited Git repository/config environment isolation: **YES / SOURCE**;
- provenance owner pre-discovery observation: **YES / SOURCE_WIRED**;
- provenance owner post-discovery observation: **YES / SOURCE_WIRED**;
- provenance owner final-emission observation: **YES / SOURCE_WIRED**;
- provenance owner schema: **try-forever-skill-provenance.v6**;
- regression source: **YES / UNEXECUTED**;
- atomic repository binding: **NO**;
- TESTED: **NO**;
- runtime UI / TalkBack: **NO**;
- deployed / callable / executed / delivered / accepted: **NO**.

## Ownership / firewall
No second provenance probe, watcher, repository daemon, scheduler, Phone Hands lane, or P0 owner may be created. Reuse the existing repository-observation organ and sole provenance owner. Phone/P0 consumption and mutation remain zero.
