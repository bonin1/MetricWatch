# Connecting to Your Existing Kafka Instance

This project is configured to connect to your existing Kafka Docker container. Here are the connection options:

## Option 1: Same Docker Network (Recommended)

If your Kafka container is on a custom network, add MetricWatch services to that network:

```bash
# Find your Kafka network
docker network ls
docker inspect <kafka-container-name> | grep NetworkMode

# Update docker-compose.yml to use that network
# Replace 'metricwatch-network' with your Kafka network name
```

## Option 2: Use Docker Host Network

Update each service in `docker-compose.yml` to use host network:

```yaml
services:
  metrics-producer:
    network_mode: "host"
    # ... rest of config
```

Then update `.env`:
```env
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

## Option 3: Connect Networks

Connect the MetricWatch network to your Kafka network:

```bash
# Start MetricWatch services
docker-compose up -d

# Connect to Kafka network
docker network connect <kafka-network-name> metricwatch-metrics-producer
docker network connect <kafka-network-name> metricwatch-social-producer
docker network connect <kafka-network-name> metricwatch-metrics-consumer
docker network connect <kafka-network-name> metricwatch-sentiment-consumer
```

## Verify Connectivity

Test Kafka connection from a producer:

```bash
docker-compose exec metrics-producer ping kafka
```

If `kafka` doesn't resolve, use the Kafka container's IP or name:

```bash
# Find Kafka container name/IP
docker ps | grep kafka
docker inspect <kafka-container> | grep IPAddress

# Update .env
KAFKA_BOOTSTRAP_SERVERS=<kafka-ip>:9092
# or
KAFKA_BOOTSTRAP_SERVERS=<kafka-container-name>:9092
```

## Troubleshooting

If services can't connect to Kafka:

1. Check Kafka is running: `docker ps | grep kafka`
2. Check Kafka logs: `docker logs <kafka-container>`
3. Verify Kafka port: Usually 9092 for internal, 29092 for external
4. Check network: `docker network inspect <network-name>`
5. Test from producer: `docker-compose logs metrics-producer | grep -i kafka`
