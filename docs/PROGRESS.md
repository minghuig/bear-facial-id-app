# Only Bears progress

Updated September 13, 2026 (Pacific). Scope: [tracer bullet](../TRACER_BULLET_PLAN.md).

| Ticket | Status |
|---|---|
| BEAR-1 | Done: Conductor onboarding |
| BEAR-2 | Done: local persisted pause, decisions, images and subsequent job survive restart; owner browser QA passed |
| BEAR-3 | Done: tools, account, plan, pricing and owner approval |
| BEAR-4 | In progress: AWS infrastructure created; committed application release building |
| BEAR-5 | Pending: real detector and ReID regression on AWS |
| BEAR-6 | Pending: real browser workflow, restart/redeploy acceptance and measured costs |

The user approved the $15 first-month / 20-running-hour trial, then selected m7i-flex.large (2 vCPU, 8 GiB) as the largest Free Plan eligible instance in Ohio. The account owner granted administrator access to the individual operator. The failed M6a launch created no EC2 instance; the continuation reused the same Terraform state and finished the remaining three resources.

Current infrastructure: private encrypted S3, empty inbound security-group rules, Session Manager online, encrypted 40 GiB root and 10 GiB database disks. Anonymous S3 object access and unsigned SSM forwarding both returned 403. First boot completed with Docker Compose 2.39.4. Application health and successful authenticated forwarding still require the release to finish.

Code checkpoint 5ac516c was pushed: Ohio/Free Plan instance, network bootstrap ordering, fail-closed writer stop, and checkpoint byte verification before builds. Four mocked remote-release cases and three hash tests pass. Models are never executed locally. The frontend simplification was separately committed as 3400b03.

All three checkpoints are uploaded to the private bucket. Their hashes must pass before building/using models. Private prototype bd687ec supplies 12 pilot originals/results and 35 field crops/embeddings. Local checks verified 47 image hashes, result image IDs/dimensions, and finite 35x512 embeddings with matching IDs. This is input integrity evidence, not model regression evidence.

Remaining: finish remote builds/migration/health checks; run AWS regression against the saved outputs; complete real workflow QA and persistence across restart/redeployment. Record runtime, memory and observed costs. No claim of tracer completion until those pass.

Operational details: [AWS release](AWS_RELEASE.md), [approved cost scope](AWS_COST_PROPOSAL.md). Private command outputs, Terraform state, model files and validation data remain ignored. Conductor updates should be brief decisions/blockers and evidence links only.
