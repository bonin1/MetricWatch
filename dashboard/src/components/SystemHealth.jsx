import './SystemHealth.css';

function SystemHealth({ connected, loading, error }) {
    const state = error ? 'error' : loading ? 'loading' : connected ? 'connected' : 'disconnected';
    const label = error ? 'API Error' : loading ? 'Loading…' : connected ? 'Live' : 'Offline';

    return (
        <div className="system-health">
            <div className={`status-indicator ${state}`}>
                <span className="status-dot"></span>
                <span className="status-text">{label}</span>
            </div>
        </div>
    );
}

export default SystemHealth;
