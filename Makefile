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
	uv run schemaforge extract "Ищем Python-разработчика в ООО Альфа. Зарплата 180000–240000 RUB." --schema schemas/vacancy.yaml

docker-build:
	docker build -t schemaforge:local .

