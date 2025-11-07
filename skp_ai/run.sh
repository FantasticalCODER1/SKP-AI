#!/usr/bin/env bash
set -euo pipefail

if [ -f .env ]; then
  set -o allexport
  source .env
  set +o allexport
fi

uvicorn app.main:app --reload --host 0.0.0.0 --port "${PORT:-8000}"
