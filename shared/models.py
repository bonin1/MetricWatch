"""
Pydantic data models for type safety and validation across services.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class SystemMetric(BaseModel):
    """System metrics event model."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metric_type: str  # 'cpu', 'memory', 'disk', 'network'
    value: float
    hostname: str
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SocialText(BaseModel):
    """Social text event model."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    text: str
    user_id: str
    platform: str  # 'twitter', 'facebook', 'instagram', etc.
    hashtags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SentimentResult(BaseModel):
    """Sentiment analysis result model."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    text: str
    sentiment: str  # 'positive', 'negative', 'neutral'
    score: float  # Confidence score 0-1
    user_id: str
    platform: str
    processing_time_ms: Optional[float] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MetricAggregation(BaseModel):
    """Aggregated metrics model."""
    window_start: datetime
    window_end: datetime
    window_size: str  # '1min', '5min', '15min'
    metric_type: str
    avg_value: float
    min_value: float
    max_value: float
    count: int
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class WebSocketMessage(BaseModel):
    """WebSocket message format."""
    event_type: str  # 'metric', 'sentiment', 'aggregation'
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
