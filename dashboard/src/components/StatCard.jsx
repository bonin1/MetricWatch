function StatCard({ label, value, unit, delta, trend, accent }) {
    return (
        <div className={`stat-card ${accent ? `stat-card--${accent}` : ''}`}>
            <span className="stat-card__label">{label}</span>
            <div className="stat-card__row">
                <span className="stat-card__value">{value}</span>
                {unit && <span className="stat-card__unit">{unit}</span>}
            </div>
            {delta != null && (
                <span className={`stat-card__delta stat-card__delta--${trend || 'neutral'}`}>
                    {delta}
                </span>
            )}
        </div>
    );
}

export default StatCard;
