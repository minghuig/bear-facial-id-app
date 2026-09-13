# Only Bears — tracer bullet implementation handoff

Updated: 2026-09-13

Status: agreed product scope and implementation direction. Application implementation and AWS provisioning have not started. This document is intended to be given directly to an implementation agent.

## 1. Objective and authority

Build a small, persistent bear-identification application around the existing BrownBear_ReID prototype. Prove this complete workflow:

**Upload photos → detect heads → pause for review → explicitly run recognition → review candidates → confirm or correct an identity → match a later photo against confirmed references.**

The tracer bullet must run against a real AWS backend with real detection and recognition. A working local mock is an intermediate checkpoint, not completion. The frontend may continue running locally while using AWS.

This document records the owner's decisions from the application-scoping conversation. For tracer bullet scope, those decisions supersede the broader implementation sequence and requirements in the earlier Bear ID documents. Use the earlier documents for technical evidence and implementation references, not to silently expand this milestone.

- Product background: sibling prototype `bear-id/APP_SPEC.md` (outside this repository)
- Detailed previous plan and verified model setup: sibling prototype `bear-id/PROJECT_PLAN.md`
- Historical experiments: sibling prototype `bear-id/PROJECT_NOTES.md`
- Proposed new application directory: this repository (`only-bears`)

At handoff, `only-bears` was empty and was not a Git repository. Use it for the new application; treat `bear-id` as the source of prototype code, evidence, and private local artifacts. Preserve the prototype directory. This repository placement is an implementation assumption based on the current workspace, not a request to move or delete the prototype.

Do not repeat the completed Colab experiments, require user-operated notebooks, retrain the models, or download the full research release. Do extract and validate reusable inference code.

## 2. Product terms and shared data

- **Photo:** one uploaded original image. A batch may contain unrelated photos and bears.
- **Detected head / observation:** one detected head and its bounding box and crop, created before recognition. One photo may have zero, one, or multiple observations. Prefer “detected head” in the UI.
- **Embedding:** the numerical representation recognition produces for a head crop, used to compare it with reference photos.
- **Suggestion:** ranked candidate bears and supporting reference images for one observation. It is not a confirmed identity.
- **Review:** a person's saved decision about one observation.
- **Bear:** a stable identity record with an editable display name, including an unnamed identity.
- **Reference gallery:** usable, human-confirmed observations eligible for future matching.

All data belongs to **one shared collection**. Do not partition photos or bears into personal user galleries. Future individual logins could grant access to this shared collection; shared data does not require shared login credentials.

Accounts, Google sign-in, invitations, roles, and user-management screens are out of scope. Keep review history, but do not invent individual reviewer attribution when there is no authentication.

## 3. User workflow

### Upload and detection

1. Upload JPEG/PNG photos, individually or as a small batch.
2. Store originals persistently and enqueue detection in the backend.
3. Save detected boxes and head crops per photo.
4. Stop at **Awaiting head review**. Detection completion must not automatically enqueue recognition.

Detailed progress displays, per-file progress bars, and elaborate live progress updates are not required. Basic states, errors, and a way to retry are required. Work must continue independently of an open browser.

Show “No head detected” for a successful detection run with no usable heads. Do not claim that the photo contains no bear.

### Explicit pause before recognition

Show the original photo with numbered boxes and the associated crops. Provide an explicit **Run recognition** action. The pause must survive closing the browser and restarting the backend.

Implementation default: let the reviewer ignore cubs or mark unusable crops, then run recognition on the remaining eligible heads. The owner explicitly requested the pause; the exact selection controls were not separately finalized. Use this simple default without adding a crop editor or another approval stage.

Detection does not determine which subjects are cubs. Ignoring cubs is a review decision. Do not automatically apply an identity to every head or every photo in a batch.

### Recognition and review

Recognition is a separate queued job. It computes embeddings for eligible heads and compares them with the confirmed gallery. Show up to five distinct candidate bears, each with a name and supporting reference image.

Allow the reviewer to:

- Confirm a suggested bear or choose another existing bear.
- Create a named or unnamed bear and assign the observation to it.
- Leave the observation unresolved.
- Ignore a subject or mark its crop unusable.
- Correct an earlier identity assignment.

Persist decisions immediately. Provide simple next/previous navigation through heads. A basic bear list and confirmed-reference view are sufficient; a full administration interface is not required. Support changing an unnamed bear's display name without changing its ID or memberships.

Start with an empty gallery. Explain that confirming identities creates references for later matching. An empty or weak candidate list must not automatically create a bear or establish that the subject is a new individual. “Unknown” is not one shared bear identity.

## 4. Architecture and stack

Use the same application code and job contracts in both environments:

| Component | Local development | AWS tracer bullet |
| --- | --- | --- |
| Frontend | React, TypeScript, Vite, Material UI | Same local frontend configured to call AWS |
| API | Local FastAPI server | Containerized FastAPI in AWS |
| Database | Local PostgreSQL | Persistent PostgreSQL in AWS |
| Object storage | MinIO or equivalent local S3-compatible service | Private S3 |
| Detection | Mock worker | Real head detector |
| Recognition | Mock worker | Real pose/ReID inference |
| Retrieval and reviews | Real application logic | Same application logic |

Additional stack choices:

- Pydantic for API and worker payloads; SQLAlchemy and Alembic for the database.
- TanStack Query for frontend server state; minimal additional dependencies.
- PostgreSQL job table as the durable queue. No dedicated queue service or vector database is required.
- Docker Compose for local API, PostgreSQL, object storage, and mock worker services.
- Docker containers for deployment; separate detector and recognition dependencies.
- Terraform for AWS infrastructure.
- AWS container registry and logs; bounded retries, worker concurrency, and job timeouts.

Keep ML imports out of the web/API process. Workers obtain work and report results through an internal API rather than coupling model code directly to database access. Use the existing plan's worker boundary as a starting point, modified for the explicit detection/recognition split.

The proposed AWS starting point is EC2 for the API and PostgreSQL. The placement of the inference containers—on the same instance or separately on demand—is still a hosting decision. Do not commit to an instance size, always-on GPU, Fargate configuration, or cost estimate without checking requirements and current costs.

There is **no local real-inference requirement**. Do not install or run the ML stack on the owner's Mac, including through emulated Docker. This supersedes the previous plan's local CPU/emulation benchmark sequence. Local API, database, storage, mock-worker execution, and container build tooling are allowed. If building ML images locally is impractical, choose a suitable remote build path and include its cost in the proposal.

## 5. Local mocks and real worker contract

Mocks must exercise the real upload, storage, queue, result persistence, retrieval, review, and gallery logic. Do not implement a disconnected frontend demo or hard-code the final candidate cards.

Define distinct detection and recognition interfaces:

- Detection input: photo identity, original storage location, pipeline version, and job/attempt identity. Output: oriented image dimensions, all detector boxes/scores, accepted head crops, provenance, and success or failure.
- Recognition input: selected observation IDs and crop locations, pipeline version, and job/attempt identity. Output: valid embeddings and diagnostics or per-observation failures. The application computes and persists candidate suggestions using the real retrieval code.

Use deterministic fixtures for known photos, boxes, and embeddings. Existing pilot outputs can supply realistic examples. Include fixture cases for multiple heads, no detections, a failed stage, and a later photo that retrieves a previously confirmed bear.

Mark mock execution visibly and in stored provenance. Use a separate mock pipeline namespace and environment; mock observations must never become references for real inference. Production AWS configuration must reject accidental mock mode.

Keep the stage contracts stable so changing the inference adapter does not require rewriting the UI or review logic. Mock inference is intended to make routine local testing cheap and predictable.

## 6. State, retrieval, and reliability

Persist at least: batches and photos, stage jobs and attempts, detections, observations/crops, embeddings, bears, suggestions, and review history. Use stable IDs independent of bear names.

Track detection, recognition, and review states separately. One giant batch-status field must not obscure a paused head review or partial recognition failure. Basic user-facing states can include Detecting, Awaiting head review, Recognizing, Ready for identity review, and Failed.

- Normalize EXIF orientation before detection; keep boxes in the oriented image's coordinate system and display them against that orientation.
- Use original-byte hashes for exact-photo deduplication.
- Persist results as work completes; isolate failures so one bad photo or crop does not discard unrelated results.
- Make job claims, retries, and result submission idempotent. Recover interrupted jobs with leases/heartbeats or an equivalent small durable mechanism.
- A worker restart must not bypass the detection pause or duplicate observations.
- Corrections must change effective gallery membership while preserving review history.
- Store immutable suggestion snapshots with pipeline version, gallery revision/time, candidate scores, and reference IDs. Explicit refresh may produce a new snapshot; confirmations must not silently rewrite old suggestions.

Use finite, nonzero, L2-normalized 512-dimensional embeddings and exact cosine comparisons. Rank distinct bears by their best eligible reference match as the initial baseline. Exclude the query observation, all references from the same original photo, invalid embeddings, incompatible pipeline versions, and ignored/unusable/unconfirmed observations.

Human-confirmed usable observations enter the reference gallery by default. A correction, ignored status, or unusable status must update that eligibility. Imported expected labels and model predictions must never silently become human confirmations.

Ranked reference cards are sufficient. If numerical similarity is displayed, label it as cosine similarity, not probability or identity confidence. Do not stretch each query's best result to a full bar or normalize candidates to percentages. Bears with more references may be favored by the baseline.

## 7. Existing ML evidence and artifacts

Reuse research source commit `4a9f5be8a57c7493096cab1b114dcd71489a3dbe` from BrownBear_ReID. Package a durable pinned source subset with provenance rather than depending on temporary inspection checkouts.

The following facts are established by the prototype:

- The pose/ReID construction reproduced a released sample embedding in Colab and generated valid embeddings for 35 recent manually cropped heads.
- The head detector loaded strictly and processed 12 original pilot photos on Colab CPU, producing 15 displayed heads.
- Automatic detection crops have not yet been connected to recognition in a packaged end-to-end service.
- Model execution is verified; reliable identification on recent photos is not. Recent matching has been inconsistent.

Useful implementation inputs under the sibling `bear-id/` prototype:

| Input | Relative path |
| --- | --- |
| Tested ReID construction and preprocessing | `scripts/build_inference_notebook.py`, `notebooks/02_one_image_inference.ipynb` |
| Field inference and saved embeddings | `scripts/colab_field_test.py`, `field_review_inputs/field_embeddings.npz` |
| Head detector runner and dependency setup | `scripts/run_head_detector_pilot.py`, `scripts/colab_head_pilot.py` |
| Detector configuration | `artifacts/detectors/released_head_config.py` |
| Pilot originals and results | `artifacts/detector_pilot/`, `artifacts/detector_pilot_results/output/` |
| 35 field crops | `artifacts/field_photo_test_v1/crops/` |
| Checkpoints | `artifacts/test_on_2020_net_60.pth`, `artifacts/hrnet_w48_balanced_n13_refined.pth`, `artifacts/detectors/bear_head_detector_latest.pth` |

Consult the previous plan's §2 for exact hashes, model wiring, dependency pins, and reference comparisons. Preserve the separate pose model, backbone width 128, output embedding dimension 512, and original-plus-horizontal-flip aggregation followed by L2 normalization. The training classifier's 102 classes are not the application's bear registry.

Initial preprocessing is head detection directly on oriented originals, threshold 0.5, clipped floor/ceil crops, no added margin. This differs from the research's body-then-head pipeline and must be documented. Body detection is deferred.

The detector's tested legacy Python/MMDetection environment and ReID's newer environment differ. Preserve compatible isolated environments; do not silently port weights or force both into an unverified dependency set. Reproduce saved outputs narrowly when extracting the runners, using AWS for actual inference. Do not turn validation into another owner-operated notebook exercise.

Never commit private photos, model checkpoints, archives, generated embeddings, credentials, or build bundles containing them. Verify trusted checkpoint hashes when packaging/loading. Preserve upstream attribution and record unresolved licensing questions from the previous plan before any future staff rollout; that work does not expand this tracer bullet into account onboarding.

## 8. AWS access, budget, and deployment

The previous plan records an all-in target **below $20/month**. That is a target, not a verified hosting quote. Before paid provisioning or benchmarks, prepare a concise resource/cost proposal covering compute, storage, container images, networking, logs, startup overhead, and what continues billing while compute is stopped. Obtain the owner's approval of the concrete spending scope. Existing agreement to use AWS is not approval of an unspecified paid configuration.

Prepare code, Dockerfiles, Terraform, and deployment scripts before this decision so the proposal is concrete. Ask only for access, spending, or other choices that actually block the next step. Do not re-ask resolved product questions.

No application accounts does not mean an anonymously writable public backend. Select a restricted development access mechanism, such as a private tunnel, and document how the local frontend reaches the API. Keep worker credentials separate from frontend access, S3 private, and object URLs short-lived. Keep secrets out of source control and browser bundles. Scope CORS to the configured local frontend. Access setup must not grow into a login product.

Provide two separate repeatable operations:

1. **Provision/update infrastructure:** Terraform with documented configuration and state handling.
2. **Deploy an application release:** a manually runnable script or Make target that builds and publishes versioned images, performs database migrations safely, updates API/workers, checks health, and reports the deployed commit.

Deployment should default to a committed version of `main` and allow an explicit commit/ref. Resolve and record the exact commit being deployed; do not silently ship an uncommitted working tree. Keep persistent storage independent of container replacement. Document application rollback and migration limitations.

Use the same deployment entry point later from GitHub Actions, either by manual trigger or after merges to `main`. Automatic deployment on merge is **not required** for this milestone. Do not make a full CI/CD system a prerequisite for the first AWS release. The manual path must be easy and documented, including prerequisites, first deployment, subsequent deployment, logs, and stop/start behavior.

## 9. Scope boundaries

Included: the complete workflow in §3, local mock development, real AWS backend and inference, Material UI, shared collection, simple bear/reference viewing, basic errors/retries, durable jobs and reviews, Terraform, repeatable manual deployment, and verification across restart/redeploy.

Deferred:

- Accounts, Google OIDC, invitations, roles, and per-user galleries.
- Multiple collections or organizations.
- Hosted frontend, polished mobile experience, and detailed progress UI.
- Bulk Google Takeout import, Google Photos integration, and full evaluation reports.
- Bear merging, advanced gallery administration, and unresolved-to-unresolved search.
- Crop editing, manual crop annotation workflows, and body detection.
- RAW/HEIC/video support, retraining, fine-tuning, or model conversion.
- Automatic deployment on merge and extensive infrastructure/CI sophistication.

Use a handful of existing photos for the first real workflow. Do not make importing or labeling the entire August 19 collection a prerequisite. Recognition quality is an outcome to assess through the application, not a promised acceptance threshold.

## 10. Implementation checkpoints and acceptance

### A. Persistent local workflow with mocks

Scaffold the application, local services, schemas, stage interfaces, and minimal Material UI screens. Demonstrate upload → mocked detection → persisted pause → explicit mocked recognition → real retrieval/review logic → later matching from confirmed references. Include empty-gallery, no-head, multiple-head, and failure/retry cases. Restart local services and verify saved state.

### B. Concrete AWS deployment path

Prepare infrastructure and release tooling, select a restricted access path, and produce the resource/cost proposal. After approval and access are available, provision AWS, package the existing models, validate extracted inference against saved prototype evidence, and measure enough runtime/memory behavior to settle worker placement. Measurements from Mac emulation are neither required nor substitutes for AWS measurements.

### C. Real AWS tracer bullet

Using the local frontend and AWS services, verify:

1. Upload unrelated photos; originals survive closing the browser.
2. Real detection produces saved boxes/crops, including independent observations for multiple heads.
3. Processing stops before recognition and remains paused across reopening and backend restart.
4. An explicit action runs real recognition only for eligible heads.
5. Empty galleries work; confirmed identities become references.
6. A different photo produces real candidate suggestions drawn from eligible references. Correct ranking is not guaranteed, but the confirmed reference must participate when eligible.
7. Assignment corrections and unnamed-bear renaming preserve IDs/history and update effective gallery membership.
8. No-head outcomes, invalid embeddings, partial failures, and retries remain understandable and do not duplicate successful work.
9. Self/same-photo matches, incompatible model versions, and mock references are excluded.
10. Restart or redeploy the backend and verify photos, paused work, suggestions, and review decisions remain available. Run another job successfully afterward.
11. Run the documented deployment command and identify the exact deployed commit. Document how to inspect logs and stop/start compute.

Write focused tests for state transitions, retrieval eligibility, corrections, retry/idempotency, and persistence. Verify the real deployed path separately from mock tests. Avoid exhaustive low-impact display tests. Report what was actually tested, remaining limitations, observed resource usage, and ongoing costs.

## 11. Prompt for the implementation agent

> Implement the tracer bullet described in `TRACER_BULLET_PLAN.md`. Read it first and use it as the controlling scope. Build the new application in `only-bears`, reusing verified prototype code and private artifacts from the sibling `bear-id` directory without modifying or relocating that prototype. Support a full local API/database/storage stack with mocked detection and recognition; do not run real inference on the owner's Mac. Include real AWS deployment and inference as required completion work, with a persisted explicit pause between detection and recognition. Use React/TypeScript and Material UI, FastAPI, PostgreSQL, S3-compatible storage, Docker, and Terraform. Implement one shared collection without accounts. Provide an easy manual release command defaulting to a committed `main` version, suitable for later reuse in GitHub Actions. Prepare a concrete resource/cost proposal before paid provisioning or benchmarks. Work autonomously on reversible implementation decisions, preserve private artifacts and existing labels, keep a short progress record, and validate both the local mock workflow and the deployed real workflow. Do not claim completion based on mocked inference alone.
