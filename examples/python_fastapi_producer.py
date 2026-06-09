"""
Example: send custom metrics to MetricWatch from a Python app.

Prerequisites:
  pip install confluent-kafka

With MetricWatch running:
  KAFKA_BOOTSTRAP_SERVERS=localhost:29092 python examples/python_fastapi_producer.py
"""
import json
import os
import socket
import time
from datetime import datetime, timezone

from confluent_kafka import Producer

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092")
TOPIC = os.getenv("KAFKA_TOPIC_METRICS", "system-metrics")
HOSTNAME = os.getenv("METRIC_HOSTNAME", socket.gethostname())


def main():
    producer = Producer({"bootstrap.servers": BOOTSTRAP})

    for i in range(20):
        payload = {
            "metric_type": "custom",
            "value": 42.0 + i,
            "hostname": HOSTNAME,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": {"source": "python_fastapi_producer", "iteration": i},
        }
        producer.produce(TOPIC, key=f"{HOSTNAME}:custom", value=json.dumps(payload).encode())
        producer.poll(0)
        print(f"Sent metric {i}: {payload['value']}")
        time.sleep(2)

    producer.flush()
    print("Done.")


if __name__ == "__main__":
    main()
