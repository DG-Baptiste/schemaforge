.PHONY: install check test demo docker-build

install:
	uv sync --all-extras
	uv run pre-commit install

check:
	uv run ruff format --check .
	uv run ruff check .
	uv run mypy src

test:
	uv run pytest -m "not slow"

demo:
	uv run schemaforge extract "Ada Lovelace works at Analytical Engines Ltd. Email ADA@EXAMPLE.ORG." --schema schemas/contact.json

docker-build:
	docker build -t schemaforge:local .

