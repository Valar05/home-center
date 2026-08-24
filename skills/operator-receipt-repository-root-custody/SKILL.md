# Operator Receipt Repository Root Custody

## Purpose
Keep one operator receipt bound to the same repository root for machine-evidence production and bounded display projection.

A repository root is not merely presentation metadata. If raw evidence is audited from one tree and then projected relative to another tree, the receipt can misstate provenance even when every individual digest is deterministic.

## Core laws
`AUDIT ROOT != DISPLAY ROOT => RECEIPT CUSTODY WOUND`.

`repo_root OWNS audit root + display projection root`.

`CALLER-SUPPLIED SECOND root != AUTHORIZED OVERRIDE`.

`DEFAULT repo_root='.' PRESERVES patches/ DEFAULT BEHAVIOR`.

`SOURCE_WIRED != REGRESSION_EXECUTED != TESTED != RUNTIME != DEPLOYED != CALLABLE != DELIVERED != ACCEPTED`.

## Existing owner
`tools/try_forever_owner_surgery_descriptor_shadow_operator_receipt.py` remains the sole bounded descriptor-shadow operator receipt command.

It now derives raw audit custody as `repo_root / PATCH_ROOT` and feeds the same `repo_root` into the existing self-integrity/display chain. Bounded audit knobs/current-owner evidence may still pass through `audit_kwargs`; a second `root` argument fails closed before raw audit execution.

No second descriptor authority, receipt projector, backend, overlay controller, recovery daemon, or phone path is created.

## Regression source
`tools/test_try_forever_descriptor_shadow_operator_receipt_root_binding.py` is **SOURCE / UNEXECUTED**.

It pins:
- one `repo_root` reaching both machine-evidence custody and display projection;
- `repo_root / PATCH_ROOT` as the audit root;
- bounded audit arguments remaining composable;
- explicit second-root override rejection before audit work.

Do not call this TESTED merely because the source fixture exists.

## Current capability truth
- operator receipt repository-root custody: **YES / SOURCE_WIRED**;
- authenticated repository source readback: **YES**;
- regression source: **YES / UNEXECUTED**;
- regression execution: **NO**;
- TESTED: **NO**;
- runtime UI/TalkBack: **NO**;
- deployed/callable/executed/delivered/accepted: **NO**.

## Accessibility / evidence consequence
Repository-path display remains bounded and privacy-preserving through the existing projector. This skill changes evidence custody, not routine spoken prose or user-facing interaction topology.

## P0 / phone firewall
Consume no Phone Hands ticket, primary-phone command, P0 recovery queue, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination. P0 evidence remains read-only.
