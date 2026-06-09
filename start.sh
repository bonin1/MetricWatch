#!/usr/bin/env bash
# MetricWatch — one-command deploy
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}MetricWatch — Quick Start${NC}"
echo "================================"
echo ""

# Docker
if ! command -v docker &>/dev/null; then
  echo -e "${RED}Docker not found. Install Docker Desktop or Docker Engine first.${NC}"
  exit 1
fi
echo -e "${GREEN}✓${NC} $(docker --version)"

# Docker Compose (plugin or standalone)
COMPOSE="docker compose"
if ! docker compose version &>/dev/null; then
  if command -v docker-compose &>/dev/null; then
    COMPOSE="docker-compose"
  else
    echo -e "${RED}Docker Compose not found.${NC}"
    exit 1
  fi
fi
echo -e "${GREEN}✓${NC} $($COMPOSE version 2>/dev/null | head -1)"
echo ""

# .env from example
if [[ ! -f .env ]]; then
  if [[ -f .env.example ]]; then
    cp .env.example .env
    echo -e "${GREEN}✓${NC} Created .env from .env.example"
  else
    echo -e "${RED}Missing .env.example — cannot create .env${NC}"
    exit 1
  fi
else
  echo -e "${GREEN}✓${NC} Using existing .env"
fi
echo ""

SENTIMENT_MODE=$(grep -E '^SENTIMENT_MODE=' .env 2>/dev/null | cut -d= -f2 | tr -d ' \r' || echo keyword)
if [ "$SENTIMENT_MODE" = "transformers" ]; then
  echo -e "${YELLOW}SENTIMENT_MODE=transformers — first build downloads ~2GB (PyTorch/CUDA). Can take 15-30 min.${NC}"
  echo -e "${YELLOW}For fast start: set SENTIMENT_MODE=keyword in .env${NC}"
else
  echo -e "${GREEN}SENTIMENT_MODE=keyword — lightweight build (no ML libraries)${NC}"
fi
echo -e "${YELLOW}Starting all services...${NC}"
$COMPOSE up -d --build

echo ""
echo -e "${YELLOW}Waiting for core services...${NC}"
sleep 15
$COMPOSE ps

echo ""
echo "================================"
echo -e "${GREEN}MetricWatch is running!${NC}"
echo ""
echo "  Dashboard:   http://localhost:3000"
echo "  API:         http://localhost:8000"
echo "  Grafana:     http://localhost:3001  (admin / admin)"
echo "  Prometheus:  http://localhost:9090"
echo ""
echo "  Seed data:   ./scripts/seed.sh"
echo "  CLI:         ./cli/metricwatch.sh status"
echo "  Logs:        $COMPOSE logs -f"
echo "  Stop:        $COMPOSE down"
echo "================================"
