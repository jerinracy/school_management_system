.PHONY: install run test lint format typecheck migrate makemigrations schema docker-up docker-down clean

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
