import './EventFeed.css';

const TYPE_LABELS = {
    metric: 'Metric',
    sentiment: 'Sentiment',
    anomaly: 'Anomaly',
};

function EventFeed({ events }) {
    const formatTime = (ts) => {
        try {
            return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        } catch {
            return '—';
        }
    };

    if (events.length === 0) {
        return (
            <div className="feed feed--empty">
                <div className="feed__pulse" aria-hidden="true" />
                <p className="feed__empty-title">No events yet</p>
                <p className="feed__empty-desc">Live metrics and sentiment updates will stream here</p>
            </div>
        );
    }

    return (
        <div className="feed">
            <table className="feed__table">
                <thead>
                    <tr>
                        <th>Type</th>
                        <th>Event</th>
                        <th>Time</th>
                    </tr>
                </thead>
                <tbody>
                    {events.map((event, i) => (
                        <tr key={`${event.timestamp}-${i}`} className={`feed__row feed__row--${event.type}`}>
                            <td>
                                <span className={`feed__badge feed__badge--${event.type}`}>
                                    {TYPE_LABELS[event.type] || 'Event'}
                                </span>
                            </td>
                            <td className="feed__message">
                                {event.type === 'sentiment' && event.meta ? (
                                    <>
                                        <span className={`feed__sentiment feed__sentiment--${event.meta.sentiment}`}>
                                            {event.meta.sentiment}
                                        </span>
                                        <span className="feed__text">{event.message}</span>
                                    </>
                                ) : (
                                    event.message
                                )}
                            </td>
                            <td className="feed__time">{formatTime(event.timestamp)}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

export default EventFeed;
