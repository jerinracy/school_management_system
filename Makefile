.PHONY: install run test lint format typecheck migrate makemigrations schema docker-up docker-down clean fe-install fe-dev fe-build fe-lint fe-typecheck fe-test fe-gen-api

PYTHON ?= ./venv/bin/python
PIP ?= ./venv/bin/pip
PYTEST ?= ./venv/bin/pytest
RUFF ?= ./venv/bin/ruff
BLACK ?= ./venv/bin/black
MYPY ?= ./venv/bin/mypy

install:
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements-dev.txt
	./venv/bin/pre-commit install

run:
	$(PYTHON) manage.py runserver 0.0.0.0:8000

test:
	$(PYTEST) -v

lint:
	$(RUFF) check .
	$(BLACK) --check .

format:
	$(BLACK) .
	$(RUFF) check --fix .

typecheck:
	$(MYPY) apps config

migrate:
	$(PYTHON) manage.py migrate

makemigrations:
	$(PYTHON) manage.py makemigrations

schema:
	$(PYTHON) manage.py spectacular --file schema/schema.yml --validate

docker-up:
	docker compose up --build

docker-down:
	docker compose down -v

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

fe-install:
	cd frontend && npm install

fe-dev:
	cd frontend && npm run dev

fe-build:
	cd frontend && npm run build

fe-lint:
	cd frontend && npm run lint

fe-typecheck:
	cd frontend && npm run typecheck

fe-test:
	cd frontend && npm run test

fe-gen-api:
	cd frontend && npm run gen:api
