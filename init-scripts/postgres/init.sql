-- Create metrics time-series table
CREATE TABLE IF NOT EXISTS metrics_timeseries (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    metric_type VARCHAR(50) NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    hostname VARCHAR(255),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for time-based queries
CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics_timeseries(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_type ON metrics_timeseries(metric_type);

-- Create aggregated metrics table
CREATE TABLE IF NOT EXISTS metrics_aggregated (
    id SERIAL PRIMARY KEY,
    window_start TIMESTAMP NOT NULL,
    window_end TIMESTAMP NOT NULL,
    window_size VARCHAR(10) NOT NULL, -- '1min', '5min', '15min'
    metric_type VARCHAR(50) NOT NULL,
    avg_value DOUBLE PRECISION,
    min_value DOUBLE PRECISION,
    max_value DOUBLE PRECISION,
    count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(window_start, window_size, metric_type)
);

CREATE INDEX IF NOT EXISTS idx_aggregated_window ON metrics_aggregated(window_start DESC, window_size);
