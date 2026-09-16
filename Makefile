.PHONY: body-model local frontend test mock-smoke release provision stop
LOCAL_COMPOSE = docker compose --env-file .env.local-real -f compose.yaml -f compose.local-real.yaml
MOCK_COMPOSE = docker compose --env-file .env.mock -f compose.yaml -f compose.mock.yaml

body-model:
	python3 scripts/download-body-model.py
local:
	python3 scripts/local_real.py $(if $(MODELS),--models "$(MODELS)",)
	$(LOCAL_COMPOSE) up -d --build
frontend:
	cd frontend && npm ci && npm run dev
test:
	.venv/bin/pytest -q tests
mock-smoke:
	python3 scripts/mock_init.py
	@set -eu; \
	trap '$(MOCK_COMPOSE) stop' EXIT; \
	$(MOCK_COMPOSE) up -d --build; \
	.venv/bin/python scripts/smoke_local.py
release:
	python3 scripts/release.py $(if $(REF),--ref $(REF),)
provision:
	terraform -chdir=infra init
	terraform -chdir=infra plan
stop:
	$(LOCAL_COMPOSE) stop
