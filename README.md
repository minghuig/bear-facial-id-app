# Only Bears

A shared bear identification tracer: upload → detect heads → **persisted pause** → explicitly recognize → review identities → match later photos against confirmed references.

The controlling scope is [TRACER_BULLET_PLAN.md](TRACER_BULLET_PLAN.md). Real AWS inference is required to finish the milestone. Local mock success alone is not completion. The sibling `bear-id` prototype and its private labels remain untouched.

## Local workflow

Prerequisites: Docker Desktop running, Node 22.12+ and Python 3.12+. No local ML installation is required or allowed.

```sh
cd only-bears
make local
make frontend
```

Open http://localhost:5173. The API listens only on 127.0.0.1:8000. PostgreSQL and MinIO remain on the Compose network. `make local` creates a private `.env` once, runs migrations, and starts API and mock worker. `docker compose logs -f api mock-worker` shows progress. `docker compose stop` preserves all data; `docker compose start` resumes services. Do not use `down -v` unless intentionally deleting the local collection.

Use the generated synthetic fixtures (`python3 scripts/smoke_local.py`) for multiple-head, empty-gallery, no-head, failure/retry, confirmed-reference and later-match checks. The mock banner and pipeline are intentional. Use `first.png` and a different-byte `later.png` for matching; identical bytes deduplicate even if filenames differ.

If Docker cannot start, first run `docker desktop start`, then `docker info`. In Codex, Docker commands need permission outside the filesystem sandbox; a sandbox launch error does not establish a broken installation. If those commands fail in your own terminal, open Docker Desktop and complete its setup prompts, then repeat `docker info` and `make local`.

## Verification and AWS

Focused tests live under `tests/`; PostgreSQL concurrency tests require a disposable database. The full Compose smoke test uses actual HTTP, PostgreSQL, MinIO and mock workers. Frontend build: `cd frontend && npm ci && npm run build`.

Before the first public commit, stage the intended files and run `bash scripts/audit_public.sh`. It rejects real `.env` files, private/generated artifact paths, model files, common credential signatures, personal local paths, and whitespace errors. Review `git diff --cached` yourself after it passes. The local MinIO values in `.env.example` and Compose are development-only placeholders and must never be reused for AWS.

See [architecture](docs/ARCHITECTURE.md), [inference packaging](docs/INFERENCE.md), [AWS proposal](docs/AWS_COST_PROPOSAL.md) and [progress](docs/PROGRESS.md). Infrastructure provisioning and app releases are separate operations. Spending approval and AWS access are required before paid work; no AWS resource has been provisioned by this implementation yet.
