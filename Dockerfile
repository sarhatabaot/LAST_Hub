# syntax=docker/dockerfile:1.7
FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

COPY . .

RUN mkdir -p /app/data /app/media /app/staticfiles \
    && chmod -R 0777 /app/data /app/media /app/staticfiles

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
