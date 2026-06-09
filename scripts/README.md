# MetricWatch Scripts

## Seed demo data

Populates the stack with realistic metrics history, sentiment records, and a live WebSocket burst so the dashboard looks alive immediately.

**Prerequisites:** `docker compose up -d` (stack running)

### Recommended (runs inside Docker network)

```powershell
# Windows
.\scripts\seed.ps1

# Linux / macOS
./scripts/seed.sh

# Or directly
docker compose --profile seed run --rm seed
```

### Manual (from host)

```bash
pip install -r scripts/requirements.txt
python scripts/seed_data.py --local
```

> If local Postgres on port 5432 conflicts with Docker, use the Docker method above.

### Options

| Flag | Description |
|------|-------------|
| `--local` | Use `localhost` ports (required when running from host) |
| `--hours 4` | Hours of metric history (default: 2) |
| `--social 60` | Number of social messages (default: 40) |
| `--kafka-only` | Publish to Kafka only (full pipeline) |
| `--stores-only` | Write DB/Redis only (no Kafka) |
| `--no-live` | Skip live WebSocket burst |

### What gets seeded

- **Kafka** — metrics + social text (processed by consumers)
- **PostgreSQL** — time-series history for charts/export
- **Redis** — latest metrics + sentiment stats
- **MongoDB** — sentiment results
- **Elasticsearch** — searchable sample docs
- **Live burst** — recent messages for real-time dashboard updates

After seeding, open http://localhost:3000 and refresh (hard refresh: `Ctrl+Shift+R`).

## Where to verify seeded data

| What | Where to check |
|------|----------------|
| **Dashboard charts** | http://localhost:3000 — refresh after seed (loads from API + live WebSocket) |
| **Metrics history (JSON)** | http://localhost:8000/api/metrics/history?metric_type=cpu&hours=3 |
| **Latest metrics (Redis)** | http://localhost:8000/api/metrics/latest |
| **Sentiment records** | http://localhost:8000/api/sentiment/recent?limit=20 |
| **Sentiment stats** | http://localhost:8000/api/sentiment/stats |
| **Export CSV** | http://localhost:8000/api/export/metrics?format=csv&metric_type=cpu |
| **Grafana** | http://localhost:3001 |
| **Prometheus** | http://localhost:9090 |
| **PostgreSQL** | `docker compose exec postgres psql -U metricwatch -d metricwatch -c "SELECT COUNT(*) FROM metrics_timeseries;"` |
| **MongoDB** | `docker compose exec mongo mongosh -u metricwatch -p metricwatch123 --eval "db.getSiblingDB('metricwatch').sentiment_results.countDocuments()"` |
