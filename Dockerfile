FROM python:3.12-slim AS builder
WORKDIR /app
RUN pip install --no-cache-dir uv==0.6.5
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev

FROM python:3.12-slim
RUN useradd --create-home --uid 10001 appuser
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY schemas ./schemas
COPY examples ./examples
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER appuser
ENTRYPOINT ["schemaforge"]
CMD ["--help"]

