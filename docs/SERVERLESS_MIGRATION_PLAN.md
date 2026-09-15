# Deferred migration: Lambda, Fargate, and Aurora PostgreSQL

Status: planning only. Written September 14, 2026.

The owner selected this direction after comparing an always-on `t3a.medium`, two serverless database options, and a smaller EC2 host with remote inference. Implementation and deployment are deferred to a future task. This document does not authorize resource creation, account conversion, cutover, or retirement of the current host.

The owner reports approximately $100 of AWS credit remaining. There is no immediate migration deadline. Keep improving and using the current deployment under its existing approvals. Before scheduling this work, check the actual credit balance, expiration, resource eligibility, and spend rate; this plan does not assume credits cover every proposed service or authorize unattended continuous operation. Do not create a reminder or monitoring automation merely because this migration is deferred.

The owner explicitly accepts discarding the current prototype data and starting over. Deploy with an empty database and fresh application-object namespace. Do not migrate existing photos, embeddings, bears, reviews, jobs, users or sessions. Recreate the intended organizations and invitations from configuration, and have users sign in again. This removes data-transfer and data-preserving rollback requirements; it does not instruct this planning task to delete anything.

## Decision and intended result

Move to Lambda for web/API execution, standalone ECS Fargate tasks for CPU inference, and Aurora Serverless v2 PostgreSQL for persistent application data. Retain private S3 storage, ECR images, Google sign-in, and the existing CloudFront hostname where practical.

This trades migration effort and occasional startup delays for reduced idle spending and managed database maintenance. PostgreSQL preserves the app's relationships and transactional behavior. DynamoDB migration, model replacement, GPU inference, and unrelated product changes are outside this plan.

Success means the application preserves intended behavior on a fresh library, its inference tasks exit when finished, and Aurora demonstrably pauses during inactivity. A cheaper estimate alone is insufficient evidence for cutover.

## Current implementation to preserve

Reinspect the current `main` revision when execution begins. Historical deployment notes and roadmap checkboxes can lag the code.

| Area | Current implementation | Migration consequence |
| --- | --- | --- |
| Hosting | CloudFront private EC2 origin, Caddy, FastAPI, PostgreSQL and workers on one host | Keep the distribution/hostname; change origins and release tooling deliberately |
| Persistence | SQLAlchemy, Alembic, foreign keys, uniqueness constraints and row locks | Preserve SQL transaction boundaries, deduplication, review/undo, and organization isolation |
| Jobs | PostgreSQL jobs/attempts, token fencing, leases and retry limits | Replace continuous claim polling with durable orchestration without weakening idempotency |
| Workers | HTTP protocol, separate detector/recognition images, short-lived model subprocesses | Reuse model adapters and provenance checks; add a bounded task entry point |
| Uploads | Up to 20 files, 25 MiB each; API hashes, decodes and orients images | Large bytes and expensive transforms must move outside ordinary API Gateway/Lambda requests |
| Images | API checks session/membership before returning private S3 bytes; cached derivatives | Preserve private access and define revocation behavior for any new delivery path |
| Matching | API reads compatible 512-dimensional embeddings and ranks them in Python | Preserve candidate ordering and organization/pipeline exclusions; bound/page database results |
| Deletion | Photo/bear deletion exists in current code, including job fencing and suggestion changes | Include deletion in parity tests; make object cleanup recoverable across partial failures |
| Idle behavior | Browser polls photos/details/matches every 2–5 seconds; SQLAlchemy pools connections | Stop needless polling and close connections so Aurora can pause |

Relevant source: [API and transactions](../backend/app/main.py), [models](../backend/app/models.py), [database sessions](../backend/app/db.py), [authentication](../backend/app/auth.py), [tenancy](../backend/app/tenancy.py), [matching](../backend/app/retrieval.py), [worker loop](../workers/worker.py), [frontend](../frontend/src/main.tsx), [CloudFront](../infra/cloudfront.tf), and [test coverage](../tests/README.md).

The existing `origin/codex/lightsail-experiment` report is useful sizing evidence, not an AWS benchmark: local 4 GiB probes passed; their peak memory INCLUDED a simulated 768 MiB service reserve. The 2 GiB recognition probe had only about 19 MiB margin. Neither result proves a whole production stack fits or predicts Fargate startup time. Keep the underlying report/results with the eventual migration evidence.

## Proposed target and design gates

```text
Browser -> existing CloudFront distribution
             |-- static frontend -> private S3 origin
             `-- /api/* and /auth/* -> API Gateway HTTP API -> Lambda
                                                               |-- Aurora PostgreSQL
                                                               |-- authorized S3 operations
                                                               `-- durable workflow
                                                                     |-- Fargate detection
                                                                     |-- Fargate recognition
                                                                     `-- result/failure persistence
```

The Aurora arrow denotes logical access: its network/driver implementation must pass Phase 1. Internal database and worker operations must not become unauthenticated browser routes.

### Database access without a standing NAT Gateway

Resolve this FIRST, before migrating the rest of the API. There are two candidates:

1. **Data API:** HTTP Lambda remains outside the VPC and accesses private Aurora over the AWS Data API. Preserve the PostgreSQL schema, but validate an appropriate driver/repository adapter against actual transactions. Do not assume this is a connection-string-only SQLAlchemy change. Check locking, savepoints, JSON, pagination, row sizes, transaction timeouts and migration tooling. The documented Data API response limit is 1 MiB, so existing unbounded collection/embedding reads need particular attention. [Data API limitations](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/data-api.limitations.html)
2. **Native PostgreSQL through a private Lambda:** keep psycopg/SQLAlchemy and execute complete database operations in a VPC Lambda. An outer HTTP Lambda handles Google OAuth, internet-facing operations, and invokes it through AWS APIs. Use typed application operations, not arbitrary SQL from the browser. Keep a whole transaction inside one invocation; do not split a locked transaction across remote calls. Design secret delivery and any S3 access without introducing an unnoticed collection of paid endpoints.

Prototype Data API first because it can keep the runtime topology smaller. If preserving correctness requires a large ORM rewrite, evaluate the native PostgreSQL alternative before choosing. Record one decision with working tests, network paths, dependencies and cost. Neither alternative exposes PostgreSQL publicly. Lambda placed in a public subnet does not acquire public internet access by itself. [Lambda VPC networking](https://docs.aws.amazon.com/lambda/latest/dg/configuration-vpc-internet.html)

### Aurora configuration

- One Aurora Standard Serverless v2 PostgreSQL writer in Ohio, on a currently supported engine version compatible with the application's SQL and auto-pause. Validate schema creation, extensions and collation on the fresh database; matching the old server's version is unnecessary.
- Initial proposal: minimum 0 ACUs, maximum 2 ACUs, five-minute auto-pause. Treat the maximum as a testable sizing limit, not a guarantee of low spend. Increase only with measured justification and an updated estimate.
- No RDS Proxy or deliberately warm connection pool. A closed SQLAlchemy session can return a connection to a pool rather than close the actual database connection; verify server-side connections disappear.
- Enable encrypted storage, deletion protection, automated backups and a tested restore. Proposed initial backup retention: seven days; record final retention and access policies before deployment.
- This budget includes one writer, not a second standby. Managed storage durability and restoration are distinct from having a ready compute failover target.
- Handle resume as a normal UI state with bounded retries. A first connection can take about 15 seconds, or 30 seconds or longer after a long pause. HTTP API integrations allow at most 30 seconds, so do not rely on one browser request waiting indefinitely. [Auto-pause](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2-auto-pause.html), [HTTP API quotas](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-quotas.html)

### Inference and durable orchestration

Use on-demand Linux/x86 Fargate, initially 2 vCPU/4 GiB per active model stage, default ephemeral storage, and pinned ECR image digests. Keep the existing model hashes, preprocessing, crop geometry, pipeline identifiers and embedding validation. Benchmark 1 vCPU later only if worthwhile. Avoid Spot initially so migration does not also introduce interruption handling as a new dependency.

Prefer Step Functions Standard for starting tasks, waiting for completion, bounding retries, and persisting final outcomes. Its ECS integration can wait for a task and report task-launch failures. An explicit worker exit/result contract is still necessary to distinguish model failure from successful processing. [Step Functions ECS integration](https://docs.aws.amazon.com/step-functions/latest/dg/connect-ecs.html)

Do not add SQS by default: Step Functions plus database job history may be sufficient for this volume. Add a queue only if measured dispatch/backpressure needs justify it, with clear ownership of retries and acknowledgements.

Requirements for the workflow:

- Assign stable operation/job IDs and return success only after work has been durably accepted. Prefer starting an idempotently named workflow whose first step creates/reserves the database job. If implementation instead commits a job and then dispatches it, use a durable outbox/recovery design; two independent writes can otherwise strand work.
- Cap admitted work and start with one active model task across the app. Concurrent workflows must enforce that cap through a recoverable shared admission/lease mechanism, not a local file lock or Lambda concurrency alone. Waiting must remain inexpensive and occur only while work exists.
- Preserve automatic detection-to-recognition and manual recognition/retry behavior. Retain job/attempt history and token-based rejection of stale results.
- Bound image pulls, model execution, workflow duration and retries. The current subprocess timeout is 1,500 seconds; validate appropriate stage and workflow deadlines rather than silently shortening allowed jobs.
- Write large intermediate/results data to attempt-specific S3 locations and pass references. Commit accepted results transactionally only after checking job token, organization, pipeline and deletion state. Clean up abandoned artifacts with bounded retention.
- A crash after a database commit, lost response, repeated launch, worker exit, or duplicate completion must not create duplicate observations, reviews, or inference jobs.
- Preserve manual recognition if automatic recognition is disabled. Deleted jobs/photos must never be resurrected by a late workflow.
- Reconcile failures through workflow retries/completion handling. Do not introduce an idle database poller that runs throughout the month.

For inexpensive Fargate egress, evaluate public-subnet tasks with temporary public IPv4 addresses and no inbound access. They receive scoped task roles for required objects/services. A task's public address does not make the database or image bucket public. Price any alternative private endpoints before adopting them.

### Web, uploads and privacy

- Keep Google invite-only login, organization switching, session revocation, CSRF, and tenant checks. Preserve the external origin/redirect hostname; verify CloudFront cookie, query-string, host-header and cache behavior with API Gateway.
- Serve static assets through a private S3 origin with CloudFront origin access control. Authenticated API responses must not enter a shared cache. API Gateway's direct hostname must enforce the same authentication boundary as CloudFront.
- Replace multipart uploads through the API with authorized staging uploads to private S3. Enforce per-file size/count, organization ownership, expiry and immutable upload identity; verify actual uploaded bytes/type/hash server-side before admission. Preserve exact-byte deduplication within an organization and protect finalized inputs against overwrite.
- Run orientation, crop generation and substantial image processing in bounded background work. Keep them out of database transactions and short HTTP requests. Unfinished staging uploads require a cleanup lifecycle.
- Preserve authenticated image access for previews. For large originals, select and test a suitable authenticated streaming/delivery path. If short-lived signed URLs are proposed, document that an issued URL can remain usable until expiry after membership revocation; accept that behavior explicitly before changing the current access contract.
- Poll only while work is pending or briefly during database resume; stop when complete and when the page is inactive. Passive health checks must not query Aurora. Health and readiness should distinguish application availability from database wake-up.
- Preserve real local CPU development and deterministic mock tests. Neither should require AWS or Aurora.

## Cost model to revalidate

September 14 planning rates, Ohio, before tax and promotional credits:

| Item | Basis |
| --- | --- |
| Fargate Linux/x86 | $0.04048/vCPU-hour + $0.004445/GiB-hour |
| Example 2 vCPU/4 GiB task | $0.09874/hour compute; approximately $0.10374/hour with one $0.005/hour public IPv4 |
| Aurora Standard v2 | $0.12/ACU-hour; $0.10/GB-month storage and $0.20/million I/O requests |
| Other services | S3, ECR, Lambda, API Gateway, workflow transitions, logs, secrets and backups; estimate from measured usage |

Sources: [Ohio Fargate catalog](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonECS/current/us-east-2/index.csv), [Ohio RDS catalog](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonRDS/current/us-east-2/index.csv), [Fargate billing](https://aws.amazon.com/fargate/pricing/), [Aurora pricing](https://aws.amazon.com/rds/aurora/pricing/), [VPC pricing](https://aws.amazon.com/vpc/pricing/).

Fargate task time includes image download/startup and retries, summed across every stage and task. At 100 photos/month and an ASSUMED ten total task-minutes per photo, the example task size costs about $1.73/month including task IPv4. This is not a measured inference runtime. At 1,000 photos the same assumption gives $17.29.

Aurora compute = awake hours × average ACUs while awake × $0.12. Thirty awake hours averaging 0.5–1 ACU cost $1.80–3.60. At 110 hours, cost is $6.60–13.20. Add idle timeout tails, workflow/database interactions and maintenance to the awake-time estimate. User inactivity does not prove database inactivity.

Provisional total: approximately $8–15/month for 100 example photos and 30 Aurora awake hours; approximately $13–25 at 110 awake hours with the same inference workload. These ranges must be rebuilt after choosing the database-access topology, retention and privacy delivery method. They assume small data/storage and no NAT Gateway, load balancer, standby DB instance, or provisioned Lambda concurrency. A NAT Gateway alone is roughly $33/month in hourly charges before IPv4/data processing. Earlier CloudFront allowances were reserves, not mandatory fees.

Compare against roughly $38–43/month for a complete `t3a.medium` deployment, not just its $27.45 compute charge. Stage overlap, migration tests, snapshots and temporary storage add one-time costs. Credits reduce near-term payment but do not establish the long-term economics.

## Execution phases for a future task

### Phase 0 — inventory and baseline

Recheck live release, account/credit eligibility, region, PostgreSQL/schema compatibility, intended organizations/invitations, and deletion behavior. Inventory the resources and object prefixes belonging to the disposable prototype so later cleanup has exact targets. Measure representative job timings, memory, API/image payload sizes and user-visible latency using disposable fixtures. No export, row-count reconciliation or backup of the old prototype is required.

Deliverable: exact starting state, baseline fixtures/metrics, fresh price estimate, and proposed staging budget. No migration scheduling should depend on an unverified historical credit-expiration date.

### Phase 1 — prove the difficult boundaries

Prototype and select the database-access option described above. Run representative transaction tests for match/undo, deduplication, concurrent recognition, tenant isolation and deletion. Test embedding reads beyond one Data API response page if that option is used. Confirm a fresh request after more than 24 hours of database pause can recover without logging the user out or duplicating a mutation.

Prototype one detector and recognition task using approved non-production inputs. Measure image-pull/model startup, memory, total cost and result handling. Test cold API behavior, upload admission and private image delivery. Establish any new RPC/payload limits before moving existing endpoints.

Deliverable: selected access/network design, measured task sizing, cold-start UX, and updated estimate. Stop redesigning if this becomes disproportionate to expected savings; record a comparison with retaining the EC2 option. Staging resources are created only under a separately agreed execution budget.

### Phase 2 — implementation and local parity

Implement bounded worker entry points and orchestration, persistence adapters/service boundaries, large-image upload/processing flow, idle-aware frontend behavior, and retryable object cleanup. Preserve stable-identity behavior, model outputs, review-history behavior and organization semantics for newly created records. Provide a repeatable empty-database migration/seed path; no data conversion from the prototype is needed.

Extend existing tests rather than replace them. Use a disposable PostgreSQL/Aurora database for locking evidence; SQLite or mocked AWS calls are insufficient for transaction and runtime guarantees. Preserve local development instructions and release-from-main checks.

Deliverable: reviewed code, passing local parity tests, immutable release artifacts, and infrastructure plans. Do not execute Alembic automatically on every Lambda cold start; use a controlled migration job.

### Phase 3 — isolated staging and acceptance

Provision a separate Aurora cluster and isolated application storage namespace/bucket, with scoped IAM roles and secrets. Prevent staging credentials from modifying the old deployment or dispatching its jobs. Use synthetic/approved fixtures; do not copy the prototype database.

Validate:

- Google login/logout, expiration, membership removal, cross-organization denial, CSRF and private images; no cached private response leaks.
- Upload limits/deduplication, no-head/multi-head photos, auto/manual recognition, failed/retried/duplicate tasks, invalid provenance, matching, correction, undo and deletion.
- Task launch failure, crash, timeout, lost callback, failure after DB commit, and deletion during inference/preview creation; no stranded accepted work or resurrected objects.
- Golden-image crop geometry, finite normalized embeddings and ranking parity within defined tolerances, using identical model hashes.
- Aurora pause/resume, no persistent idle connections, and no periodic workflow/health activity keeping it awake. Observe at least a 48-hour window containing a pause longer than 24 hours.
- Restore a staging database backup and reconcile object references; verify alerts, failure history, retention and deployment rollback.
- CloudFront routing, Lambda/API time and payload limits, actual task concurrency, minimum/maximum Aurora capacity and per-service spend.

Deliverable: acceptance report with measured costs and unresolved limitations. Prepare the final production Terraform diff, cutover runbook, rollback procedure and overlap/retention budget for owner approval. This is the deployment approval point, not a reason to leave preparatory implementation vague.

### Phase 4 — fresh deployment and traffic switch

Use a brief maintenance window. Data continuity and zero downtime are not requirements for this prototype.

1. Announce that the library will reset and users will sign in again. Stop new uploads/dispatch on the old app and cancel or drain its workers. Prevent old tasks and cleanup processes from writing into the new environment.
2. Initialize an empty Aurora database using reviewed migrations. Seed Internal Testing and McNeil plus the intended invitation configuration; do not copy historical user/session records. Verify both libraries are empty and isolated.
3. Configure fresh application storage and scoped runtime credentials. Reuse the verified model artifacts and pinned container images as appropriate; model files are dependencies, not disposable library data. Clear incompatible old browser sessions and OAuth cookies.
4. Change the existing CloudFront distribution's origins/behaviors to the new stack. Preserve its hostname and OAuth redirect, wait for propagation, and check login, organization switching and empty-library behavior.
5. Perform a disposable upload, recognition, review and deletion cycle, then begin the observation window. The old app stays inactive so requests during propagation cannot start an independent writable library.

Deliverable: a working fresh deployment, verified release commit, and switch-over evidence. No database export/import, historical S3 reconciliation, CDC, dual writes or reverse-data migration is needed. Schedule the maintenance window when executing; none is scheduled by this plan.

### Phase 5 — observe and retire

Retain the previous deployable application/configuration as a fallback. Keeping the old host stopped for a short trial, such as 48 hours, is optional; agree its overlap cost at cutover rather than defaulting to a week of retained infrastructure. Verify idle savings and successful user workflows before retiring it. Preserving the old database contents is unnecessary.

Retire resources in a separate reviewed change: old workers, obsolete ingress/origin dependencies, EC2, its disposable database disks, and the exact obsolete application-object prefixes/images. Existing permission to discard prototype data removes the need for an archival migration, but resource targets must still be resolved. Protect shared S3, ECR, CloudFront, model weights, and release artifacts needed by the new stack. Document what was removed and whether it is recoverable. Update README architecture, operating procedures and cost records to describe what is actually deployed.

## Rollback rules

For this prototype migration, rollback may also discard test data. Stop/fence new workflows and writes, restore a known-good deployment (on the retained EC2 host or a replacement), initialize an empty compatible database if necessary, reseed organizations/invitations, and restore CloudFront routing. Have users sign in again. Test this procedure with disposable fixtures in staging; no reverse-data migration is required.

Tell users when a reset occurs. If real field data starts being stored before execution or during the trial, revisit the reset assumption before cutover/rollback. The present acceptance of prototype data loss should not silently become a permanent production retention policy. Aurora backup/restore validation in Phase 3 is preparation for future use, not an obligation to preserve the current prototype.

## Handoff to the future implementation task

Start with this document and current `main`, then complete Phases 0 and 1 before committing to an access topology. Record approved staging spend, source/target database versions, selected connection method, privacy delivery behavior, admission/retry design, actual measurements and final retention decisions in this document as they are resolved.

The first concrete milestone is a tested Aurora access path and one complete bounded inference workflow. The owner has selected the architectural direction; this document records preparation for later execution and does not start that migration.
