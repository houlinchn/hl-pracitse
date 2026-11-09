FROM ghcr.io/astral-sh/uv:0.13.7 AS uv
FROM python:3.13-slim-bookworm
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY poc ./poc
RUN useradd --uid 1000 --create-home poc && chown -R poc:poc /app && chmod -R a+rX /app
USER poc
CMD ["uv", "run", "--frozen", "--no-dev", "uvicorn", "poc.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
