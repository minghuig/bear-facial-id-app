.PHONY: local frontend test release provision stop
local:
	python3 scripts/local_init.py
	docker compose up -d --build
frontend:
	cd frontend && npm ci && npm run dev
test:
	.venv/bin/pytest -q tests
release:
	python3 scripts/release.py $(if $(REF),--ref $(REF),)
provision:
	terraform -chdir=infra init
	terraform -chdir=infra plan
stop:
	docker compose stop
