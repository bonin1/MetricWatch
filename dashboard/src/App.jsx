import { useState, useEffect } from 'react';
import { io } from 'socket.io-client';
import MetricsChart from './components/MetricsChart';
import SentimentChart from './components/SentimentChart';
import EventFeed from './components/EventFeed';
import SystemHealth from './components/SystemHealth';
import './App.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function App() {
    const [socket, setSocket] = useState(null);
    const [connected, setConnected] = useState(false);
    const [metricsData, setMetricsData] = useState([]);
    const [sentimentData, setSentimentData] = useState([]);
    const [events, setEvents] = useState([]);

    useEffect(() => {
        // Initialize Socket.IO connection
        const newSocket = io(API_URL, {
            transports: ['websocket', 'polling'],
            reconnection: true,
            reconnectionDelay: 1000,
            reconnectionAttempts: 10
        });

        newSocket.on('connect', () => {
            console.log('WebSocket connected');
            setConnected(true);
        });

        newSocket.on('disconnect', () => {
            console.log('WebSocket disconnected');
            setConnected(false);
        });

        newSocket.on('metric_update', (data) => {
            console.log('Metric update:', data);
            setMetricsData(prev => [...prev.slice(-99), data]);
            setEvents(prev => [{
                type: 'metric',
                timestamp: new Date().toISOString(),
                message: `${data.data.metric_type}: ${data.data.value.toFixed(2)}`
            }, ...prev.slice(0, 49)]);
        });

        newSocket.on('sentiment_update', (data) => {
            console.log('Sentiment update:', data);
            setSentimentData(prev => [...prev.slice(-99), data]);
            setEvents(prev => [{
                type: 'sentiment',
                timestamp: new Date().toISOString(),
                message: `${data.data.sentiment} (${(data.data.score * 100).toFixed(0)}%): ${data.data.text}`
            }, ...prev.slice(0, 49)]);
        });

        setSocket(newSocket);

        return () => {
            newSocket.close();
        };
    }, []);

    return (
        <div className="app">
            <header className="app-header">
                <h1>🚀 MetricWatch</h1>
                <p className="subtitle">Real-time Microservices Monitoring Dashboard</p>
                <SystemHealth connected={connected} />
            </header>

            <main className="dashboard-grid">
                <div className="card metrics-card">
                    <h2>📊 System Metrics</h2>
                    <MetricsChart data={metricsData} />
                </div>

                <div className="card sentiment-card">
                    <h2>💬 Sentiment Analysis</h2>
                    <SentimentChart data={sentimentData} />
                </div>

                <div className="card events-card">
                    <h2>📡 Live Event Feed</h2>
                    <EventFeed events={events} />
                </div>
            </main>

            <footer className="app-footer">
                <p>Powered by Kafka • Redis • MongoDB • PostgreSQL • Elasticsearch • DistilBERT</p>
            </footer>
        </div>
    );
}

export default App;
