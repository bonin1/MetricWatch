# Integrating Your Application with MetricWatch

MetricWatch accepts JSON metrics on the `system-metrics` Kafka topic and social/text events on `social-text`.

## Quick connection

| Setting | Default (Docker) | From host machine |
|---------|------------------|-------------------|
| Kafka bootstrap | `kafka:9092` | `localhost:29092` |
| Metrics topic | `system-metrics` | same |
| Social topic | `social-text` | same |
| API | `http://api-gateway:8000` | `http://localhost:8000` |

## Metric message schema

```json
{
  "metric_type": "cpu",
  "value": 72.5,
  "hostname": "my-service",
  "timestamp": "2026-06-09T12:00:00Z",
  "metadata": { "region": "us-east", "service": "checkout" }
}
```

Required fields: `metric_type`, `value`, `hostname`, `timestamp` (ISO-8601).

## Custom topics

Set in `.env`:

```env
KAFKA_TOPIC_METRICS=my-app-metrics
KAFKA_TOPIC_SOCIAL=my-app-events
```

Restart producers/consumers after changing topics.

## Example producers

- Python: [`examples/python_fastapi_producer.py`](../examples/python_fastapi_producer.py)
- Node.js: [`examples/nodejs_producer.js`](../examples/nodejs_producer.js)

```bash
# Python
pip install confluent-kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:29092 python examples/python_fastapi_producer.py

# Node.js
npm install kafkajs
KAFKA_BOOTSTRAP_SERVERS=localhost:29092 node examples/nodejs_producer.js
```

## REST API (bypass Kafka)

For low-volume telemetry you can query aggregated data after metrics land in storage:

- `GET /api/metrics/latest`
- `GET /api/metrics/history?metric_type=cpu&hours=24`
- `GET /api/export/metrics?format=csv&metric_type=cpu`

## Sentiment pipeline

Publish to `social-text`:

```json
{
  "text": "This release is amazing!",
  "user_id": "user-42",
  "platform": "twitter",
  "timestamp": "2026-06-09T12:00:00Z"
}
```

Use `SENTIMENT_MODE=keyword` in `.env` for fast startup without downloading DistilBERT (~250MB).
