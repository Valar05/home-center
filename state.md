# Motion-to-Docs Scanner — Project State

Status date: 2026-08-13
State owner: Adam
Authority: Drew Clarke
Authoritative copy: repository root on `feature/motion-to-docs-scanner`

## Commission

Turn one Work Mode video upload into ordered, unique-frame contact sheets and place those contact sheets in a Google Document through the existing Home Center/Helm Center and Google Workflow lane.

## Locked boundaries

- Do not modify Spice of Life Cookbook beyond the separately approved recipe-upload branch.
- Use deterministic media processing; no generative AI is required for frame extraction or deduplication.
- Preserve exact decoded-frame mode and a useful perceptual-deduplication default.
- Keep the Google Document as the human-facing result. Preserve the manifest, contact-sheet JPEGs, and every unique PNG in a ZIP as evidence artifacts.
- Command Center is retired and is not an ingress or execution dependency.
- Reuse Home Center host-file ingress and Google Workflow rather than inventing a separate executable for email.

## Capability state

- Requested: yes.
- Implemented: scanner service, contact-sheet composer, unique-frame ZIP, manifest, Google Workflow, deployment workflow.
- Tested: local unit and synthetic-MP4 pipeline tests pass; remote CI not yet observed.
- Deployed: no.
- Callable from Work Mode video upload: no; top-level `motion_to_docs_scan` tool wiring remains the active implementation gate.
- Delivered as a Google Document: no.
- Accepted: no.

## Sealed decisions

- `perceptual` is the default mode and uses a 256-bit difference hash with a default Hamming threshold of 6.
- `exact` hashes decoded RGB pixels with SHA-256 and collapses only pixel-identical frames.
- One source video produces one ordered Google Document containing all contact sheets.
- Source downloads fail closed to approved HTTPS upload-host suffixes and public IP resolutions; redirects are revalidated.
- The scanner caps source bytes and decoded frame count.

## Working set

- `services/motion-to-docs-scanner/service.py`
- `services/motion-to-docs-scanner/workflow.yaml`
- `services/motion-to-docs-scanner/test_service.py`
- `.github/workflows/deploy-motion-to-docs-scanner.yml`
- `.github/workflows/test-motion-to-docs-scanner.yml`
- `functions/host_file_ingress.js`
- `functions/home_center_mcp.js`
- `contracts/home-center-top-level-mcp.v1.json`

## Evidence

- Branch: `feature/motion-to-docs-scanner`
- Local test: six tests passed, including an FFmpeg-generated MP4 decoded into two unique frames and one contact sheet.
- Current hardening commits include `f6b548a14387b65f7406171e2a125f4ffb1231d4`, `9b4a5a9ac7af2ba9f7ac22acded8ab20da87857b`, `1d52fc58769a0bc0a364447ce34cfdef5e600eb1`, and `7f4ea01827df57d955b46bd7efc48be715d38845`.

## Active gate and next authorized action

Add and contract-test the first-class Work Mode file-bound tool that reuses Home Center host-file ingress, invokes the deployed Google Workflow with the uploaded video, and returns the observed Google Document link. Then obtain remote CI, Regnet QA, deployment, callable canary, Drive readback, and Venice stop judgment in that order.
