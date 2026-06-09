# Kafka in MetricWatch

**MetricWatch now includes Kafka and Zookeeper in `docker-compose.yml`.** You do not need an external Kafka instance for the default setup.

## Default configuration

| Context | Bootstrap servers |
|---------|-------------------|
| Services inside Docker | `kafka:9092` |
| Apps on your host machine | `localhost:29092` |

Topics `system-metrics` and `social-text` are created automatically by the `kafka-init` service.

## Using an external Kafka cluster

If you prefer your own Kafka:

1. Set in `.env`:
   ```env
   KAFKA_BOOTSTRAP_SERVERS=your-kafka-host:9092
   ```
2. Comment out or remove the `zookeeper`, `kafka`, and `kafka-init` services in `docker-compose.yml`.
3. Ensure topics exist with 3 partitions and replication factor matching your cluster.

## Verify connectivity

```bash
docker compose exec kafka kafka-topics --list --bootstrap-server kafka:9092
./cli/metricwatch.sh topics
```

## Troubleshooting

1. `docker compose ps` — kafka should be `healthy`
2. `docker compose logs kafka` — broker startup errors
3. From host: `kafkacat -b localhost:29092 -L` (if kafkacat installed)
