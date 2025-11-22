"""
Metrics Consumer Service
Consumes system metrics from Kafka, performs aggregation, and persists to multiple storage backends.
"""
import os
import sys
import json
import logging
import asyncio
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List
from prometheus_client import Counter, Histogram, start_http_server

# Add shared module to path
sys.path.append('/app/shared')
from kafka_config import create_consumer, consume_messages
from storage_clients import redis_client, postgres_client, es_client
from models import SystemMetric, MetricAggregation

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
messages_processed = Counter('metrics_consumer_messages_processed_total', 'Total messages processed')
processing_time = Histogram('metrics_consumer_processing_seconds', 'Time spent processing messages')
storage_operations = Counter('metrics_consumer_storage_operations_total', 'Storage operations', ['backend', 'operation'])


class MetricsConsumer:
    """Consumes and processes system metrics."""
    
    def __init__(self):
        self.topic = os.getenv('KAFKA_TOPIC_METRICS', 'system-metrics')
        self.group_id = 'metrics-consumer-group'
        self.batch_size = int(os.getenv('CONSUMER_BATCH_SIZE', '10'))
        
        # Storage clients
        self.redis = redis_client.connect()
        self.es = es_client.connect()
        
        # Aggregation windows
        self.aggregation_buffers = {
            '1min': defaultdict(list),
            '5min': defaultdict(list),
            '15min': defaultdict(list)
        }
        self.last_aggregation = {
            '1min': datetime.utcnow(),
            '5min': datetime.utcnow(),
            '15min': datetime.utcnow()
        }
        
        logger.info(f"MetricsConsumer initialized - Topic: {self.topic}, Group: {self.group_id}")
    
    async def store_to_postgres(self, metric: SystemMetric):
        """Store metric to PostgreSQL time-series table."""
        try:
            pool = await postgres_client.connect()
            async with pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO metrics_timeseries (timestamp, metric_type, value, hostname, metadata)
                    VALUES ($1, $2, $3, $4, $5)
                ''', metric.timestamp, metric.metric_type, metric.value, metric.hostname, json.dumps(metric.metadata))
            
            storage_operations.labels(backend='postgres', operation='insert').inc()
            logger.debug(f"Stored metric to PostgreSQL: {metric.metric_type}")
        except Exception as e:
            logger.error(f"Failed to store to PostgreSQL: {e}")
    
    def store_to_redis(self, metric: SystemMetric):
        """Store latest metric value to Redis with TTL."""
        try:
            key = f"metrics:latest:{metric.hostname}:{metric.metric_type}"
            value = json.dumps({
                'value': metric.value,
                'timestamp': metric.timestamp.isoformat(),
                'metadata': metric.metadata
            })
            
            # Store with 5-minute TTL
            self.redis.setex(key, 300, value)
            
            # Also update a sorted set for recent metrics
            self.redis.zadd(
                f"metrics:recent:{metric.metric_type}",
                {f"{metric.hostname}:{metric.timestamp.isoformat()}": metric.timestamp.timestamp()}
            )
            self.redis.zremrangebyscore(
                f"metrics:recent:{metric.metric_type}",
                '-inf',
                (datetime.utcnow() - timedelta(minutes=15)).timestamp()
            )
            
            storage_operations.labels(backend='redis', operation='set').inc()
            logger.debug(f"Stored metric to Redis: {metric.metric_type}")
        except Exception as e:
            logger.error(f"Failed to store to Redis: {e}")
    
    def store_to_elasticsearch(self, metric: SystemMetric):
        """Index metric to Elasticsearch."""
        try:
            doc = {
                'timestamp': metric.timestamp.isoformat(),
                'metric_type': metric.metric_type,
                'value': metric.value,
                'hostname': metric.hostname,
                'metadata': metric.metadata
            }
            
            self.es.index(index='metrics', document=doc)
            storage_operations.labels(backend='elasticsearch', operation='index').inc()
            logger.debug(f"Indexed metric to Elasticsearch: {metric.metric_type}")
        except Exception as e:
            logger.error(f"Failed to index to Elasticsearch: {e}")
    
    def publish_to_websocket(self, metric: SystemMetric):
        """Publish metric event to Redis pub/sub for WebSocket gateway."""
        try:
            message = {
                'event_type': 'metric',
                'data': {
                    'metric_type': metric.metric_type,
                    'value': metric.value,
                    'hostname': metric.hostname,
                    'timestamp': metric.timestamp.isoformat()
                }
            }
            self.redis.publish('websocket:metrics', json.dumps(message))
            logger.debug(f"Published to WebSocket channel: {metric.metric_type}")
        except Exception as e:
            logger.error(f"Failed to publish to WebSocket: {e}")
    
    def add_to_aggregation_buffer(self, metric: SystemMetric):
        """Add metric to aggregation buffers."""
        for window_size in self.aggregation_buffers.keys():
            key = f"{metric.hostname}:{metric.metric_type}"
            self.aggregation_buffers[window_size][key].append(metric.value)
    
    async def process_aggregations(self):
        """Process aggregation windows and store results."""
        now = datetime.utcnow()
        
        for window_size, buffer in self.aggregation_buffers.items():
            # Determine window duration
            if window_size == '1min':
                duration = timedelta(minutes=1)
            elif window_size == '5min':
                duration = timedelta(minutes=5)
            else:  # 15min
                duration = timedelta(minutes=15)
            
            # Check if it's time to aggregate
            if now - self.last_aggregation[window_size] >= duration:
                await self._aggregate_window(window_size, buffer, duration)
                self.last_aggregation[window_size] = now
                buffer.clear()
    
    async def _aggregate_window(self, window_size: str, buffer: Dict[str, List[float]], duration: timedelta):
        """Aggregate metrics for a window and store to PostgreSQL."""
        if not buffer:
            return
        
        pool = await postgres_client.connect()
        
        for key, values in buffer.items():
            if not values:
                continue
            
            hostname, metric_type = key.split(':', 1)
            window_end = datetime.utcnow()
            window_start = window_end - duration
            
            aggregation = MetricAggregation(
                window_start=window_start,
                window_end=window_end,
                window_size=window_size,
                metric_type=metric_type,
                avg_value=sum(values) / len(values),
                min_value=min(values),
                max_value=max(values),
                count=len(values)
            )
            
            try:
                async with pool.acquire() as conn:
                    await conn.execute('''
                        INSERT INTO metrics_aggregated 
                        (window_start, window_end, window_size, metric_type, avg_value, min_value, max_value, count)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        ON CONFLICT (window_start, window_size, metric_type) DO UPDATE
                        SET avg_value = EXCLUDED.avg_value,
                            min_value = EXCLUDED.min_value,
                            max_value = EXCLUDED.max_value,
                            count = EXCLUDED.count
                    ''', aggregation.window_start, aggregation.window_end, aggregation.window_size,
                        aggregation.metric_type, aggregation.avg_value, aggregation.min_value,
                        aggregation.max_value, aggregation.count)
                
                logger.info(f"Stored {window_size} aggregation for {metric_type}: avg={aggregation.avg_value:.2f}")
            except Exception as e:
                logger.error(f"Failed to store aggregation: {e}")
    
    @processing_time.time()
    def process_message(self, message: dict):
        """Process a single metric message."""
        try:
            # Parse message
            metric = SystemMetric(**message)
            
            # Run async storage operations
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Store to all backends
            loop.run_until_complete(self.store_to_postgres(metric))
            self.store_to_redis(metric)
            self.store_to_elasticsearch(metric)
            
            # Publish to WebSocket
            self.publish_to_websocket(metric)
            
            # Add to aggregation buffers
            self.add_to_aggregation_buffer(metric)
            
            # Process aggregations if needed
            loop.run_until_complete(self.process_aggregations())
            
            loop.close()
            
            messages_processed.inc()
            logger.info(f"Processed metric: {metric.metric_type} = {metric.value} from {metric.hostname}")
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def run(self):
        """Start consuming messages."""
        logger.info("Starting metrics consumer...")
        
        consumer = create_consumer(
            group_id=self.group_id,
            topics=[self.topic]
        )
        
        consume_messages(
            consumer,
            self.process_message,
            batch_size=self.batch_size
        )


if __name__ == '__main__':
    # Start Prometheus metrics server
    prometheus_port = 8003
    start_http_server(prometheus_port)
    logger.info(f"Prometheus metrics available at http://0.0.0.0:{prometheus_port}/metrics")
    
    # Start consumer
    consumer = MetricsConsumer()
    consumer.run()
