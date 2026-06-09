#!/usr/bin/env python3
"""
Seed MetricWatch with demo metrics and sentiment data.

Usage (stack must be running):
  pip install -r scripts/requirements.txt
  python scripts/seed_data.py --local          # from host machine
  python scripts/seed_data.py                  # inside Docker network

  ./scripts/seed.sh
  .\\scripts\\seed.ps1
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from faker import Faker

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

fake = Faker()

HOSTNAMES = ["api-gateway-01", "metrics-worker-02", "edge-node-03"]
PLATFORMS = ["twitter", "reddit", "linkedin", "github"]

SOCIAL_SAMPLES = [
    ("This deployment pipeline is incredibly fast and reliable!", "positive"),
    ("Love how clean the new dashboard looks. Great work team.", "positive"),
    ("Monitoring setup was painless. Up and running in minutes.", "positive"),
    ("Terrible latency spikes after the last release.", "negative"),
    ("Service keeps crashing under moderate load. Very frustrated.", "negative"),
    ("The documentation could be much better.", "negative"),
    ("Metrics look normal for this time of day.", "neutral"),
    ("Running some routine checks on the cluster.", "neutral"),
    ("Average response times, nothing unusual.", "neutral"),
    ("Kafka consumer lag is back to zero. Excellent!", "positive"),
]


def apply_local_overrides() -> None:
    """Point at published Docker ports when running from the host."""
    os.environ["KAFKA_BOOTSTRAP_SERVERS"] = "localhost:29092"
    os.environ["REDIS_HOST"] = "localhost"
    os.environ["MONGO_HOST"] = "localhost"
    os.environ["POSTGRES_HOST"] = "localhost"
    os.environ["ELASTICSEARCH_HOST"] = "localhost"


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def generate_metrics(hours: float = 2, points_per_hour: int = 60) -> list[dict]:
    """Generate realistic metric time series with gentle waves + noise."""
    total = int(hours * points_per_hour)
    interval = timedelta(hours=hours) / max(total, 1)
    start = utc_now() - timedelta(hours=hours)
    rows = []

    for i in range(total):
        ts = start + interval * i
        phase = i / max(points_per_hour, 1) * math.pi * 2
        hostname = HOSTNAMES[i % len(HOSTNAMES)]
        base_cpu = 38 + 12 * math.sin(phase) + random.uniform(-4, 4)
        base_mem = 62 + 8 * math.cos(phase * 0.7) + random.uniform(-3, 3)

        for metric_type, value in [
            ("cpu", max(5, min(98, base_cpu))),
            ("memory", max(10, min(95, base_mem))),
            ("disk", max(20, min(88, 55 + 5 * math.sin(phase * 0.3)))),
            ("network", max(0.1, 2.5 + 1.5 * abs(math.sin(phase * 1.2)) + random.uniform(0, 0.8))),
        ]:
            rows.append({
                "timestamp": ts.isoformat(),
                "metric_type": metric_type,
                "value": round(value, 2),
                "hostname": hostname,
                "metadata": {"source": "seed", "batch": "demo"},
            })
    return rows


def generate_social(count: int) -> list[dict]:
    messages = []
    for i in range(count):
        if i < len(SOCIAL_SAMPLES):
            text, _ = SOCIAL_SAMPLES[i % len(SOCIAL_SAMPLES)]
        else:
            text = fake.sentence(nb_words=12)
        messages.append({
            "timestamp": (utc_now() - timedelta(minutes=random.randint(0, 120))).isoformat(),
            "text": text,
            "user_id": f"user_{fake.uuid4()[:8]}",
            "platform": random.choice(PLATFORMS),
            "hashtags": random.sample(["devops", "monitoring", "sre", "metrics", "kafka"], k=2),
            "metadata": {"source": "seed"},
        })
    return messages


def sentiment_for_text(text: str) -> tuple[str, float]:
    lower = text.lower()
    neg = sum(1 for w in ("terrible", "bad", "frustrated", "crashing", "awful", "disappointed") if w in lower)
    pos = sum(1 for w in ("love", "great", "excellent", "fast", "reliable", "clean", "painless") if w in lower)
    if pos > neg:
        return "positive", round(random.uniform(0.72, 0.95), 2)
    if neg > pos:
        return "negative", round(random.uniform(0.72, 0.95), 2)
    return "neutral", round(random.uniform(0.55, 0.75), 2)


def seed_kafka(metrics: list[dict], social: list[dict]) -> None:
    from confluent_kafka import Producer

    bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    metrics_topic = os.getenv("KAFKA_TOPIC_METRICS", "system-metrics")
    social_topic = os.getenv("KAFKA_TOPIC_SOCIAL", "social-text")

    producer = Producer({"bootstrap.servers": bootstrap})
    sent = 0

    for row in metrics:
        producer.produce(
            metrics_topic,
            key=f"{row['hostname']}:{row['metric_type']}",
            value=json.dumps(row).encode(),
        )
        sent += 1
        if sent % 50 == 0:
            producer.poll(0)

    for row in social:
        producer.produce(
            social_topic,
            key=row["user_id"],
            value=json.dumps(row).encode(),
        )

    producer.flush()
    print(f"  Kafka: published {len(metrics)} metrics + {len(social)} social messages")


def seed_postgres(metrics: list[dict]) -> None:
    import psycopg2

    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "metricwatch"),
        user=os.getenv("POSTGRES_USER", "metricwatch"),
        password=os.getenv("POSTGRES_PASSWORD", "metricwatch123"),
    )
    try:
        with conn.cursor() as cur:
            for row in metrics:
                cur.execute(
                    """INSERT INTO metrics_timeseries (timestamp, metric_type, value, hostname, metadata)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (row["timestamp"], row["metric_type"], row["value"], row["hostname"], json.dumps(row["metadata"])),
                )
        conn.commit()
        print(f"  PostgreSQL: inserted {len(metrics)} metric rows")
    finally:
        conn.close()


def seed_redis(metrics: list[dict], social: list[dict]) -> None:
    import redis as redis_lib

    r = redis_lib.Redis(
        host=os.getenv("REDIS_HOST", "redis"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=int(os.getenv("REDIS_DB", "0")),
        decode_responses=True,
    )

    latest = {}
    for row in metrics:
        key = f"metrics:latest:{row['hostname']}:{row['metric_type']}"
        latest[key] = json.dumps({
            "value": row["value"],
            "timestamp": row["timestamp"],
            "metadata": row["metadata"],
        })

    for key, val in latest.items():
        r.set(key, val, ex=300)

    counts = {"positive": 0, "negative": 0, "neutral": 0}
    recent = []
    for row in social:
        sentiment, _ = sentiment_for_text(row["text"])
        counts[sentiment] += 1
        recent.append(sentiment)

    r.delete("sentiment:stats")
    for k, v in counts.items():
        if v:
            r.hset("sentiment:stats", k, v)

    r.delete("sentiment:recent")
    for s in recent[:100]:
        r.lpush("sentiment:recent", s)

    print(f"  Redis: {len(latest)} latest metric keys, sentiment stats {counts}")


def seed_mongo(social: list[dict]) -> None:
    from pymongo import MongoClient

    user = os.getenv("MONGO_USER", "metricwatch")
    password = os.getenv("MONGO_PASSWORD", "metricwatch123")
    host = os.getenv("MONGO_HOST", "mongo")
    port = int(os.getenv("MONGO_PORT", "27017"))
    db_name = os.getenv("MONGO_DB", "metricwatch")

    client = MongoClient(f"mongodb://{user}:{password}@{host}:{port}/")
    coll = client[db_name]["sentiment_results"]

    docs = []
    for row in social:
        sentiment, score = sentiment_for_text(row["text"])
        docs.append({
            "timestamp": datetime.fromisoformat(row["timestamp"]),
            "text": row["text"],
            "sentiment": sentiment,
            "score": score,
            "user_id": row["user_id"],
            "platform": row["platform"],
            "processing_time_ms": round(random.uniform(2, 18), 1),
        })

    if docs:
        coll.insert_many(docs)
    print(f"  MongoDB: inserted {len(docs)} sentiment documents")
    client.close()


def seed_elasticsearch(metrics: list[dict], social: list[dict]) -> None:
    from elasticsearch import Elasticsearch

    host = os.getenv("ELASTICSEARCH_HOST", "elasticsearch")
    port = os.getenv("ELASTICSEARCH_PORT", "9200")
    es = Elasticsearch(f"http://{host}:{port}", request_timeout=10)
    try:
        es.info()
    except Exception:
        print("  Elasticsearch: skipped (not reachable)")
        return

    for row in metrics[-80:]:
        es.index(index="metrics", document={
            "timestamp": row["timestamp"],
            "metric_type": row["metric_type"],
            "value": row["value"],
            "hostname": row["hostname"],
            "metadata": row["metadata"],
        })

    for row in social:
        sentiment, score = sentiment_for_text(row["text"])
        es.index(index="sentiment", document={
            "timestamp": row["timestamp"],
            "text": row["text"],
            "sentiment": sentiment,
            "score": score,
            "user_id": row["user_id"],
            "platform": row["platform"],
        })

    print(f"  Elasticsearch: indexed sample metrics + {len(social)} sentiment docs")


def publish_live_burst(metrics: list[dict], social: list[dict], count: int = 24) -> None:
    """Publish recent-timestamp messages so consumers push WebSocket updates."""
    from confluent_kafka import Producer

    bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    metrics_topic = os.getenv("KAFKA_TOPIC_METRICS", "system-metrics")
    social_topic = os.getenv("KAFKA_TOPIC_SOCIAL", "social-text")
    producer = Producer({"bootstrap.servers": bootstrap})
    now = utc_now()

    recent_metrics = [m for m in metrics if m["metric_type"] == "cpu"][-count:]
    for i, row in enumerate(recent_metrics):
        live = {**row, "timestamp": (now - timedelta(seconds=(count - i) * 5)).isoformat()}
        producer.produce(metrics_topic, key=f"{live['hostname']}:{live['metric_type']}", value=json.dumps(live).encode())
        producer.poll(0)
        time.sleep(0.05)

    for i, row in enumerate(social[: min(12, len(social))]):
        live = {**row, "timestamp": (now - timedelta(seconds=i * 3)).isoformat()}
        producer.produce(social_topic, key=live["user_id"], value=json.dumps(live).encode())
        producer.poll(0)
        time.sleep(0.05)

    producer.flush()
    print(f"  Live burst: {len(recent_metrics)} metrics + {min(12, len(social))} social (WebSocket feed)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed MetricWatch with demo data")
    parser.add_argument("--local", action="store_true", help="Use localhost ports (run from host)")
    parser.add_argument("--hours", type=float, default=2.0, help="Hours of metric history")
    parser.add_argument("--social", type=int, default=40, help="Number of social messages")
    parser.add_argument("--kafka-only", action="store_true", help="Only publish to Kafka")
    parser.add_argument("--stores-only", action="store_true", help="Only write to databases (no Kafka)")
    parser.add_argument("--no-live", action="store_true", help="Skip live WebSocket burst")
    args = parser.parse_args()

    if args.local:
        apply_local_overrides()

    print("MetricWatch — seeding demo data", flush=True)
    print("=" * 40, flush=True)

    metrics = generate_metrics(hours=args.hours)
    social = generate_social(args.social)
    print(f"Generated {len(metrics)} metrics, {len(social)} social messages", flush=True)

    errors: list[str] = []

    def run_step(name: str, fn) -> None:
        try:
            fn()
        except Exception as e:
            errors.append(f"{name}: {e}")
            print(f"  [!] {name} failed: {e}", flush=True)

    if not args.stores_only:
        run_step("Kafka", lambda: seed_kafka(metrics, social))
        if not args.no_live:
            run_step("Live burst", lambda: publish_live_burst(metrics, social))

    if not args.kafka_only:
        run_step("PostgreSQL", lambda: seed_postgres(metrics))
        run_step("Redis", lambda: seed_redis(metrics, social))
        run_step("MongoDB", lambda: seed_mongo(social))
        run_step("Elasticsearch", lambda: seed_elasticsearch(metrics, social))

    print("=" * 40, flush=True)
    if errors:
        print(f"Completed with {len(errors)} warning(s).", flush=True)
        if args.local:
            print("Tip: use Docker seed for reliable DB access:", flush=True)
            print("  docker compose --profile seed run --rm seed", flush=True)
        return 1

    print("Done! Open http://localhost:3000 and refresh.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
