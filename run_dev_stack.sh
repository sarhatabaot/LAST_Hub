#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

export UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}"
export UV_PROJECT_ENVIRONMENT="${UV_PROJECT_ENVIRONMENT:-/tmp/uv-venv}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-/tmp}"
export STATIC_ROOT="${STATIC_ROOT:-/tmp/staticfiles}"

uv sync
uv run python manage.py migrate
uv run python manage.py collectstatic --noinput
uv run python manage.py import_manual_md docs/manual

sudo systemctl restart last-hub.service
sudo systemctl status --no-pager last-hub.service
