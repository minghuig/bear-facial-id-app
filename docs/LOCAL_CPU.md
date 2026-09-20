# Local development with CPU inference

Local CPU inference is the canonical development environment. It runs on the local machine using Docker Desktop's Linux x86 containers. AWS remains available separately; the AWS-only regression command still requires AWS identity.

Put the four trusted checkpoint files in `.private/models/`, or pass an existing directory. Nothing under `.private/` is committed. The ReID file is the released `Public_release/checkpoints/reid_ckpts/katmai_exps/6y_model/net_best.pth`, named `katmai_6y_net_best.pth` locally and pinned to SHA-256 `6b9c43bb6f82d5a16c12a91258629e33656ad851a2626cc91baafbb82bea0cd3`. The verified download in this workspace is copied into `.private/models/` by `python3 scripts/package_artifacts.py`; a fresh workspace must obtain the exact member from the [authors' release](https://zenodo.org/records/17822054). The MegaDetector v4.1 body checkpoint is public and can be downloaded with a pinned SHA-256:

```sh
make body-model
```

The head, pose, and ReID checkpoints remain private prototype artifacts. Prepare the local settings:

```sh
python scripts/local_real.py --models /path/to/checkpoints
```

Then run from the repository (Compose 2.24.4 or newer):

```sh
make local
make frontend
```

The equivalent direct stack command is:

```sh
docker compose --env-file .env.local-real -f compose.yaml -f compose.local-real.yaml up -d --build
```

Open **http://localhost:5174**. The local API uses **127.0.0.1:18000**. PostgreSQL and MinIO use private project volumes; no AWS credentials, S3 calls, or cloud runtime are needed. Real workers share a lock and run one model job at a time. Docker needs enough memory for model loading; this machine's Docker allocation is checked during the smoke test.

### Try the owner-only member settings locally

Run `make members-local` and then `make frontend` from another terminal. Open **http://localhost:5174** or **http://127.0.0.1:5174** and select **Settings**. The first command enables `LOCAL_OWNER_SETTINGS=true` in the ignored `.env.local-real` and starts only the local API and its database/storage dependencies; detection and recognition workers are unnecessary for testing invitations. The local session acts as a test owner and can add or remove memberships in the local PostgreSQL volume. These changes never reach the hosted app. The explicit local switch is rejected when the API is configured for a public or nonlocal deployment. If Docker Desktop is stopped, start it first. `make stop` pauses the local services without deleting their data.

Use the same Compose flags with `logs --tail 50 api body-detector detector recognition` for diagnostics, or run `make stop` to pause the stack. Do not use `down -v` unless you intend to delete local data. Re-run the preparation command after adapter changes; it updates the pipeline while preserving existing local credentials. Checkpoint hashes are checked during preparation and again before each model loads.

Changing from the old five-year ReID model to the six-year model requires recomputing existing embeddings, not re-uploading photos. Stored original images and accepted head crops remain intact. While the API and workers are stopped (leave PostgreSQL and MinIO running), back up the local database and run `python -m app.reembed plan --org internal-testing` in the current API image. If the planned count matches the library, run `python -m app.reembed queue --org internal-testing --expected <planned old_complete>` in that image, then start the stack. The scoped queue preserves confirmed bear links and review history, uses saved crops, and refuses active jobs or an unexpected count. Wait for `python -m app.reembed verify --org internal-testing` to show zero pending/failed and no legacy completed embeddings before treating the new gallery as ready. Do not use this command to migrate an AWS library without a separate approved deployment window and backup.

Deterministic mock inference is retained only for automated full-stack checks. `make mock-smoke` starts its isolated stack on port 19000 and stops it after a successful run; do not use that stack for application development.
