RETIRED — HISTORICAL RECORD ONLY — DO NOT USE FOR AUTHORING

# Cloud Execution Retirement - 2026-07-27

This record preserves archaeology only. It is not an operation catalog or deployment guide.

Pre-repair resources observed on 2026-07-27 included private service `command-center-blender-render-00023-wnt`, task worker `commandcenterrenderworker-00002-luf`, queue `commandCenterRenderWorker`, and Foundry worker `foundryassetworker-00001-bip`. Repository truth removed the renderer service source, worker export, queue path, image build, deployment workflow, public tools, dynamic operations, tests, and active documentation. Command Center Codex worker discovery and its Cloud Run worker package were also removed.

Historical GCS outputs and terminal receipts are retained as owner-scoped evidence. Generic receipt delivery can verify and materialize their named bytes without exposing or invoking the retired producer.

After the Foundry V2 commit is merged to main and deployed, decommission must delete the renderer Cloud Function, task queue, Cloud Run service, and dedicated Artifact Registry image package. It must then prove no service, function, queue, job, or image remains. Buckets and historical objects are not deleted.

Rollback preserves the pre-deploy Home, Command Center, and Foundry revisions recorded immediately before release. It does not restore retired catalogs or execution resources.
