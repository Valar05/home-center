# Motion-to-Docs Scanner — Project State

Status date: 2026-08-13
State owner: Adam
Authority: Drew Clarke
Authoritative copy: repository root on `feature/motion-to-docs-scanner`

## Commission

Turn one Work Mode video upload into ordered, unique-frame contact sheets and place those contact sheets in one Google Document through the existing Home Center/Helm Center and Google Workflow lane.

## Locked boundaries

- Do not modify Spice of Life Cookbook beyond the separately approved recipe-upload branch.
- Use deterministic media processing; no generative AI is required for frame extraction or deduplication.
- Preserve exact decoded-frame mode and a useful perceptual-deduplication default.
- Keep the Google Document as the human-facing result. Preserve the manifest, contact-sheet JPEGs, and every unique PNG in a ZIP as evidence artifacts.
- Command Center is retired and is not an ingress or execution dependency.
- Reuse Home Center host-file ingress and Google Workflow rather than inventing a separate executable for email.

## Capability state

- Requested: yes.
- Implemented: scanner service, contact-sheet composer, unique-frame ZIP, manifest, Google Workflow, top-level Work Mode upload tool, contract updates, and deployment workflow.
- Locally tested: seven Python tests and three Node contract tests pass, including a real FFmpeg-generated MP4.
- Remotely tested: no. Two PR-run rounds failed before step zero. In the latest round all six repository workflows failed the same way, including unrelated workflows, with no executable step list or job log.
- Regnet QA: REVISE_REQUIRED until a remote CI execution and deployed runtime canary exist.
- Deployed: no.
- Callable from Work Mode video upload: no; `motion_to_docs_scan` is implemented on the branch, but the Home Center revision is not deployed.
- Delivered as a Google Document: no.
- Accepted: no.

## Sealed decisions

- `perceptual` is the default mode and uses a 256-bit difference hash with a default Hamming threshold of 6 and a BK-tree threshold search.
- `exact` hashes decoded RGB pixels with SHA-256 and collapses only pixel-identical frames.
- One source video produces one ordered Google Document containing all contact sheets.
- Source downloads fail closed to approved HTTPS upload-host suffixes and public IP resolutions; redirects are revalidated.
- The scanner caps source bytes and decoded frame count.

## Working set

- `services/motion-to-docs-scanner/service.py`
- `services/motion-to-docs-scanner/workflow.yaml`
- `services/motion-to-docs-scanner/test_service.py`
- `services/motion-to-docs-scanner/requirements.txt`
- `functions/motion_to_docs_service.js`
- `functions/home_center_mcp.js`
- `tools/motion_to_docs_contract_test.mjs`
- `contracts/home-center-top-level-mcp.v1.json`
- `contracts/home-center-public-tool-manifest.v1.json`
- `.github/workflows/test-motion-to-docs-scanner.yml`
- `.github/workflows/deploy-motion-to-docs-scanner.yml`

## Evidence

- Branch: `feature/motion-to-docs-scanner`
- Draft PR: https://github.com/Valar05/home-center/pull/289
- Current head before this state-only update: `6ae1786eb6346e5185e49421dac9f3ae640823e2`
- Local verification: seven Python tests and three Node contract tests passed.
- Latest failed workflow run set: Home Center CI `31749832748`, Venice Nerve Source `31749832736`, Motion-to-Docs `31749832746`, Cauldron `31749832745`, Android `31749832914`, and Venice Nerve Manifest `31749832722`.
- Every listed run failed before any workflow step and exposed no job log, so the exact repository Actions infrastructure cause remains unknown.

## Venice stop review

- Hard gate HG-06 forbids claiming public/live status without evidence.
- Hard gate HG-10 forbids improvising or escalating autonomously when worker evidence is missing.
- The Run Guide requires an executable minimum recovery action when an operator-only boundary remains; when no operator action can advance the lane, the commission remains active and resumes from the returned receipt.
- Ruling for this pass: hold at the deployment threshold. Do not merge, deploy, or claim completion until GitHub Actions can execute.

## Active gate and exact resume trigger

GitHub Actions must produce a real step-started run for PR 289 or an authorized equivalent deployment lane must become available. On that receipt, resume automatically at remote CI; then route through Regnet QA. After PASS: merge, deploy scanner/workflow and Home Center, invoke a synthetic-video Work Mode canary, read the Google Document back, and consult Venice again before calling the commission complete.
