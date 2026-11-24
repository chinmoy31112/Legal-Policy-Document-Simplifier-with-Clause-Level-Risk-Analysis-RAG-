.PHONY: eval test lint format typecheck up down build clean

PHASE ?= 1

eval:
	python -m backend.eval.runner --phase $(PHASE)

test:
	pytest backend/tests -v

test-backend:
	pytest backend/tests -v

test-frontend:
	cd frontend && npm test

lint:
	ruff check backend
	cd frontend && npm run lint

typecheck:
	mypy backend/app --ignore-missing-imports
	cd frontend && npx tsc --noEmit

up:
	docker-compose up -d

down:
	docker-compose down

build:
	docker-compose build
