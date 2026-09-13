# Only Bears progress and continuation handoff

Updated: 2026-09-13

Publication audit: the intended staged tree was simulated in a temporary Git repository. No real `.env`, `.private/`, model/checkpoint, photo, embedding, key, or credential-signature file was included; local filesystem paths were removed from public docs. `scripts/audit_public.sh` now provides the repeatable pre-commit gate. The target GitHub remote has not been configured or pushed from this session.

This is the handoff for continuing the tracer bullet in another Codex account. The controlling scope is [`TRACER_BULLET_PLAN.md`](../TRACER_BULLET_PLAN.md). The sibling `bear-id` prototype was read and remains separate and unmodified. No private prototype photos, labels, checkpoints, embeddings, credentials, or generated bundles are tracked in this repository.

## Current status

The new application scaffold and local mock workflow are implemented in `only-bears`. The real AWS deployment and real inference validation are still outstanding. No AWS resources have been provisioned, no paid benchmark has run, and no real model inference has run on the owner’s Mac.

The worktree currently contains the new application as uncommitted files in addition to the original plan commit. This session could write the progress file but could not write `.git/index` (`Operation not permitted`), so no commit was created here. Before handing the project to another account, review the diff and make a normal application commit. `.env`, `.private/`, model files, generated reports, and build output are ignored.

## Implemented

- FastAPI API under `/api` and authenticated worker endpoints under `/internal/jobs`.
- PostgreSQL models for batches, photos, jobs and attempts, detections, observations, embeddings, bears, reviews, gallery revision, and immutable suggestion snapshots.
- Original-byte SHA-256 deduplication; EXIF orientation normalization; private S3/MinIO originals, oriented images, and crops.
- Durable two-stage queue. Detection completes into `Awaiting head review`; it never creates a recognition job automatically. Recognition is enqueued only by the explicit **Run recognition** action and skips ignored/unusable heads.
- PostgreSQL row-lock claims with `SKIP LOCKED`, attempt tokens, leases, heartbeats, bounded retries, stale-result rejection, and idempotent repeated successful result submission.
- Exact cosine retrieval over finite L2-normalized 512-dimensional embeddings. Candidates are grouped by distinct bear, limited to five, and exclude same-photo/self, invalid, incompatible-pipeline, unconfirmed, ignored, and unusable references.
- Review history and correction behavior. Bear IDs survive display-name changes. Confirmed usable observations become references; no automatic bear creation or automatic confirmation exists.
- React/TypeScript/Vite frontend using Material UI and TanStack Query. It supports upload, numbered boxes and crops, explicit recognition, next/previous head review, candidate cards with supporting references, assignment/correction, named or unnamed bears, rename, history, retry, and reference viewing.
- Local deterministic mock worker using the real queue, storage, persistence, retrieval, review, and gallery paths. Fixture filename prefixes cover `multi`, `no-head`, `fail-detection`, `partial`, `different`, and `first`/`later` matching cases. Mock pipeline data is visibly marked and production configuration rejects mock mode.
- Real worker boundary without ML imports in the API. The detector and ReID adapters are separate. The ReID adapter preserves the verified prototype construction: separate HRNet pose model, Swin width 128, 512 output, original-plus-horizontal-flip aggregation, and L2 normalization. The detector uses the pinned legacy MMDetection environment. Each real job runs in a short-lived subprocess under a shared file lock so model memory is released between jobs and detector/recognition allocations do not overlap.
- The vendored source subset is pinned to BrownBear_ReID commit `4a9f5be8a57c7493096cab1b114dcd71489a3dbe`; `workers/vendor/NOTICE` and `SOURCE_HASHES.json` preserve provenance. Checkpoint SHA-256 verification is enforced before loading.
- Docker Compose services for PostgreSQL 16, MinIO, migration, API, and mock worker. MinIO uses the pinned official Quay image because the initial Docker Hub pull was rejected.
- Terraform and AWS release path for a restricted development host: x86 EC2, separate encrypted database EBS volume, private S3, immutable ECR tags, CloudWatch logs, no inbound security-group rules, and SSM port forwarding. `scripts/release.py` defaults to committed `main`, uses `git archive`, performs remote builds, migrations, health verification, and reports the deployed commit. `scripts/aws-stack.sh` separates plan/apply/tunnel/start/stop/log operations.
- AWS-only artifact packaging and validation scripts. `scripts/package_artifacts.py` hash-verifies an allowlist and copies private inputs to ignored `.private/`; `workers/validate.py` is designed to run detector and ReID regression checks on AWS and record timings, memory, versions, and failures.
- Resource and cost proposal in [`docs/AWS_COST_PROPOSAL.md`](AWS_COST_PROPOSAL.md): first-month request up to `$15 before tax`, with an estimated `$10.41`, capped at 20 EC2 running hours. It includes compute, IPv4, EBS, ECR, S3, requests, logs, and transfer, and documents charges that continue while compute is stopped.

## Validation completed

Evidence available at the handoff:

- `python3 scripts/smoke_local.py` passed the HTTP workflow against the local API, PostgreSQL, MinIO, and mock worker. It covered upload/storage, exact-byte deduplication, persisted detection pause, explicit recognition, later-photo retrieval, correction/history, immutable snapshots, unnamed-bear rename, no-head, automatic retry, and partial-failure retry. The private report is `.private/local-smoke.json` (run `85ade0d9`; 11 checks).
- `docker compose up -d --build` completed successfully after Docker Desktop was started. The last observed services were PostgreSQL healthy, MinIO up, API up on `127.0.0.1:8000`, and mock worker up.
- `cd frontend && npm run build` passed with Vite `7.3.6`. `npm audit` reported zero vulnerabilities after the Vite update.
- Focused tests reported by the test worker: 18 passed against a disposable PostgreSQL 15 instance. They cover pause persistence, no-head and multi-head cases, deduplication, retrieval exclusions, corrections, immutable snapshots, partial failures, leases, concurrency, worker auth, provenance, and pipeline separation. The tests use an in-memory object store and deterministic inference; they do not prove MinIO restart behavior, AWS deployment, or model correctness. See [`tests/README.md`](../tests/README.md).
- Private artifact packaging reported 54 allowlisted files copied and hash-verified. No model was executed locally.

## Not complete yet

The following are required before claiming tracer-bullet completion:

1. Install or make available Terraform >= 1.6, AWS CLI v2, and the AWS Session Manager plugin. Run `aws sts get-caller-identity` and confirm the intended account and region.
2. Review [`docs/AWS_COST_PROPOSAL.md`](AWS_COST_PROPOSAL.md). Obtain explicit owner approval for the exact `$15` / 20-running-hour scope before any `terraform apply`, model upload, benchmark, or paid provisioning. Existing AWS access is not approval of this proposal.
3. Run `bash scripts/aws-stack.sh plan`, inspect the saved Terraform plan, then apply only after approval. Resolve any provider or account-specific validation errors before provisioning.
4. Run `python3 scripts/upload-models.py --approved-spend`; it must upload only the three trusted checkpoints from the sibling prototype. Do not copy labels or photos as part of this step.
5. Run `python3 scripts/release.py --approved-spend` (or pass an explicit committed ref). Keep the local frontend and use `bash scripts/aws-stack.sh tunnel` to reach the API through SSM. Do not expose port 8000 or put worker credentials in the browser.
6. Run `workers/validate.py` on AWS and compare all 12 detector pilot outputs and 35 saved ReID embeddings against the prototype evidence at the plan’s thresholds. Record actual AWS runtime, RSS/cgroup memory, failures, and image/dependency versions.
7. Execute the real deployed acceptance checklist in section C of the controlling plan: close/reopen during the persisted pause, restart/redeploy the backend, run real recognition only after the explicit action, confirm a reference participates in later-photo suggestions, exercise corrections and renaming, and verify partial failures/retries and exclusion rules.
8. Record the real workflow results and observed ongoing cost. Keep the completion statement limited to what the AWS path actually proved; mock tests alone are not completion.

## Known environment notes

Docker was initially reported as unavailable because the desktop GUI launch returned a macOS error. `docker desktop start` then succeeded outside the sandbox, and the Docker engine reported version `28.3.3`. No reinstall is currently indicated. If it fails in a normal terminal, run `docker desktop start`, wait for `docker info` to succeed, and retry `make local`.

The Codex sandbox could not bind the Vite dev server (`listen EPERM` on `127.0.0.1:5173`). This is a sandbox restriction observed from Codex, not evidence that Vite fails in the owner’s terminal. Run `cd frontend && npm ci && npm run dev` in a normal local terminal if needed.

The AWS agent could not finish Terraform installation/validation after its usage limit was reached. Terraform syntax and provider validation therefore remain an explicit next step. The real worker adapters were statically checked against the verified prototype wiring, but neither container has been built or executed on AWS.

## Resume commands

```sh
cd only-bears
git status --short
python3 scripts/local_init.py
docker desktop start                 # if needed
docker info
docker compose up -d --build
.venv/bin/python scripts/smoke_local.py
cd frontend && npm ci && npm run build
cd ..
.venv/bin/pytest -q tests             # uses TEST_DATABASE_URL when supplied
python3 scripts/package_artifacts.py
python3 scripts/pipeline.py           # prints the content-derived real pipeline namespace
git add . && git commit -m "Implement Only Bears tracer bullet scaffold"
```

If the commit command is run from the restricted Codex session and reports `.git/index.lock: Operation not permitted`, run the same command in the owner’s normal terminal or in the next account. Review `git status --short` before committing so ignored private files are not added.

For AWS, read [`docs/AWS_RELEASE.md`](AWS_RELEASE.md) in full and follow its approval gate. The release command is intentionally manual and can later be called from GitHub Actions; automatic deployment on merge is out of scope.
