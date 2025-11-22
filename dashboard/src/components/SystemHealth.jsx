import './SystemHealth.css';

function SystemHealth({ connected }) {
    return (
        <div className="system-health">
            <div className={`status-indicator ${connected ? 'connected' : 'disconnected'}`}>
                <span className="status-dot"></span>
                <span className="status-text">
                    {connected ? 'Connected' : 'Disconnected'}
                </span>
            </div>
        </div>
    );
}

export default SystemHealth;
