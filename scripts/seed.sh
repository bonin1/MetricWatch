#!/usr/bin/env bash
# Seed MetricWatch demo data (stack must be running)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

COMPOSE="docker compose"
docker compose version &>/dev/null || COMPOSE="docker-compose"

if command -v docker &>/dev/null; then
  echo "Seeding via Docker (recommended)..."
  $COMPOSE --profile seed run --rm seed "$@"
  exit $?
fi

echo "Docker not found — falling back to local Python..."
PY=python3
command -v python3 &>/dev/null || PY=python
"$PY" -m pip install -q -r scripts/requirements.txt
"$PY" scripts/seed_data.py --local "$@"
