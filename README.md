# 🚀 MetricWatch - Fault-Tolerant Microservices System

A production-grade, horizontally scalable microservices architecture featuring real-time system metrics collection, sentiment analysis using AI, and live dashboard updates through WebSockets.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         KAFKA EVENT BUS                          │
│                   (system-metrics, social-text)                  │
└──────────────┬────────────────────────────────┬─────────────────┘
               │                                │
       ┌───────▼────────┐              ┌───────▼────────┐
       │   PRODUCERS    │              │   CONSUMERS    │
       ├────────────────┤              ├────────────────┤
       │ Metrics        │              │ Metrics        │
       │ Social Text    │              │ Sentiment (AI) │
       └────────────────┘              └────┬───────────┘
                                            │
                    ┌───────────────────────┴──────────────────┐
                    │         STORAGE LAYER                     │
                    ├──────────┬──────────┬──────────┬─────────┤
                    │  Redis   │ MongoDB  │Postgres  │  ES     │
                    └──────────┴──────────┴──────────┴─────────┘
                                            │
                                   ┌────────▼────────┐
                                   │  API GATEWAY    │
                                   │  + WebSocket    │
                                   └────────┬────────┘
                                            │
                                   ┌────────▼────────┐
                                   │ REACT DASHBOARD │
                                   │   (ECharts)     │
                                   └─────────────────┘
```

## ✨ Features

- **Event-Driven Architecture**: Apache Kafka for reliable message streaming
- **Horizontal Scalability**: Stateless consumers with automatic partition rebalancing
- **Multi-Storage Persistence**: Redis, MongoDB, PostgreSQL, Elasticsearch
- **AI-Powered Sentiment Analysis**: Hugging Face DistilBERT model
- **Real-Time Updates**: WebSocket connections via Socket.IO
- **Modern Dashboard**: React with ECharts for beautiful visualizations
- **Full Observability**: Prometheus + Grafana monitoring
- **Fault Tolerance**: Service health checks and automatic restarts

## 🛠️ Technology Stack

| Component | Technology |
|-----------|-----------|
| **Event Bus** | Apache Kafka |
| **Producers** | Python + confluent-kafka + psutil/Faker |
| **Consumers** | Python + transformers (DistilBERT) |
| **Storage** | Redis, MongoDB, PostgreSQL, Elasticsearch |
| **API Gateway** | FastAPI + Socket.IO |
| **Dashboard** | React + Vite + ECharts |
| **Monitoring** | Prometheus + Grafana |
| **Containerization** | Docker + Docker Compose |

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose installed
- **Existing Kafka instance running** (configured in your Docker network)
- Minimum 6-8GB RAM available
- Git

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd MetricWatch
```

2. **Configure Kafka connection**

Edit `.env` file to point to your existing Kafka instance:
```env
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
```

3. **Start all services**
```bash
docker-compose up -d
```

4. **Verify services are running**
```bash
docker-compose ps
```

5. **Access the dashboard**
- Dashboard: http://localhost:3000
- API Gateway: http://localhost:8000
- Grafana: http://localhost:3001 (admin/admin)
- Prometheus: http://localhost:9090

## 📊 Services Overview

### Producers

#### Metrics Producer
- Collects system metrics (CPU, memory, disk, network) using `psutil`
- Publishes to `system-metrics` Kafka topic every 5 seconds
- Exposes Prometheus metrics on port 8001

#### Social Producer
- Generates realistic mock social media posts using Faker
- Publishes to `social-text` Kafka topic every 2 seconds
- Simulates varying sentiment (60% positive, 20% negative, 20% neutral)
- Exposes Prometheus metrics on port 8002

### Consumers

#### Metrics Consumer
- Consumes from `system-metrics` topic
- Performs real-time aggregation (1-min, 5-min, 15-min windows)
- **Multi-storage persistence**:
  - **Redis**: Latest values with TTL for dashboard
  - **PostgreSQL**: Time-series data for historical analysis
  - **Elasticsearch**: Indexed metrics for search
- Publishes events to WebSocket via Redis pub/sub
- Consumer group: `metrics-consumer-group`
- Exposes Prometheus metrics on port 8003

#### Sentiment Consumer
- Consumes from `social-text` topic
- Performs sentiment analysis using DistilBERT
- **Multi-storage persistence**:
  - **MongoDB**: Full text + sentiment results
  - **Elasticsearch**: Indexed for full-text search
- Publishes events to WebSocket via Redis pub/sub
- Consumer group: `sentiment-consumer-group`
- Exposes Prometheus metrics on port 8004

### API Gateway
- FastAPI application with REST endpoints
- Socket.IO WebSocket server for real-time updates
- Connects to all storage backends
- Endpoints:
  - `GET /health` - Health check
  - `GET /api/metrics/latest` - Latest metrics from Redis
  - `GET /api/metrics/history` - Historical data from PostgreSQL
  - `GET /api/metrics/aggregated` - Aggregated metrics
  - `GET /api/sentiment/recent` - Recent sentiment from MongoDB
  - `GET /api/sentiment/stats` - Sentiment statistics from Redis
  - `GET /api/search` - Elasticsearch queries
  - `GET /metrics` - Prometheus metrics

### Dashboard
- Modern React application built with Vite
- Real-time charts using ECharts
- WebSocket integration for live updates
- Dark theme with glassmorphism effects
- Responsive design

## 🔄 Horizontal Scaling

Scale consumers dynamically to handle increased load:

```bash
# Scale sentiment consumer to 3 instances
docker-compose up -d --scale sentiment-consumer=3

# Verify partition distribution
docker-compose exec kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --describe \
  --group sentiment-consumer-group

# Scale back down
docker-compose up -d --scale sentiment-consumer=1
```

Kafka automatically rebalances partitions across consumer instances.

## 📈 Monitoring

### Prometheus Metrics

All services expose Prometheus metrics:
- Message processing rates
- Processing latency (histograms)
- Error rates
- Storage operation counts
- Model inference time
- WebSocket connections

Access Prometheus: http://localhost:9090

### Grafana Dashboards

Pre-configured dashboards available at http://localhost:3001:
- **Service Health**: Processing rates, latency, API metrics
- Sentiment distribution
- Model performance

Default credentials: `admin` / `admin`

## 🧪 Testing

### Verify Kafka Topics

```bash
docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:9092
```

Expected topics: `system-metrics`, `social-text`

### Check Consumer Lag

```bash
docker-compose exec kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --describe \
  --all-groups
```

### View Service Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f sentiment-consumer
```

### Test API Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Latest metrics
curl http://localhost:8000/api/metrics/latest

# Recent sentiment
curl http://localhost:8000/api/sentiment/recent?limit=10
```

## 🛡️ Fault Tolerance

The system is designed for resilience:

1. **Kafka Replication**: Messages replicated across brokers
2. **Consumer Groups**: Automatic partition rebalancing on failure
3. **Health Checks**: All services have Docker health checks
4. **Restart Policies**: Services automatically restart on failure
5. **Connection Pooling**: Efficient resource usage for storage
6. **WebSocket Reconnection**: Automatic reconnection on disconnect

## 🔧 Configuration

### Environment Variables

Key configuration in `.env`:

```env
# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_TOPIC_METRICS=system-metrics
KAFKA_TOPIC_SOCIAL=social-text

# Producer intervals (seconds)
METRICS_INTERVAL=5
SOCIAL_INTERVAL=2

# Consumer settings
CONSUMER_BATCH_SIZE=10

# Sentiment model
SENTIMENT_MODEL=distilbert-base-uncased-finetuned-sst-2-english
```

## 📁 Project Structure

```
MetricWatch/
├── shared/                    # Shared libraries
│   ├── kafka_config.py       # Kafka utilities
│   ├── storage_clients.py    # Storage connections
│   └── models.py             # Pydantic models
├── producers/
│   ├── metrics-producer/     # System metrics collector
│   └── social-producer/      # Social text generator
├── consumers/
│   ├── metrics-consumer/     # Metrics processor
│   └── sentiment-consumer/   # Sentiment analyzer
├── api-gateway/              # FastAPI + WebSocket server
├── dashboard/                # React dashboard
├── prometheus/               # Prometheus config
├── grafana/                  # Grafana dashboards
├── init-scripts/             # Database init scripts
├── docker-compose.yml        # Service orchestration
└── .env                      # Configuration
```

## 🐛 Troubleshooting

### Services won't start
- Check Docker resources (6-8GB RAM minimum)
- Verify Kafka is accessible: `docker-compose exec metrics-producer ping kafka`
- Check logs: `docker-compose logs <service-name>`

### No data in dashboard
- Verify WebSocket connection (green indicator in header)
- Check API Gateway logs: `docker-compose logs api-gateway`
- Ensure producers are running: `docker-compose ps`

### High consumer lag
- Scale consumers: `docker-compose up -d --scale <consumer>=3`
- Check Prometheus metrics for bottlenecks
- Verify storage backends are healthy

### Sentiment model download slow
- First startup downloads ~250MB model from Hugging Face
- Subsequent starts use cached model
- Check logs: `docker-compose logs sentiment-consumer`

## 📝 License

MIT License - feel free to use for learning and production!

## 🤝 Contributing

Contributions welcome! Please open an issue or PR.

## 📧 Support

For issues and questions, please open a GitHub issue.

---

**Built with ❤️ using Kafka, Python, React, and AI**
