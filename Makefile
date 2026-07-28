.PHONY: dev infra-up infra-down public-audit backend-test backend-lint web-dev web-test web-lint web-build check

dev:
	./scripts/dev.sh

infra-up:
	docker compose -f infra/docker-compose.yml up -d

infra-down:
	docker compose -f infra/docker-compose.yml down

public-audit:
	python3 scripts/validate_public_release.py

backend-test:
	cd backend && ENVIRONMENT=testing PYTHONPATH=. pytest -q

backend-lint:
	cd backend && ruff check app tests

web-dev:
	npm --prefix apps/web run dev

web-test:
	npm --prefix apps/web run test:run

web-lint:
	npm --prefix apps/web run lint

web-build:
	npm --prefix apps/web run build

check: public-audit backend-lint backend-test web-lint web-test web-build
