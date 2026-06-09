function ChartPanel({ title, description, children, empty, emptyText, className = '' }) {
    return (
        <section className={`panel ${className}`.trim()}>
            <header className="panel__header">
                <div>
                    <h2 className="panel__title">{title}</h2>
                    {description && <p className="panel__desc">{description}</p>}
                </div>
            </header>
            <div className="panel__body">
                {empty ? (
                    <div className="panel__empty">
                        <div className="panel__empty-icon" aria-hidden="true">
                            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                                <path d="M3 3v18h18" strokeLinecap="round" />
                                <path d="M7 14l4-4 4 4 5-6" strokeLinecap="round" strokeLinejoin="round" />
                            </svg>
                        </div>
                        <p>{emptyText || 'Waiting for live data…'}</p>
                    </div>
                ) : children}
            </div>
        </section>
    );
}

export default ChartPanel;
