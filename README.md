# Only Bears

A shared photo library for identifying individual bears. Upload field photos, find bear heads automatically, and compare them with confirmed reference photos. People make the final identity decisions; model suggestions help with the review.

**[Open the app](https://d1u7h1fs60yvpr.cloudfront.net/)** · Invite-only Google sign-in · **[Roadmap](ROADMAP.md)**

## How it works

The body-to-head crop-curation flow below is implemented in the repository but is not yet released to the linked hosted app. The existing AWS deployment retains its previous head-only behavior until the separately reviewed infrastructure/model upload and release are completed.

1. **Upload photos.** Select up to 20 JPEG or PNG files, up to 25 MiB each. Upload progress and per-photo results appear in the library.
2. **Find bear heads.** The app detects whole animals, pads each body crop, then detects heads inside each crop.
3. **Curate and compare.** Approve usable head crops before recognition. Reject false or unusable crops; inspect similarity-ranked matches for accepted crops.
4. **Build the reference library.** Confirmed references help identify bears in later photos. Review history preserves corrections.

The library supports search, status and bear filters, and pagination. The **Bears** tab shows identities and their reference photos. A similarity score is a ranking aid, not a probability that an identification is correct.

## Research foundation and credits

Only Bears builds on the pose-aware brown-bear re-identification research of **Beth Rosenberg, Mu Zhou, Nathan Wolf, Mackenzie Weygandt Mathis, Bradley P. Harris, and Alexander Mathis**:

> Rosenberg, B., Zhou, M., Wolf, N., Weygandt Mathis, M., Harris, B. P., & Mathis, A. (2026). “[Individual identification of brown bears using pose-aware metric learning](https://doi.org/10.1016/j.cub.2025.12.022).” *Current Biology*, 36(3), 645–659.e14. [PubMed](https://pubmed.ncbi.nlm.nih.gov/41558480/).

The recognition worker includes adapted PoseSwin code from the Mathis Lab’s official [BrownBear_ReID repository](https://github.com/amathislab/BrownBear_ReID). We gratefully acknowledge the paper’s authors and the repository’s contributors for making this work available. See [Acknowledgements and research provenance](ACKNOWLEDGMENTS.md) for the pinned source revision, scope, and licensing notes.

## Shared access

Each person signs in with their own invited Google account. Members of an organization share its photos, bears, and reviews with equal access. The hosted app has two separate libraries: **Internal Testing** and **McNeil**. Members of both can switch organizations in the app.

This is an early hobby MVP. Photos and bear identities can be deleted, but backups and broader reliability testing are a later milestone. Do not treat the app as the only copy of original field photos.

## Run locally

Local CPU inference is the canonical development environment. Install Docker Desktop with Linux containers, Node.js 22.12+, and Python 3.12+. Put the four trusted model checkpoints in `.private/models/`. The public MegaDetector checkpoint can be installed with `make body-model`; the head and pose checkpoints come from the private prototype artifacts, while the ReID checkpoint is the authors' released `katmai_exps/6y_model/net_best.pth` (stored locally as `katmai_6y_net_best.pth`). Then start the stack:

```sh
make local
# Or use checkpoints stored elsewhere:
make local MODELS=/path/to/checkpoints
```

Start the frontend in another terminal:

```sh
make frontend
```

Open **http://localhost:5174**. Preparation verifies the checkpoints and creates private local settings while preserving existing credentials. The stack starts the API, PostgreSQL, MinIO, body detector, head detector, and recognition worker; the API binds to `127.0.0.1:18000`. Database and object storage remain inside Docker.

```sh
docker compose --env-file .env.local-real -f compose.yaml -f compose.local-real.yaml logs -f api body-detector detector recognition
make stop
```

Avoid `docker compose down -v` unless you intend to erase the local database and photos. Checkpoints and private photos are not included in a clone. See the [local CPU setup guide](docs/LOCAL_CPU.md) for direct Compose commands and troubleshooting.

## Hosted architecture

```text
Browser → CloudFront HTTPS → private VPC origin → Caddy
                                                   ├─ React frontend
                                                   └─ FastAPI → PostgreSQL
                                                        ├─ private S3 photos
                                                        └─ CPU detection / recognition workers
```

Caddy, the API, PostgreSQL, and inference workers share one EC2 instance in **us-east-2 (Ohio)**. The gateway blocks internal worker routes; application sessions protect photo access. Google handles sign-in, and application membership controls organization access.

The account implementation and local CPU tooling are merged into `main`. Deployments must use the current `main` commit; the release script rejects other revisions. See the [deployment notes](docs/MVP_IMPLEMENTATION.md) for the current infrastructure state; older tracer documents describe earlier deployment assumptions.

Deployment requires owner approval. Keep the AWS account on its approved Free Plan: running resources consume credits, and those credits are finite. Do not upgrade the account, resize infrastructure, or assume continuous hosting is approved. Never put credentials, Terraform state, checkpoints, or private photos in Git.

## Development and verification

| Area | Location |
| --- | --- |
| React / TypeScript frontend | [`frontend/`](frontend/) |
| FastAPI, database models, migrations | [`backend/`](backend/) |
| Detection and recognition workers | [`workers/`](workers/) |
| Terraform and deployment containers | [`infra/`](infra/) |
| Setup, packaging, release utilities | [`scripts/`](scripts/) |
| Tests and test-data instructions | [`tests/`](tests/) |

Build the frontend with `cd frontend && npm ci && npm run build`. See the [backend test guide](tests/README.md) for PostgreSQL test setup. Use a disposable database; deterministic tests validate application behavior, not model accuracy.

Real bear test photos live in the ignored `.private/test-data/bear-photos/` directory, grouped by bear identity. They are local inputs, not part of the repository. See the [test photo documentation](tests/README.md) for layout and usage. `make mock-smoke` temporarily starts the separately named test-only mock stack on port **19000**, exercises deterministic workflow fixtures, and stops it after a successful run. It is not a development environment.

Before committing, stage only intended files, inspect `git diff --cached`, and run `bash scripts/audit_public.sh` where Bash and ripgrep are available.

## More detail

- [Architecture](docs/ARCHITECTURE.md)
- [Deferred serverless migration plan](docs/SERVERLESS_MIGRATION_PLAN.md) — planned Lambda, Fargate, and Aurora PostgreSQL migration; not yet implemented.
- [Progress and historical implementation notes](docs/PROGRESS.md)
- [Original tracer-bullet plan](TRACER_BULLET_PLAN.md)
- [Model provenance and AWS validation](docs/INFERENCE.md) — describes the original AWS validation workflow; local CPU development is documented separately above.
- [Acknowledgements and research provenance](ACKNOWLEDGMENTS.md)
