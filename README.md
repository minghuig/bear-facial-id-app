# Only Bears

A shared photo library for identifying individual bears. Upload field photos, find bear heads automatically, and compare them with confirmed reference photos. People make the final identity decisions; model suggestions help with the review.

**[Open the app](https://d1u7h1fs60yvpr.cloudfront.net/)** · Invite-only Google sign-in · **[Roadmap](ROADMAP.md)**

## How it works

1. **Upload photos.** Select up to 20 JPEG or PNG files, up to 25 MiB each. Upload progress and per-photo results appear in the library.
2. **Find and compare bears.** Detection runs automatically, followed by recognition for eligible heads. Jobs run in the background while you review other photos.
3. **Review the suggestions.** Inspect each crop and its similarity-ranked matches. Confirm a bear, leave it unidentified, or exclude an unusable crop.
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

### Quick start with mock inference

Use this mode for UI and workflow development. It needs no AWS account, Google credentials, or model checkpoints. Mock results are synthetic and do not identify real bears.

Install Docker Desktop with Linux containers, Node.js 22.12+ and Python 3.12+. Start Docker, then run these commands from the repository root:

```sh
python scripts/local_init.py
docker compose up -d --build
```

Start the frontend in another terminal:

```sh
cd frontend
npm ci
npm run dev
```

Open **http://localhost:5173**. Use `python3` instead of `python` if that is your Python command. On systems with Make, `make local` and `make frontend` are equivalent shortcuts.

The setup creates a private `.env` if one is missing, applies database migrations, and starts the API, PostgreSQL, MinIO, and mock worker. The API binds to `127.0.0.1:8000`; database and object storage stay inside the Docker network.

```sh
docker compose logs -f api mock-worker
docker compose stop
# Resume without deleting the local library:
docker compose start
```

Avoid `docker compose down -v` unless you intend to erase the local database and photos. If startup fails, check `docker info` and make sure Docker Desktop has finished starting.

### Real inference on a local CPU

`main` supports real detection and recognition in Docker, with no AWS runtime dependency. It uses private model checkpoints, its own data volumes, frontend port **5174**, and API port **18000**.

Follow the [local CPU setup guide](docs/LOCAL_CPU.md). Checkpoints and private photos are not included in a clone. Local CPU mode uses the same application source as the hosted UI, with a separate local database and inference runtime.

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

Build the frontend with `cd frontend && npm ci && npm run build`. See the [backend test guide](tests/README.md) for PostgreSQL test setup. Use a disposable database; mock tests validate application behavior, not model accuracy.

Real bear test photos live in the ignored `.private/test-data/bear-photos/` directory, grouped by bear identity. They are local inputs, not part of the repository. See the [test photo documentation](tests/README.md) for layout and usage. `python scripts/smoke_local.py` provides synthetic workflow fixtures.

Before committing, stage only intended files, inspect `git diff --cached`, and run `bash scripts/audit_public.sh` where Bash and ripgrep are available.

## More detail

- [Architecture](docs/ARCHITECTURE.md)
- [Progress and historical implementation notes](docs/PROGRESS.md)
- [Original tracer-bullet plan](TRACER_BULLET_PLAN.md)
- [Model provenance and AWS validation](docs/INFERENCE.md) — describes the original AWS validation workflow; local CPU development is documented separately above.
- [Acknowledgements and research provenance](ACKNOWLEDGMENTS.md)
