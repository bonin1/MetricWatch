"""
Shared Kafka configuration and utilities for producers and consumers.
Uses confluent-kafka-python (librdkafka wrapper) for high performance.
"""
import os
import json
import logging
from datetime import date, datetime
from typing import Dict, Any, Optional, Callable
from confluent_kafka import Producer, Consumer, KafkaError, KafkaException
from confluent_kafka.admin import AdminClient, NewTopic

logger = logging.getLogger(__name__)


def get_kafka_config() -> Dict[str, str]:
    """Get base Kafka configuration from environment."""
    return {
        'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092'),
        'client.id': os.getenv('HOSTNAME', 'metricwatch-client'),
    }


def create_producer() -> Producer:
    """Create and configure a Kafka producer."""
    config = get_kafka_config()
    config.update({
        'acks': 'all',  # Wait for all replicas
        'retries': 3,
        'max.in.flight.requests.per.connection': 5,
        'compression.type': 'snappy',
        'linger.ms': 10,  # Batch messages for efficiency
        'batch.size': 16384,
    })
    
    producer = Producer(config)
    logger.info("Kafka producer created successfully")
    return producer


def create_consumer(
    group_id: str,
    topics: list,
    auto_offset_reset: str = 'earliest'
) -> Consumer:
    """Create and configure a Kafka consumer."""
    config = get_kafka_config()
    config.update({
        'group.id': group_id,
        'auto.offset.reset': auto_offset_reset,
        'enable.auto.commit': False,  # Manual commit for reliability
        'max.poll.interval.ms': int(os.getenv('CONSUMER_MAX_POLL_INTERVAL', '300000')),
        'session.timeout.ms': 30000,
        'heartbeat.interval.ms': 10000,
    })
    
    consumer = Consumer(config)
    consumer.subscribe(topics)
    logger.info(f"Kafka consumer created for group '{group_id}', topics: {topics}")
    return consumer


def _json_default(obj: Any) -> str:
    """JSON serializer for datetime objects in Kafka payloads."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def delivery_report(err: Optional[KafkaError], msg: Any) -> None:
    """Callback for producer delivery reports."""
    if err is not None:
        logger.error(f"Message delivery failed: {err}")
    else:
        logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}] @ offset {msg.offset()}")


def produce_message(
    producer: Producer,
    topic: str,
    value: Dict[str, Any],
    key: Optional[str] = None
) -> None:
    """Produce a message to Kafka topic with JSON serialization."""
    try:
        producer.produce(
            topic=topic,
            key=key.encode('utf-8') if key else None,
            value=json.dumps(value, default=_json_default).encode('utf-8'),
            callback=delivery_report
        )
        producer.poll(0)  # Trigger callbacks
    except BufferError:
        logger.warning(f"Local producer queue is full ({len(producer)} messages awaiting delivery)")
        producer.poll(1)  # Block until queue has space
        producer.produce(
            topic,
            key=key.encode('utf-8') if key else None,
            value=json.dumps(value, default=_json_default).encode('utf-8'),
            callback=delivery_report,
        )
    except Exception as e:
        logger.error(f"Failed to produce message: {e}")


def consume_messages(
    consumer: Consumer,
    process_callback: Callable[[Dict[str, Any]], None],
    batch_size: int = 1
) -> None:
    """
    Consume messages from Kafka and process them.
    
    Args:
        consumer: Kafka consumer instance
        process_callback: Function to process each message
        batch_size: Number of messages to process before committing
    """
    messages_processed = 0
    
    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            
            if msg is None:
                continue
            
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    logger.debug(f"Reached end of partition {msg.partition()}")
                else:
                    raise KafkaException(msg.error())
            else:
                try:
                    # Deserialize message
                    value = json.loads(msg.value().decode('utf-8'))
                    
                    # Process message
                    process_callback(value)
                    
                    messages_processed += 1
                    
                    # Commit offset after batch
                    if messages_processed >= batch_size:
                        consumer.commit(asynchronous=False)
                        messages_processed = 0
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode message: {e}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    
    except KeyboardInterrupt:
        logger.info("Consumer interrupted by user")
    finally:
        consumer.close()
        logger.info("Consumer closed")


def create_topics_if_not_exist(topics: list) -> None:
    """Create Kafka topics if they don't exist."""
    admin_client = AdminClient(get_kafka_config())
    
    # Get existing topics
    metadata = admin_client.list_topics(timeout=10)
    existing_topics = set(metadata.topics.keys())
    
    # Create missing topics
    new_topics = [
        NewTopic(
            topic=topic,
            num_partitions=3,
            replication_factor=1  # Adjust based on your Kafka cluster
        )
        for topic in topics
        if topic not in existing_topics
    ]
    
    if new_topics:
        fs = admin_client.create_topics(new_topics)
        for topic, f in fs.items():
            try:
                f.result()  # Wait for operation to complete
                logger.info(f"Topic '{topic}' created successfully")
            except Exception as e:
                logger.error(f"Failed to create topic '{topic}': {e}")
    else:
        logger.info("All topics already exist")
