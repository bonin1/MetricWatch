"""
API Gateway with WebSocket Support
Provides REST API endpoints and WebSocket server for real-time updates.
"""
import os
import json
import csv
import io
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
import socketio
from prometheus_client import Counter, Histogram, Gauge, make_asgi_app
import redis.asyncio as aioredis

import sys
sys.path.append('/app/shared')
from storage_clients import mongo_client, postgres_client, es_client
from logging_config import setup_logging

logger = setup_logging("api-gateway")

# Prometheus metrics
api_requests = Counter('api_requests_total', 'Total API requests', ['endpoint', 'method'])
api_latency = Histogram('api_request_duration_seconds', 'API request latency', ['endpoint'])
websocket_connections = Gauge('websocket_connections', 'Active WebSocket connections')

# FastAPI app
app = FastAPI(title="MetricWatch API Gateway", version="1.0.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Socket.IO server
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    logger=True,
    engineio_logger=False
)
socket_app = socketio.ASGIApp(sio, app)

# Storage clients
mongo_db = None
postgres_pool = None
es = None
redis_client = None


@app.on_event("startup")
async def startup_event():
    """Initialize storage connections and start WebSocket listener."""
    global mongo_db, postgres_pool, es, redis_client
    
    logger.info("Initializing storage connections...")
    
    # Connect to storage backends
    mongo_db = mongo_client.connect()
    postgres_pool = await postgres_client.connect()
    es = es_client.connect()
    
    # Connect to Redis for pub/sub
    redis_host = os.getenv('REDIS_HOST', 'redis')
    redis_port = int(os.getenv('REDIS_PORT', '6379'))
    redis_client = await aioredis.from_url(f"redis://{redis_host}:{redis_port}")
    
    logger.info("Storage connections initialized")
    
    # Start WebSocket event listener
    asyncio.create_task(websocket_event_listener())


@app.on_event("shutdown")
async def shutdown_event():
    """Close storage connections."""
    logger.info("Closing storage connections...")
    
    if redis_client:
        await redis_client.close()
    if postgres_pool:
        await postgres_client.close()
    if mongo_db:
        mongo_client.close()
    if es:
        es_client.close()


# WebSocket Event Handlers
@sio.event
async def connect(sid, environ):
    """Handle WebSocket connection."""
    websocket_connections.inc()
    logger.info(f"Client connected: {sid}")


@sio.event
async def disconnect(sid):
    """Handle WebSocket disconnection."""
    websocket_connections.dec()
    logger.info(f"Client disconnected: {sid}")


async def websocket_event_listener():
    """Listen to Redis pub/sub and broadcast to WebSocket clients."""
    logger.info("Starting WebSocket event listener...")
    
    pubsub = redis_client.pubsub()
    await pubsub.subscribe('websocket:metrics', 'websocket:sentiment')
    
    try:
        async for message in pubsub.listen():
            if message['type'] == 'message':
                channel = message['channel'].decode('utf-8')
                data = json.loads(message['data'].decode('utf-8'))
                
                # Broadcast to appropriate namespace
                if channel == 'websocket:metrics':
                    await sio.emit('metric_update', data)
                elif channel == 'websocket:sentiment':
                    await sio.emit('sentiment_update', data)
                    
    except Exception as e:
        logger.error(f"WebSocket listener error: {e}")


# REST API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/metrics/latest")
@api_latency.labels(endpoint='/api/metrics/latest').time()
async def get_latest_metrics():
    """Get latest metrics from Redis."""
    api_requests.labels(endpoint='/api/metrics/latest', method='GET').inc()
    
    try:
        # Get all latest metric keys
        keys = await redis_client.keys("metrics:latest:*")
        
        metrics = {}
        for key in keys:
            value = await redis_client.get(key)
            if value:
                key_parts = key.decode('utf-8').split(':')
                hostname = key_parts[2]
                metric_type = key_parts[3]
                
                if hostname not in metrics:
                    metrics[hostname] = {}
                
                metrics[hostname][metric_type] = json.loads(value)
        
        return {"metrics": metrics}
        
    except Exception as e:
        logger.error(f"Failed to get latest metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/metrics/history")
@api_latency.labels(endpoint='/api/metrics/history').time()
async def get_metrics_history(
    metric_type: str = Query(..., description="Metric type (cpu, memory, disk, network)"),
    hours: int = Query(1, description="Number of hours of history")
):
    """Get historical metrics from PostgreSQL."""
    api_requests.labels(endpoint='/api/metrics/history', method='GET').inc()
    
    try:
        since = datetime.utcnow() - timedelta(hours=hours)
        
        async with postgres_pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT timestamp, hostname, value, metadata
                FROM metrics_timeseries
                WHERE metric_type = $1 AND timestamp >= $2
                ORDER BY timestamp DESC
                LIMIT 1000
            ''', metric_type, since)
        
        metrics = [
            {
                'timestamp': row['timestamp'].isoformat(),
                'hostname': row['hostname'],
                'value': row['value'],
                'metadata': row['metadata']
            }
            for row in rows
        ]
        
        return {"metric_type": metric_type, "count": len(metrics), "data": metrics}
        
    except Exception as e:
        logger.error(f"Failed to get metrics history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/metrics/aggregated")
@api_latency.labels(endpoint='/api/metrics/aggregated').time()
async def get_aggregated_metrics(
    window_size: str = Query("5min", description="Window size (1min, 5min, 15min)"),
    hours: int = Query(1, description="Number of hours of history")
):
    """Get aggregated metrics from PostgreSQL."""
    api_requests.labels(endpoint='/api/metrics/aggregated', method='GET').inc()
    
    try:
        since = datetime.utcnow() - timedelta(hours=hours)
        
        async with postgres_pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT window_start, window_end, metric_type, avg_value, min_value, max_value, count
                FROM metrics_aggregated
                WHERE window_size = $1 AND window_start >= $2
                ORDER BY window_start DESC
            ''', window_size, since)
        
        aggregations = [
            {
                'window_start': row['window_start'].isoformat(),
                'window_end': row['window_end'].isoformat(),
                'metric_type': row['metric_type'],
                'avg_value': row['avg_value'],
                'min_value': row['min_value'],
                'max_value': row['max_value'],
                'count': row['count']
            }
            for row in rows
        ]
        
        return {"window_size": window_size, "count": len(aggregations), "data": aggregations}
        
    except Exception as e:
        logger.error(f"Failed to get aggregated metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sentiment/recent")
@api_latency.labels(endpoint='/api/sentiment/recent').time()
async def get_recent_sentiment(
    limit: int = Query(100, description="Number of results to return")
):
    """Get recent sentiment results from MongoDB."""
    api_requests.labels(endpoint='/api/sentiment/recent', method='GET').inc()
    
    try:
        collection = mongo_db['sentiment_results']
        cursor = collection.find().sort('timestamp', -1).limit(limit)
        
        results = []
        for doc in cursor:
            doc['_id'] = str(doc['_id'])  # Convert ObjectId to string
            doc['timestamp'] = doc['timestamp'].isoformat()
            results.append(doc)
        
        return {"count": len(results), "data": results}
        
    except Exception as e:
        logger.error(f"Failed to get recent sentiment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sentiment/stats")
@api_latency.labels(endpoint='/api/sentiment/stats').time()
async def get_sentiment_stats():
    """Get sentiment statistics from Redis."""
    api_requests.labels(endpoint='/api/sentiment/stats', method='GET').inc()
    
    try:
        # Get sentiment counts
        stats = await redis_client.hgetall('sentiment:stats')
        
        # Convert bytes to strings and int
        sentiment_counts = {
            k.decode('utf-8'): int(v.decode('utf-8'))
            for k, v in stats.items()
        }
        
        # Get recent sentiment list
        recent = await redis_client.lrange('sentiment:recent', 0, 99)
        recent_sentiments = [s.decode('utf-8') for s in recent]
        
        # Calculate distribution
        total = sum(sentiment_counts.values())
        distribution = {
            k: round(v / total * 100, 2) if total > 0 else 0
            for k, v in sentiment_counts.items()
        }
        
        return {
            "total": total,
            "counts": sentiment_counts,
            "distribution": distribution,
            "recent": recent_sentiments
        }
        
    except Exception as e:
        logger.error(f"Failed to get sentiment stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/anomalies/recent")
@api_latency.labels(endpoint='/api/anomalies/recent').time()
async def get_recent_anomalies(limit: int = Query(50, ge=1, le=100)):
    """Get recent metric anomalies from Redis."""
    api_requests.labels(endpoint='/api/anomalies/recent', method='GET').inc()
    try:
        raw = await redis_client.lrange('anomalies:recent', 0, limit - 1)
        anomalies = [json.loads(item.decode('utf-8')) for item in raw]
        return {"count": len(anomalies), "data": anomalies}
    except Exception as e:
        logger.error(f"Failed to get anomalies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/export/metrics")
@api_latency.labels(endpoint='/api/export/metrics').time()
async def export_metrics(
    format: str = Query("json", pattern="^(json|csv)$"),
    metric_type: str = Query("cpu"),
    hours: int = Query(1, ge=1, le=168),
):
    """Export historical metrics as JSON or CSV."""
    api_requests.labels(endpoint='/api/export/metrics', method='GET').inc()
    since = datetime.utcnow() - timedelta(hours=hours)
    try:
        async with postgres_pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT timestamp, hostname, metric_type, value, metadata
                FROM metrics_timeseries
                WHERE metric_type = $1 AND timestamp >= $2
                ORDER BY timestamp DESC
                LIMIT 5000
            ''', metric_type, since)

        records = [
            {
                'timestamp': row['timestamp'].isoformat(),
                'hostname': row['hostname'],
                'metric_type': row['metric_type'],
                'value': row['value'],
                'metadata': row['metadata'],
            }
            for row in rows
        ]

        if format == 'json':
            return JSONResponse(
                content={"metric_type": metric_type, "count": len(records), "data": records},
                headers={"Content-Disposition": f'attachment; filename="metrics-{metric_type}.json"'},
            )

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=['timestamp', 'hostname', 'metric_type', 'value'])
        writer.writeheader()
        for r in records:
            writer.writerow({k: r[k] for k in ['timestamp', 'hostname', 'metric_type', 'value']})
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type='text/csv',
            headers={"Content-Disposition": f'attachment; filename="metrics-{metric_type}.csv"'},
        )
    except Exception as e:
        logger.error(f"Failed to export metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/export/sentiment")
@api_latency.labels(endpoint='/api/export/sentiment').time()
async def export_sentiment(format: str = Query("json", pattern="^(json|csv)$"), limit: int = Query(500, ge=1, le=5000)):
    """Export recent sentiment results as JSON or CSV."""
    api_requests.labels(endpoint='/api/export/sentiment', method='GET').inc()
    try:
        collection = mongo_db['sentiment_results']
        cursor = collection.find().sort('timestamp', -1).limit(limit)
        records = []
        for doc in cursor:
            records.append({
                'timestamp': doc['timestamp'].isoformat(),
                'text': doc['text'],
                'sentiment': doc['sentiment'],
                'score': doc['score'],
                'user_id': doc.get('user_id', ''),
                'platform': doc.get('platform', ''),
            })

        if format == 'json':
            return JSONResponse(
                content={"count": len(records), "data": records},
                headers={"Content-Disposition": 'attachment; filename="sentiment.json"'},
            )

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=['timestamp', 'text', 'sentiment', 'score', 'user_id', 'platform'])
        writer.writeheader()
        writer.writerows(records)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type='text/csv',
            headers={"Content-Disposition": 'attachment; filename="sentiment.csv"'},
        )
    except Exception as e:
        logger.error(f"Failed to export sentiment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/search")
@api_latency.labels(endpoint='/api/search').time()
async def search(
    index: str = Query(..., description="Index to search (metrics, sentiment)"),
    query: str = Query(..., description="Search query"),
    size: int = Query(50, description="Number of results")
):
    """Search Elasticsearch indices."""
    api_requests.labels(endpoint='/api/search', method='GET').inc()
    
    try:
        body = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["*"]
                }
            },
            "size": size,
            "sort": [{"timestamp": {"order": "desc"}}]
        }
        
        response = es.search(index=index, body=body)
        
        hits = [hit['_source'] for hit in response['hits']['hits']]
        
        return {
            "index": index,
            "query": query,
            "total": response['hits']['total']['value'],
            "count": len(hits),
            "data": hits
        }
        
    except Exception as e:
        logger.error(f"Failed to search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Mount Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv('API_PORT', '8000'))
    uvicorn.run(socket_app, host="0.0.0.0", port=port, log_level="info")
