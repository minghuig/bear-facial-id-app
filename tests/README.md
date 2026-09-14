# Backend validation

Install only the API dependencies (no local inference stack):

```sh
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
TEST_DATABASE_URL='postgresql+psycopg://bears:bears@127.0.0.1:5432/bears' .venv/bin/pytest -q tests
```

Use the database URL/port appropriate to your local stack. Each API test creates and removes a uniquely named PostgreSQL schema; the database role needs schema creation privileges. Never point tests at production. Without `TEST_DATABASE_URL`, PostgreSQL API tests are skipped explicitly; the retrieval and settings tests still run. SQLite is used only for retrieval filtering, never as evidence of queue locking correctness.

Coverage includes automatic and manual recognition modes, photo and bear deletion, no-head and multi-head outcomes, exact-byte deduplication, empty gallery, later-photo matching, correction and rename history, immutable suggestions, exclusions, finite normalized embedding checks, partial failures, bounded retry, stale tokens, heartbeat limits, duplicate result delivery, concurrent claims and recognition requests, worker credentials and pipeline separation.

The API integration tests substitute an in-memory object store and deterministic inference results. They test real PostgreSQL transactions and application logic, but **do not** establish Docker/MinIO integration, process restart survival, AWS deployment, or real model correctness. Those require the separate end-to-end acceptance run.
