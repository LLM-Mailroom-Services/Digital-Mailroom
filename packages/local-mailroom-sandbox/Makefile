.PHONY: install test up down health pilot jupyter prepare

install:
	pip install -e ".[dev,notebooks]"
	@if [ ! -f .env ]; then cp config/.env.example .env; else echo "(.env already exists — left untouched)"; fi

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
