.PHONY: ci eval test test-backend test-frontend lint format typecheck install-hooks up down build clean

PHASE ?= 1
PYTHON ?= python

ci:
	$(PYTHON) scripts/run_ci.py

install-hooks:
	$(PYTHON) -c "import shutil, os; os.makedirs('.git/hooks', exist_ok=True); [shutil.copy2('.githooks/' + h, '.git/hooks/' + h) for h in ('pre-commit', 'pre-push')]"
	@echo "Git pre-commit and pre-push hooks installed."

eval:
	$(PYTHON) -m backend.eval.runner --phase $(PHASE)

test:
	pytest backend/tests -v

test-backend:
	pytest backend/tests -v

test-frontend:
	cd frontend && npm test

lint:
	ruff check backend
	ruff format --check backend
	cd frontend && npm run lint

format:
	ruff check --fix backend
	ruff format backend

typecheck:
	mypy --config-file backend/pyproject.toml backend/app
	cd frontend && npx tsc --noEmit

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build
