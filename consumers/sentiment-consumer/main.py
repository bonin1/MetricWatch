"""
Sentiment Analysis Consumer Service
Consumes social text from Kafka, performs sentiment analysis using Hugging Face DistilBERT,
and persists results to multiple storage backends.
"""
import os
import sys
import json
import logging
import time
from datetime import datetime
from typing import List, Dict
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Add shared module to path
sys.path.append('/app/shared')
from kafka_config import create_consumer, consume_messages
from storage_clients import redis_client, mongo_client, es_client
from models import SocialText, SentimentResult
from logging_config import setup_logging
from sentiment_keyword import analyze_keyword_sentiment

logger = setup_logging("sentiment-consumer")

# Prometheus metrics
messages_processed = Counter('sentiment_consumer_messages_processed_total', 'Total messages processed')
processing_time = Histogram('sentiment_consumer_processing_seconds', 'Time spent processing messages')
model_inference_time = Histogram('sentiment_model_inference_seconds', 'Model inference time')
storage_operations = Counter('sentiment_consumer_storage_operations_total', 'Storage operations', ['backend', 'operation'])
sentiment_distribution = Counter('sentiment_distribution_total', 'Sentiment distribution', ['sentiment'])
model_loaded = Gauge('sentiment_model_loaded', 'Whether the model is loaded')


class SentimentConsumer:
    """Consumes social text and performs sentiment analysis."""
    
    def __init__(self):
        self.topic = os.getenv('KAFKA_TOPIC_SOCIAL', 'social-text')
        self.group_id = 'sentiment-consumer-group'
        self.batch_size = int(os.getenv('CONSUMER_BATCH_SIZE', '10'))
        self.model_name = os.getenv('SENTIMENT_MODEL', 'distilbert-base-uncased-finetuned-sst-2-english')
        self.sentiment_mode = os.getenv('SENTIMENT_MODE', 'transformers').lower()
        
        # Storage clients
        self.redis = redis_client.connect()
        self.mongo = mongo_client.connect()
        self.es = es_client.connect()
        
        self.sentiment_pipeline = None
        if self.sentiment_mode == 'keyword':
            model_loaded.set(1)
            logger.info("Using lightweight keyword sentiment mode (no ML model)")
        else:
            logger.info(f"Loading sentiment model: {self.model_name}")
            self.load_model()
        
        logger.info(f"SentimentConsumer initialized - Topic: {self.topic}, Group: {self.group_id}")
    
    def load_model(self):
        """Load Hugging Face sentiment analysis model."""
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline

            device = 0 if torch.cuda.is_available() else -1
            tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            self.sentiment_pipeline = pipeline(
                'sentiment-analysis',
                model=model,
                tokenizer=tokenizer,
                device=device,
                truncation=True,
                max_length=512
            )
            self.sentiment_pipeline("This is a test sentence.")
            model_loaded.set(1)
            logger.info(f"Model loaded successfully (device: {'GPU' if device == 0 else 'CPU'})")
        except Exception as e:
            logger.error(f"Failed to load model, falling back to keyword mode: {e}")
            self.sentiment_mode = 'keyword'
            self.sentiment_pipeline = None
            model_loaded.set(1)
    
    @model_inference_time.time()
    def analyze_sentiment(self, text: str) -> tuple:
        """Analyze sentiment using transformers or keyword mode."""
        if self.sentiment_mode == 'keyword' or self.sentiment_pipeline is None:
            return analyze_keyword_sentiment(text)
        try:
            result = self.sentiment_pipeline(text)[0]
            label = result['label'].lower()
            score = result['score']
            if label == 'positive':
                sentiment = 'positive'
            elif label == 'negative':
                sentiment = 'negative'
            else:
                sentiment = 'positive' if score > 0.5 else 'negative'
            if score < 0.6:
                sentiment = 'neutral'
            return sentiment, score
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return analyze_keyword_sentiment(text)
    
    def store_to_mongodb(self, result: SentimentResult):
        """Store sentiment result to MongoDB."""
        try:
            collection = self.mongo['sentiment_results']
            doc = result.model_dump()
            doc['timestamp'] = result.timestamp  # Keep as datetime for MongoDB
            
            collection.insert_one(doc)
            storage_operations.labels(backend='mongodb', operation='insert').inc()
            logger.debug(f"Stored result to MongoDB: {result.sentiment}")
        except Exception as e:
            logger.error(f"Failed to store to MongoDB: {e}")
    
    def store_to_elasticsearch(self, result: SentimentResult):
        """Index sentiment result to Elasticsearch."""
        try:
            doc = {
                'timestamp': result.timestamp.isoformat(),
                'text': result.text,
                'sentiment': result.sentiment,
                'score': result.score,
                'user_id': result.user_id,
                'platform': result.platform,
                'processing_time_ms': result.processing_time_ms
            }
            
            self.es.index(index='sentiment', document=doc)
            storage_operations.labels(backend='elasticsearch', operation='index').inc()
            logger.debug(f"Indexed result to Elasticsearch: {result.sentiment}")
        except Exception as e:
            logger.error(f"Failed to index to Elasticsearch: {e}")
    
    def publish_to_websocket(self, result: SentimentResult):
        """Publish sentiment result to Redis pub/sub for WebSocket gateway."""
        try:
            message = {
                'event_type': 'sentiment',
                'data': {
                    'text': result.text[:100],  # Truncate for WebSocket
                    'sentiment': result.sentiment,
                    'score': result.score,
                    'user_id': result.user_id,
                    'platform': result.platform,
                    'timestamp': result.timestamp.isoformat()
                }
            }
            self.redis.publish('websocket:sentiment', json.dumps(message))
            logger.debug(f"Published to WebSocket channel: {result.sentiment}")
        except Exception as e:
            logger.error(f"Failed to publish to WebSocket: {e}")
    
    def update_sentiment_stats(self, sentiment: str):
        """Update sentiment statistics in Redis."""
        try:
            # Increment sentiment counter
            self.redis.hincrby('sentiment:stats', sentiment, 1)
            
            # Update recent sentiment list (keep last 100)
            self.redis.lpush('sentiment:recent', sentiment)
            self.redis.ltrim('sentiment:recent', 0, 99)
            
            logger.debug(f"Updated sentiment stats: {sentiment}")
        except Exception as e:
            logger.error(f"Failed to update sentiment stats: {e}")
    
    @processing_time.time()
    def process_message(self, message: dict):
        """Process a single social text message."""
        try:
            # Parse message
            social_text = SocialText(**message)
            
            # Perform sentiment analysis
            start_time = time.time()
            sentiment, score = self.analyze_sentiment(social_text.text)
            processing_time_ms = (time.time() - start_time) * 1000
            
            # Create result
            result = SentimentResult(
                timestamp=social_text.timestamp,
                text=social_text.text,
                sentiment=sentiment,
                score=score,
                user_id=social_text.user_id,
                platform=social_text.platform,
                processing_time_ms=processing_time_ms
            )
            
            # Store to all backends
            self.store_to_mongodb(result)
            self.store_to_elasticsearch(result)
            
            # Publish to WebSocket
            self.publish_to_websocket(result)
            
            # Update statistics
            self.update_sentiment_stats(sentiment)
            sentiment_distribution.labels(sentiment=sentiment).inc()
            
            messages_processed.inc()
            logger.info(f"Processed text from {social_text.user_id}: {sentiment} ({score:.2f}) - {social_text.text[:50]}...")
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def run(self):
        """Start consuming messages."""
        logger.info("Starting sentiment consumer...")
        
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
    prometheus_port = 8004
    start_http_server(prometheus_port)
    logger.info(f"Prometheus metrics available at http://0.0.0.0:{prometheus_port}/metrics")
    
    # Start consumer
    consumer = SentimentConsumer()
    consumer.run()
