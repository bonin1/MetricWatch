import './EventFeed.css';

function EventFeed({ events }) {
    const getEventIcon = (type) => {
        switch (type) {
            case 'metric':
                return '📊';
            case 'sentiment':
                return '💬';
            default:
                return '📡';
        }
    };

    const getEventClass = (type) => {
        return `event-item event-${type}`;
    };

    const formatTimestamp = (timestamp) => {
        const date = new Date(timestamp);
        return date.toLocaleTimeString();
    };

    return (
        <div className="event-feed">
            {events.length === 0 ? (
                <div className="no-events">
                    <p>Waiting for events...</p>
                    <div className="pulse-loader"></div>
                </div>
            ) : (
                <div className="events-list">
                    {events.map((event, index) => (
                        <div key={index} className={getEventClass(event.type)}>
                            <span className="event-icon">{getEventIcon(event.type)}</span>
                            <div className="event-content">
                                <div className="event-message">{event.message}</div>
                                <div className="event-time">{formatTimestamp(event.timestamp)}</div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

export default EventFeed;
