# Current architecture

This describes the deployed EC2 app and the local development stack. The proposed Lambda/Fargate/Aurora replacement is documented separately in the [serverless migration plan](SERVERLESS_MIGRATION_PLAN.md); it has not been deployed.

## Hosted access and storage

The invite-only site enters through HTTPS CloudFront, then a private VPC origin on port 8080 to Caddy on the Ohio EC2 instance. Caddy serves the React app and proxies `/api/*` and `/auth/*` to FastAPI; it blocks internal worker routes, API documentation, and health checks from the public site. The security group permits port 8080 only from the CloudFront VPC-origin security group. The API also binds to host loopback for operator use through AWS Session Manager, not to a public API port.

Google sign-in creates revocable server-side sessions. Invited members can use the Internal Testing and/or McNeil organization, and requests are scoped to the selected organization. PostgreSQL persists users, memberships, sessions, photos, head observations, embeddings, bear identities, reviews, suggestion snapshots, and job history. Original photos and derived crops/previews stay in private S3; browser image requests pass through the authenticated API. The current release process backs up PostgreSQL and runs Alembic migrations without clearing the library. See [AWS operations](AWS_RELEASE.md) for the current release path.

## Photo-to-identity workflow

Upload hashes original bytes, stores the original and EXIF-oriented image, and rejects exact duplicates within an organization. A MegaDetector body job runs first; the API pads accepted body boxes and stores body crops. A separate detector finds heads in those crops. Each detected head starts in `pending` crop-review state. A person must accept a usable crop before recognition; rejected crops do not become references.

The CPU recognition worker uses the released six-year PoseSwin checkpoint to produce a normalized 512-dimensional embedding for each accepted crop. Retrieval compares only compatible embeddings in the same organization and excludes the query's original photo. The displayed value is raw cosine similarity between two head crops, **not an identity probability**. The top ten results are reference photos, so one bear can occupy multiple rows; a known-bear row also exposes its other confirmed photos. A person confirms, changes, or leaves an identity unresolved. Review history and gallery revisions support correction and prevent stale suggestions from silently becoming identities.

PostgreSQL jobs use row locks, leases, attempt tokens, and bounded retries so detection and recognition can continue independently of the browser. The API owns the database and crop geometry; model code runs in separate body, head, and recognition containers. See [inference provenance](INFERENCE.md) and the [similarity evaluation TODO](POSE_AND_SIMILARITY_TODO.md) for model and score details.

## Local and test environments

The supported local development path runs the real CPU workers with PostgreSQL and MinIO in Docker; see [local CPU setup](LOCAL_CPU.md). A separate mock stack exists only for deterministic tests. Neither environment needs the hosted Google sign-in or AWS credentials for ordinary local work.
