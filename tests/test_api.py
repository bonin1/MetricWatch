"""Basic API endpoint tests with mocked storage backends."""
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api-gateway"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))


@pytest.fixture
def client():
    mock_redis = AsyncMock()
    mock_redis.keys = AsyncMock(return_value=[])
    mock_redis.hgetall = AsyncMock(return_value={})
    mock_redis.lrange = AsyncMock(return_value=[])

    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[])
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

    mock_mongo = MagicMock()
    mock_mongo.__getitem__.return_value.find.return_value.sort.return_value.limit.return_value = []

    with patch("main.redis_client", mock_redis), \
         patch("main.postgres_pool", mock_pool), \
         patch("main.mongo_db", mock_mongo), \
         patch("main.es", MagicMock()), \
         patch("main.asyncio.create_task"):
        from main import app
        from fastapi.testclient import TestClient
        yield TestClient(app)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert "timestamp" in body


def test_sentiment_stats_empty(client):
    response = client.get("/api/sentiment/stats")
    assert response.status_code == 200
    body = response.json()
    assert "total" in body
    assert "distribution" in body
