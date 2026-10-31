.PHONY: help venv test test-backend test-frontend lint adk-web adk-run api up down logs gcp-setup gcp-deploy gcp-deploy-adk gcp-cleanup

PY := backend/.venv/bin/python
NODE := docker run --rm -v $(CURDIR)/frontend:/app -w /app node:20-alpine

help: ## Show targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n",$$1,$$2}'

venv: ## Create backend venv (Python 3.12) + install deps
	cd backend && uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements-dev.txt

test: test-backend test-frontend ## Run all tests

test-backend: ## pytest + coverage (offline, fake LLM)
	cd backend && .venv/bin/python -m pytest -q --cov=bloggeragent --cov=app --cov-report=term-missing

test-frontend: ## vitest (in Docker, no local Node needed)
	$(NODE) sh -c "npm ci --no-audit --no-fund >/dev/null && npx vitest run"

lint: ## ruff + tsc
	cd backend && .venv/bin/ruff check .
	$(NODE) sh -c "npm ci --no-audit --no-fund >/dev/null && npx tsc -b --noEmit"

adk-web: ## Codelab step 7: ADK Web UI on :8000
	cd backend && .venv/bin/adk web --port 8000

adk-run: ## Chat with the agent in the terminal
	cd backend && .venv/bin/adk run bloggeragent

api: ## FastAPI dev server on :8080 (API only)
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8080

up: ## docker compose: app + Postgres → http://localhost:8080
	docker compose up --build -d db app

down: ## Stop compose stack
	docker compose down

logs: ## Tail app logs
	docker compose logs -f app

gcp-setup: ## One-time GCP infra (PROJECT_ID=... REGION=...)
	./deploy/setup_gcp.sh

gcp-deploy: ## Build with Cloud Build + deploy Cloud Run
	./deploy/deploy.sh

gcp-deploy-adk: ## Original codelab deploy (adk deploy cloud_run --with_ui)
	./deploy/deploy_adk_cli.sh

gcp-cleanup: ## Delete all cloud resources
	./deploy/cleanup.sh
