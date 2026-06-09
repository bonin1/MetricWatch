import { useState, useEffect, useCallback, useMemo } from 'react';
import { io } from 'socket.io-client';
import axios from 'axios';
import MetricsChart from './components/MetricsChart';
import SentimentChart from './components/SentimentChart';
import EventFeed from './components/EventFeed';
import SystemHealth from './components/SystemHealth';
import StatCard from './components/StatCard';
import ChartPanel from './components/ChartPanel';
import './App.css';

const API_URL = import.meta.env.VITE_API_URL || (typeof window !== 'undefined' ? window.location.origin : 'http://localhost:8000');

function App() {
    const [theme, setTheme] = useState(() => localStorage.getItem('mw-theme') || 'dark');
    const [connected, setConnected] = useState(false);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [metricsData, setMetricsData] = useState([]);
    const [sentimentData, setSentimentData] = useState([]);
    const [events, setEvents] = useState([]);

    useEffect(() => {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('mw-theme', theme);
    }, [theme]);

    const bootstrap = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            await axios.get(`${API_URL}/health`, { timeout: 5000 });

            const metricTypes = ['cpu', 'memory', 'disk', 'network'];
            const [historyResults, sentimentRes, anomaliesRes] = await Promise.all([
                Promise.all(
                    metricTypes.map((t) =>
                        axios.get(`${API_URL}/api/metrics/history`, { params: { metric_type: t, hours: 3 } })
                            .catch(() => ({ data: { data: [] } }))
                    )
                ),
                axios.get(`${API_URL}/api/sentiment/recent`, { params: { limit: 100 } })
                    .catch(() => ({ data: { data: [] } })),
                axios.get(`${API_URL}/api/anomalies/recent`, { params: { limit: 20 } })
                    .catch(() => ({ data: { data: [] } })),
            ]);

            const metricsPoints = [];
            historyResults.forEach((res, idx) => {
                const metricType = metricTypes[idx];
                (res.data?.data || []).forEach((row) => {
                    metricsPoints.push({
                        data: {
                            metric_type: metricType,
                            value: row.value,
                            hostname: row.hostname,
                            timestamp: row.timestamp,
                        },
                    });
                });
            });
            metricsPoints.sort(
                (a, b) => new Date(a.data.timestamp) - new Date(b.data.timestamp)
            );
            if (metricsPoints.length) setMetricsData(metricsPoints);

            const sentiments = (sentimentRes.data?.data || []).map((doc) => ({
                data: {
                    sentiment: doc.sentiment,
                    score: doc.score,
                    text: doc.text,
                    timestamp: doc.timestamp,
                    user_id: doc.user_id,
                    platform: doc.platform,
                },
            }));
            if (sentiments.length) setSentimentData(sentiments);

            const seededEvents = [];
            metricsPoints.slice(-30).forEach((m) => {
                seededEvents.push({
                    type: 'metric',
                    timestamp: m.data.timestamp,
                    message: `${m.data.metric_type} ${Number(m.data.value).toFixed(1)}${m.data.metric_type === 'network' ? ' MB/s' : '%'}`,
                    meta: m.data,
                });
            });
            sentiments.slice(0, 30).forEach((s) => {
                seededEvents.push({
                    type: 'sentiment',
                    timestamp: s.data.timestamp,
                    message: s.data.text,
                    meta: { sentiment: s.data.sentiment, score: s.data.score },
                });
            });
            (anomaliesRes.data?.data || []).forEach((a) => {
                seededEvents.push({
                    type: 'anomaly',
                    timestamp: a.timestamp,
                    message: `${a.metric_type} spike detected (z-score ${a.z_score})`,
                    meta: { metric: a.metric_type, value: a.value },
                });
            });
            seededEvents.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
            if (seededEvents.length) setEvents(seededEvents.slice(0, 100));
        } catch {
            setError('Unable to connect to the API gateway. Ensure MetricWatch is running.');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { bootstrap(); }, [bootstrap]);

    useEffect(() => {
        const socket = io(API_URL, {
            transports: ['websocket', 'polling'],
            reconnection: true,
            reconnectionDelay: 1000,
            reconnectionAttempts: 10,
        });

        socket.on('connect', () => setConnected(true));
        socket.on('disconnect', () => setConnected(false));

        socket.on('metric_update', (data) => {
            setMetricsData((prev) => [...prev.slice(-199), data]);
            setEvents((prev) => [{
                type: data.data?.anomaly ? 'anomaly' : 'metric',
                timestamp: data.data?.timestamp || new Date().toISOString(),
                message: data.data?.anomaly
                    ? `${data.data.metric_type} anomaly — ${data.data.value.toFixed(1)}`
                    : `${data.data.metric_type} ${data.data.value.toFixed(1)}${data.data.metric_type === 'network' ? ' MB/s' : '%'}`,
                meta: data.data,
            }, ...prev.slice(0, 99)]);
        });

        socket.on('sentiment_update', (data) => {
            setSentimentData((prev) => [...prev.slice(-199), data]);
            setEvents((prev) => [{
                type: 'sentiment',
                timestamp: data.data?.timestamp || new Date().toISOString(),
                message: data.data.text,
                meta: { sentiment: data.data.sentiment, score: data.data.score },
            }, ...prev.slice(0, 99)]);
        });

        return () => socket.close();
    }, []);

    const latestMetrics = useMemo(() => {
        const map = {};
        [...metricsData].reverse().forEach((item) => {
            const t = item.data?.metric_type;
            if (t && map[t] === undefined) map[t] = item.data.value;
        });
        return map;
    }, [metricsData]);

    const anomalyCount = useMemo(() => events.filter((e) => e.type === 'anomaly').length, [events]);
    const positivePct = useMemo(() => {
        if (!sentimentData.length) return 0;
        const pos = sentimentData.filter((d) => d.data?.sentiment === 'positive').length;
        return Math.round((pos / sentimentData.length) * 100);
    }, [sentimentData]);

    const exportData = (path) => window.open(`${API_URL}${path}`, '_blank');

    return (
        <div className="app">
            <nav className="topnav">
                <div className="topnav__brand">
                    <svg className="topnav__logo" viewBox="0 0 32 32" fill="none" aria-hidden="true">
                        <rect width="32" height="32" rx="8" fill="currentColor" fillOpacity="0.1" />
                        <path d="M6 22 L10 14 L14 18 L18 10 L22 14 L26 8" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                        <circle cx="26" cy="8" r="2" fill="currentColor" />
                    </svg>
                    <div>
                        <span className="topnav__name">MetricWatch</span>
                        <span className="topnav__tag">Observability</span>
                    </div>
                </div>

                <div className="topnav__links">
                    <a href="http://localhost:3001" target="_blank" rel="noreferrer" className="topnav__link">Grafana</a>
                    <a href="http://localhost:9090" target="_blank" rel="noreferrer" className="topnav__link">Prometheus</a>
                    <a href={`${API_URL}/docs`} target="_blank" rel="noreferrer" className="topnav__link">API</a>
                </div>

                <div className="topnav__actions">
                    <div className="export-menu">
                        <button type="button" className="btn btn--outline" onClick={() => exportData('/api/export/metrics?format=csv&metric_type=cpu')}>
                            Export CSV
                        </button>
                        <button type="button" className="btn btn--outline" onClick={() => exportData('/api/export/metrics?format=json&metric_type=cpu')}>
                            Export JSON
                        </button>
                    </div>
                    <button
                        type="button"
                        className="btn btn--icon"
                        onClick={() => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))}
                        aria-label="Toggle theme"
                        title="Toggle theme"
                    >
                        {theme === 'dark' ? (
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>
                        ) : (
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
                        )}
                    </button>
                    <SystemHealth connected={connected} loading={loading} error={error} />
                </div>
            </nav>

            {error && (
                <div className="alert alert--error" role="alert">
                    <span>{error}</span>
                    <button type="button" className="btn btn--sm" onClick={bootstrap}>Retry</button>
                </div>
            )}

            <main className="main">
                <div className="stats-row">
                    <StatCard
                        label="CPU Usage"
                        value={latestMetrics.cpu != null ? latestMetrics.cpu.toFixed(1) : '—'}
                        unit={latestMetrics.cpu != null ? '%' : ''}
                        accent="blue"
                    />
                    <StatCard
                        label="Memory"
                        value={latestMetrics.memory != null ? latestMetrics.memory.toFixed(1) : '—'}
                        unit={latestMetrics.memory != null ? '%' : ''}
                        accent="green"
                    />
                    <StatCard
                        label="Positive Sentiment"
                        value={positivePct || '—'}
                        unit={positivePct ? '%' : ''}
                        accent="teal"
                    />
                    <StatCard
                        label="Anomalies"
                        value={anomalyCount}
                        delta={anomalyCount > 0 ? 'Requires attention' : 'All clear'}
                        trend={anomalyCount > 0 ? 'down' : 'up'}
                        accent={anomalyCount > 0 ? 'red' : 'neutral'}
                    />
                </div>

                <div className="content-grid">
                    <ChartPanel
                        title="Infrastructure Metrics"
                        description="Real-time CPU, memory, disk, and network throughput"
                        empty={!loading && metricsData.length === 0}
                        emptyText="Metrics will appear once producers are connected"
                    >
                        {loading ? <div className="skeleton skeleton--chart" /> : <MetricsChart data={metricsData} theme={theme} />}
                    </ChartPanel>

                    <ChartPanel
                        title="Sentiment Distribution"
                        description="AI-classified social text stream"
                        empty={!loading && sentimentData.length === 0}
                        emptyText="Sentiment data streams from the social producer"
                    >
                        {loading ? <div className="skeleton skeleton--chart" /> : <SentimentChart data={sentimentData} theme={theme} />}
                    </ChartPanel>

                    <ChartPanel
                        title="Activity Log"
                        description={`${events.length} events captured`}
                        className="panel--wide"
                    >
                        {loading ? <div className="skeleton skeleton--feed" /> : <EventFeed events={events} />}
                    </ChartPanel>
                </div>
            </main>

            <footer className="footer">
                <span>MetricWatch</span>
                <span className="footer__sep">·</span>
                <span>Kafka · Redis · PostgreSQL · MongoDB · Elasticsearch</span>
            </footer>
        </div>
    );
}

export default App;
