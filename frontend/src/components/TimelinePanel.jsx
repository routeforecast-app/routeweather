import { usePreferences } from "../hooks/usePreferences";
import { formatDateTime, formatDistanceKm, formatTemperatureC } from "../utils/formatters";

function TimelinePanel({ points, selectedSampleIndex, onSelectSample }) {
  const { preferences } = usePreferences();

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Timeline</p>
          <h2>Sampled route points</h2>
        </div>
      </div>

      <div className="timeline-list">
        {points.map((point) => {
          const isActive = point.index === selectedSampleIndex;
          return (
            <button
              className={`timeline-item ${isActive ? "timeline-item-active" : ""}`}
              key={point.index}
              onClick={() => onSelectSample(point)}
              type="button"
            >
              <div>
                <strong>#{point.index + 1}</strong>
                <p>{formatDateTime(point.timestamp, preferences)}</p>
              </div>
              <div>
                <p>{formatDistanceKm(point.distance_from_start_km, preferences)}</p>
                <p>{formatTemperatureC(point.weather?.temperature_c, preferences)}</p>
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}

export default TimelinePanel;
