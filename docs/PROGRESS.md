# Only Bears progress

> Historical progress snapshot from September 13, 2026, not a current task list. The invite-only two-organization app, local real-CPU development, body-to-head pipeline, six-year model, comparison, and deletion were integrated later. Use the [README](../README.md) for current capabilities and the [roadmap](../ROADMAP.md) for next work.

At this snapshot, the next milestone was the [invite-only MVP](MVP_PLAN.md) for one shared organization and 3–5 Google users. Broad regression, recovery and reliability acceptance (including remaining BEAR-5/6 work) were deferred by the owner. Planning and independent review: BEAR-18.

Updated September 13, 2026 (Pacific). Scope: [tracer bullet](../TRACER_BULLET_PLAN.md).

| Ticket | Status |
|---|---|
| BEAR-1 | Done: Conductor onboarding |
| BEAR-2 | Done: local persistence and owner browser QA |
| BEAR-3 | Done: account, cost scope and provisioning approval |
| BEAR-4 | Done: authenticated AWS stack deployed |
| BEAR-5 | Pending: full 12-photo detector / 35-crop ReID regression |
| BEAR-6 | Pending: real workflow, restart/redeploy acceptance and measured costs |
| BEAR-8 | Local CPU branch running; p002 upload, detection and recognition pass |
| BEAR-9 | Done: PyTorch runtime, MPO uploads and upload progress fixes |

AWS runs m7i-flex.large (2 vCPU, 8 GiB) in Ohio within the approved $15 first-month / 20-running-hour trial. S3 is private and encrypted; the security group has no inbound rules. Access uses an authenticated SSM tunnel. PostgreSQL and workers share the EC2 instance.

The AWS-connected portal is localhost:5173. The independent local CPU portal is localhost:5174, on branch codex/local-cpu-inference with separate database/storage volumes. All three downloaded checkpoints passed SHA-256 verification. Local inference was explicitly authorized for this alternative and debugging.

AWS p002 and MPO p012 now detect one and two heads respectively. Recognition's missing vendor dependency reproduced locally; an optional Swin V2 import blocked the deployed Swin V1 model. The fix produces a valid 512-value embedding and passes full local p002 upload/detect/recognize. Recognition retries use the current model while preserving prior completed embeddings and detection provenance. Nineteen focused tests pass. Historical detection alerts are hidden once detection completes. Shared fixes are pushed and AWS release b4f5c70 is deployed; the p002 recognition retry is being verified.

The private prototype supplies 12 pilot originals/results and 35 field crops/embeddings. Input integrity checks passed; these and the p002 smoke test do not replace full regression or tracer acceptance.

Operational details: [AWS release](AWS_RELEASE.md), [approved cost scope](AWS_COST_PROPOSAL.md). Private outputs, Terraform state, checkpoints and validation data remain ignored.
