import { usePreferences } from "../hooks/usePreferences";
import {
  formatDateTime,
  formatDistanceKm,
  formatShortTime,
  formatTemperatureC,
} from "../utils/formatters";

function KeyPointsPanel({ keyPoints }) {
  const { preferences } = usePreferences();

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">24-hour outlook</p>
          <h2>Key point forecasts</h2>
        </div>
      </div>

      <div className="keypoint-grid">
        {keyPoints.map((point) => (
          <article className="keypoint-card" key={`${point.category}-${point.label}-${point.sample_index}`}>
            <div className="keypoint-heading">
              <div>
                <h3>{point.label}</h3>
                <p>{formatDateTime(point.arrival_time, preferences)}</p>
              </div>

              <div className="badge-stack">
                <span className="metric-badge metric-badge-soft">{point.category}</span>
                <span className="metric-badge">{formatDistanceKm(point.distance_from_start_km ?? 0, preferences)}</span>
              </div>
            </div>

            {Object.keys(point.details || {}).length ? (
              <div className="details-inline">
                {point.details.day_number ? <span>Day {point.details.day_number}</span> : null}
                {point.details.rest_minutes ? <span>{point.details.rest_minutes} min rest</span> : null}
                {point.details.target_end_time ? <span>Target {point.details.target_end_time}</span> : null}
                {point.details.sunset_time ? (
                  <span>Sunset {formatDateTime(point.details.sunset_time, preferences)}</span>
                ) : null}
              </div>
            ) : null}

            <div className="forecast-strip">
              {point.forecast_24h.slice(0, 8).map((forecast) => (
                <div className="forecast-chip" key={forecast.timestamp}>
                  <strong>{formatShortTime(forecast.timestamp, preferences)}</strong>
                  <span>{formatTemperatureC(forecast.temperature_c, preferences)}</span>
                  <span>{forecast.summary}</span>
                </div>
              ))}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

export default KeyPointsPanel;
