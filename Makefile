.PHONY: install test up down health pilot jupyter prepare

install:
	pip install -e ".[dev,notebooks]"
	@if [ ! -f .env ]; then cp config/.env.example .env; else echo "(.env already exists — left untouched)"; fi

# Regenerate requirements/*.txt from pyproject.toml (DMR-078b).
requirements-sync:
	python3 scripts/sync_requirements.py

requirements-check:
	python3 scripts/sync_requirements.py --check

test:
	pytest -v

up:
	sandbox up --profile ollama

down:
	sandbox down --profile ollama

health:
	sandbox health --profile ollama

pilot:
	sandbox pilot --mock

jupyter:
	sandbox up --compose-profile jupyter

prepare:
	sandbox datasets prepare
