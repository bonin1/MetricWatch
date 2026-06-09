# Testing MetricWatch

A step-by-step guide to verify everything works — from the API to Grafana.

---

## 0. Prerequisites

Stack must be running:

```powershell
docker compose ps
```

All core services should show **Up** and **healthy**. If not:

```powershell
.\start.ps1
```

Optional demo data:

```powershell
.\scripts\seed.ps1
```

Quick automated check:

```powershell
.\scripts\smoke_test.ps1
```

---

## 1. API layer (5 minutes)

Open these URLs in your browser or use PowerShell.

### Health

```
http://localhost:8000/health
```

Expected: `{"status":"healthy",...}`

### Metrics flowing

```
http://localhost:8000/api/metrics/latest
http://localhost:8000/api/metrics/history?metric_type=cpu&hours=1
```

Expected: `count` > 0 if producers or seed ran.

### Sentiment flowing

```
http://localhost:8000/api/sentiment/recent?limit=10
http://localhost:8000/api/sentiment/stats
```

Expected: recent posts with `positive` / `negative` / `neutral`.

### PowerShell one-liner

```powershell
Invoke-RestMethod http://localhost:8000/health
(Invoke-RestMethod "http://localhost:8000/api/metrics/history?metric_type=cpu&hours=1").count
```

If all return data → **API + databases work**.

---

## 2. Dashboard (http://localhost:3000)

| What to check | Pass criteria |
|---------------|---------------|
| Top-right status | Green **Live** pill |
| KPI cards | CPU / Memory show numbers (not `—`) |
| Infrastructure chart | Lines moving or historical data visible |
| Sentiment donut | Shows positive / negative / neutral slices |
| Activity log | Rows appearing over time |

**Hard refresh:** `Ctrl+Shift+R`

**Live test:** Leave the tab open 30 seconds — event count should increase (producers run every 2–5s).

If empty → run `.\scripts\seed.ps1` then refresh.

---

## 3. Prometheus (http://localhost:9090)

Prometheus **scrapes internal service metrics** (message rates, latency, API calls). It does not show your CPU/memory business metrics — those live in the MetricWatch dashboard and PostgreSQL.

### Step A — Targets healthy

1. Open http://localhost:9090/targets
2. Confirm these jobs are **UP**:
   - `metrics-producer`
   - `social-producer`
   - `metrics-consumer`
   - `sentiment-consumer`
   - `api-gateway`

If **DOWN** → `docker compose logs <service-name>`

### Step B — Run queries

Go to http://localhost:9090/graph and try:

| Query | Meaning |
|-------|---------|
| `rate(metrics_consumer_messages_processed_total[5m])` | Metrics processed per second |
| `rate(sentiment_consumer_messages_processed_total[5m])` | Sentiment messages per second |
| `websocket_connections` | Open dashboard WebSocket clients |
| `api_requests_total` | API traffic |

Click **Execute** → switch to **Graph**. You should see lines after a few minutes of uptime.

---

## 4. Grafana (http://localhost:3001)

Login: **admin** / **admin** (skip password change or set one).

### Step A — Data source

1. **Connections → Data sources → Prometheus**
2. Click **Test** → should say success
3. URL should be `http://prometheus:9090` (internal Docker URL)

### Step B — Pre-built dashboard

1. **Dashboards** (left menu)
2. Open **MetricWatch - Service Health**
3. You should see panels for:
   - Messages processed
   - Processing latency (p95)
   - API request rate
   - WebSocket connections

Set time range to **Last 15 minutes** (top-right).

### Step C — Build your first panel

1. **Explore** → select **Prometheus**
2. Query: `rate(metrics_producer_messages_sent_total[5m])`
3. **Run query** → you should see the metrics producer sending data

---

## 5. End-to-end pipeline test

This proves Kafka → consumers → storage → API works:

```powershell
# 1. Note current CPU history count
$before = (Invoke-RestMethod "http://localhost:8000/api/metrics/history?metric_type=cpu&hours=1").count

# 2. Wait 30 seconds for live producers
Start-Sleep -Seconds 30

# 3. Count should increase
$after = (Invoke-RestMethod "http://localhost:8000/api/metrics/history?metric_type=cpu&hours=1").count
Write-Host "Before: $before  After: $after"
```

`After` > `Before` → **full pipeline is live**.

### Kafka topics (optional)

```powershell
docker compose exec kafka kafka-topics --list --bootstrap-server kafka:9092
docker compose exec kafka kafka-consumer-groups --bootstrap-server kafka:9092 --describe --all-groups
```

Expected topics: `system-metrics`, `social-text`. Consumer lag should stay low.

---

## 6. What each UI is for

| Tool | Purpose |
|------|---------|
| **Dashboard :3000** | Business view — CPU, sentiment, live events |
| **API :8000** | Raw JSON, exports, integrations |
| **Prometheus :9090** | Service health metrics, alerting queries |
| **Grafana :3001** | Pretty charts on top of Prometheus |
| **Alertmanager :9093** | Alert routing (Slack/email when configured) |

---

## 7. Troubleshooting

| Symptom | Fix |
|---------|-----|
| Dashboard empty | `.\scripts\seed.ps1` then `Ctrl+Shift+R` |
| Prometheus targets DOWN | `docker compose restart metrics-producer api-gateway` |
| Grafana "No data" | Wait 2–3 min; set time range to Last 15 min |
| API connection error | `docker compose ps api-gateway` |
| No sentiment | Check `SENTIMENT_MODE` in `.env`; `docker compose logs sentiment-consumer` |

---

## 8. Checklist (copy/paste)

```
[ ] docker compose ps — all healthy
[ ] http://localhost:8000/health — healthy
[ ] /api/metrics/history?metric_type=cpu — count > 0
[ ] http://localhost:3000 — charts + Live status
[ ] http://localhost:9090/targets — jobs UP
[ ] Prometheus query rate(metrics_consumer_messages_processed_total[5m]) — graph
[ ] http://localhost:3001 — login, Service Health dashboard
[ ] Wait 30s — dashboard events increase
```

All checked → **MetricWatch is working end-to-end**.
