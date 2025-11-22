"""
Storage client managers for Redis, MongoDB, PostgreSQL, and Elasticsearch.
Provides connection pooling and async support where applicable.
"""
import os
import logging
from typing import Optional, Dict, Any, List
import redis
from pymongo import MongoClient
import asyncpg
from elasticsearch import Elasticsearch, helpers as es_helpers

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client with connection pooling."""
    
    def __init__(self):
        self.host = os.getenv('REDIS_HOST', 'redis')
        self.port = int(os.getenv('REDIS_PORT', '6379'))
        self.db = int(os.getenv('REDIS_DB', '0'))
        self.client = None
        
    def connect(self) -> redis.Redis:
        """Create Redis connection with pool."""
        if self.client is None:
            pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                db=self.db,
                decode_responses=True,
                max_connections=10
            )
            self.client = redis.Redis(connection_pool=pool)
            logger.info(f"Connected to Redis at {self.host}:{self.port}")
        return self.client
    
    def close(self):
        """Close Redis connection."""
        if self.client:
            self.client.close()
            logger.info("Redis connection closed")


class MongoDBClient:
    """MongoDB client wrapper."""
    
    def __init__(self):
        self.host = os.getenv('MONGO_HOST', 'mongo')
        self.port = int(os.getenv('MONGO_PORT', '27017'))
        self.db_name = os.getenv('MONGO_DB', 'metricwatch')
        self.user = os.getenv('MONGO_USER', 'metricwatch')
        self.password = os.getenv('MONGO_PASSWORD', 'metricwatch123')
        self.client = None
        self.db = None
        
    def connect(self) -> MongoClient:
        """Create MongoDB connection."""
        if self.client is None:
            connection_string = f"mongodb://{self.user}:{self.password}@{self.host}:{self.port}/"
            self.client = MongoClient(connection_string)
            self.db = self.client[self.db_name]
            logger.info(f"Connected to MongoDB at {self.host}:{self.port}")
        return self.db
    
    def close(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")


class PostgresClient:
    """PostgreSQL async client with connection pooling."""
    
    def __init__(self):
        self.host = os.getenv('POSTGRES_HOST', 'postgres')
        self.port = int(os.getenv('POSTGRES_PORT', '5432'))
        self.database = os.getenv('POSTGRES_DB', 'metricwatch')
        self.user = os.getenv('POSTGRES_USER', 'metricwatch')
        self.password = os.getenv('POSTGRES_PASSWORD', 'metricwatch123')
        self.pool = None
        
    async def connect(self) -> asyncpg.Pool:
        """Create PostgreSQL connection pool."""
        if self.pool is None:
            self.pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                min_size=2,
                max_size=10
            )
            logger.info(f"Connected to PostgreSQL at {self.host}:{self.port}")
        return self.pool
    
    async def close(self):
        """Close PostgreSQL connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("PostgreSQL connection pool closed")


class ElasticsearchClient:
    """Elasticsearch client wrapper."""
    
    def __init__(self):
        self.host = os.getenv('ELASTICSEARCH_HOST', 'elasticsearch')
        self.port = int(os.getenv('ELASTICSEARCH_PORT', '9200'))
        self.client = None
        
    def connect(self) -> Elasticsearch:
        """Create Elasticsearch connection."""
        if self.client is None:
            self.client = Elasticsearch(
                [f"http://{self.host}:{self.port}"],
                request_timeout=30,
                max_retries=3,
                retry_on_timeout=True
            )
            logger.info(f"Connected to Elasticsearch at {self.host}:{self.port}")
            
            # Create indices if they don't exist
            self._create_indices()
            
        return self.client
    
    def _create_indices(self):
        """Create Elasticsearch indices with mappings."""
        indices = {
            'metrics': {
                'mappings': {
                    'properties': {
                        'timestamp': {'type': 'date'},
                        'metric_type': {'type': 'keyword'},
                        'value': {'type': 'double'},
                        'hostname': {'type': 'keyword'},
                        'metadata': {'type': 'object'}
                    }
                }
            },
            'sentiment': {
                'mappings': {
                    'properties': {
                        'timestamp': {'type': 'date'},
                        'text': {'type': 'text'},
                        'sentiment': {'type': 'keyword'},
                        'score': {'type': 'float'},
                        'user_id': {'type': 'keyword'},
                        'platform': {'type': 'keyword'}
                    }
                }
            }
        }
        
        for index_name, index_body in indices.items():
            try:
                if not self.client.indices.exists(index=index_name):
                    # ES 8.x uses kwargs instead of body parameter
                    self.client.indices.create(index=index_name, **index_body)
                    logger.info(f"Created Elasticsearch index: {index_name}")
            except Exception as e:
                logger.warning(f"Could not create index {index_name}: {e}")
    
    def bulk_index(self, index: str, documents: List[Dict[str, Any]]):
        """Bulk index documents to Elasticsearch."""
        actions = [
            {
                '_index': index,
                '_source': doc
            }
            for doc in documents
        ]
        
        if actions:
            success, failed = es_helpers.bulk(self.client, actions, raise_on_error=False)
            logger.debug(f"Bulk indexed {success} documents to {index}, {failed} failed")
    
    def close(self):
        """Close Elasticsearch connection."""
        if self.client:
            self.client.close()
            logger.info("Elasticsearch connection closed")


# Singleton instances
redis_client = RedisClient()
mongo_client = MongoDBClient()
postgres_client = PostgresClient()
es_client = ElasticsearchClient()
