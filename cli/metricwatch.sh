#!/usr/bin/env bash
# MetricWatch CLI — manage the Docker stack
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

COMPOSE="docker compose"
docker compose version &>/dev/null || COMPOSE="docker-compose"

usage() {
  cat <<EOF
MetricWatch CLI

Usage: ./cli/metricwatch.sh <command>

Commands:
  start       Start all services (creates .env if missing)
  stop        Stop all services
  restart     Restart all services
  status      Show service status
  logs        Tail logs (optional: service name)
  scale       Scale a consumer (e.g. scale sentiment-consumer 3)
  topics      List Kafka topics
  health      Hit API health endpoint
EOF
}

ensure_env() {
  [[ -f .env ]] || cp .env.example .env
}

cmd="${1:-}"
shift || true

case "$cmd" in
  start)
    ensure_env
    $COMPOSE up -d --build
    ;;
  stop)
    $COMPOSE down
    ;;
  restart)
    $COMPOSE restart "$@"
    ;;
  status)
    $COMPOSE ps
    ;;
  logs)
    $COMPOSE logs -f "$@"
    ;;
  scale)
    service="${1:?Usage: scale <service> <count>}"
    count="${2:?Usage: scale <service> <count>}"
    $COMPOSE up -d --scale "$service=$count" --no-recreate
    ;;
  topics)
    $COMPOSE exec kafka kafka-topics --list --bootstrap-server kafka:9092
    ;;
  health)
    curl -sf "http://localhost:${API_PORT:-8000}/health" | python -m json.tool
    ;;
  ""|help|-h|--help)
    usage
    ;;
  *)
    echo "Unknown command: $cmd"
    usage
    exit 1
    ;;
esac
