# Local development with CPU inference

Local CPU inference is the canonical development environment. It runs on the local machine using Docker Desktop's Linux x86 containers. AWS remains available separately; the AWS-only regression command still requires AWS identity.

Put the three trusted checkpoint files in `.private/models/`, or pass an existing directory. Nothing under `.private/` is committed. Prepare the local settings:

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

Use the same Compose flags with `logs --tail 50 api detector recognition` for diagnostics, or run `make stop` to pause the stack. Do not use `down -v` unless you intend to delete local data. Re-run the preparation command after adapter changes; it updates the pipeline while preserving existing local credentials. Checkpoint hashes are checked during preparation and again before each model loads.

Deterministic mock inference is retained only for automated full-stack checks. `make mock-smoke` starts its isolated stack on port 19000 and stops it after a successful run; do not use that stack for application development.
