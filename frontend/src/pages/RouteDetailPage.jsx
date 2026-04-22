import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { exportRoute, fetchRouteById, refreshRouteWeather } from "../api/routes";
import KeyPointsPanel from "../components/KeyPointsPanel";
import LoadingState from "../components/LoadingState";
import RouteMap from "../components/RouteMap";
import TimelinePanel from "../components/TimelinePanel";
import { usePreferences } from "../hooks/usePreferences";
import { downloadBlob } from "../utils/downloads";
import {
  formatCoordinate,
  formatDateTime,
  formatDistanceKm,
  formatMetric,
  formatSpeedKmh,
  formatTemperatureC,
  summarizeWeather,
} from "../utils/formatters";

function RouteDetailPage() {
  const { routeId } = useParams();
  const { preferences } = usePreferences();
  const [route, setRoute] = useState(null);
  const [selectedSample, setSelectedSample] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadRoute() {
      try {
        const loadedRoute = await fetchRouteById(routeId);
        setRoute(loadedRoute);
        setSelectedSample(loadedRoute.sampled_points?.[0] || null);
      } catch (loadError) {
        setError(loadError.response?.data?.detail || "Could not load this route.");
      } finally {
        setIsLoading(false);
      }
    }

    loadRoute();
  }, [routeId]);

  async function handleAddKeyPoint() {
    if (!selectedSample || !route) {
      return;
    }

    setIsRefreshing(true);
    setError("");

    const currentCustomIndices = route.key_points
      .filter((point) => point.category === "custom")
      .map((point) => point.sample_index);
    const nextIndices = Array.from(new Set([...currentCustomIndices, selectedSample.index]));

    try {
      const refreshedRoute = await refreshRouteWeather(route.id, nextIndices);
      setRoute(refreshedRoute);
      setSelectedSample(
        refreshedRoute.sampled_points.find((point) => point.index === selectedSample.index) || null,
      );
    } catch (refreshError) {
      setError(refreshError.response?.data?.detail || "Could not refresh route weather.");
    } finally {
      setIsRefreshing(false);
    }
  }

  async function handleExportRoute() {
    if (!route) {
      return;
    }

    setIsExporting(true);
    setError("");
    try {
      const file = await exportRoute(route.id);
      downloadBlob(file.blob, file.filename);
    } catch (exportError) {
      setError(exportError.response?.data?.detail || "Could not export this route.");
    } finally {
      setIsExporting(false);
    }
  }

  if (isLoading) {
    return <LoadingState label="Loading route forecast..." />;
  }

  if (!route) {
    return <div className="panel empty-panel">{error || "Route not found."}</div>;
  }

  const weather = selectedSample?.weather;
  const tripPlan = route.trip_plan;

  return (
    <section className="stack">
      <div className="panel route-header-panel">
        <div>
          <p className="eyebrow">Saved route detail</p>
          <h1>{route.name}</h1>
          <p>
            Start {formatDateTime(route.start_time, preferences)} | {formatDistanceKm(route.total_distance_km, preferences)} |{" "}
            {formatSpeedKmh(route.speed_kmh, preferences)} average
          </p>
        </div>

        <div className="header-badges">
          <span className="metric-badge">{route.sample_interval_minutes} min sampling</span>
          <span className="metric-badge">{route.sampled_points_count} sampled points</span>
          {tripPlan?.daily_legs?.length ? (
            <span className="metric-badge">{tripPlan.daily_legs.length} planned days</span>
          ) : null}
          <button className="secondary-button" disabled={isExporting} onClick={handleExportRoute} type="button">
            {isExporting ? "Exporting..." : "Download route"}
          </button>
        </div>
      </div>

      {error ? <p className="form-error">{error}</p> : null}

      <div className="route-layout">
        <div className="route-main-column">
          {tripPlan ? (
            <section className="panel">
              <div className="panel-header">
                <div>
                  <p className="eyebrow">Trip planning</p>
                  <h2>Daily camp and lunch plan</h2>
                </div>
              </div>

              <div className="details-inline">
                <span>{tripPlan.options?.overnight_camps_enabled ? "Overnight camps on" : "Day route"}</span>
                {tripPlan.options?.target_distance_per_day_km ? (
                  <span>{formatDistanceKm(tripPlan.options.target_distance_per_day_km, preferences)} target per day</span>
                ) : null}
                {tripPlan.options?.plan_lunch_stops ? (
                  <span>{tripPlan.options.lunch_rest_minutes} min lunch stop</span>
                ) : null}
                {tripPlan.options?.avoid_camp_after_sunset ? <span>Sunset camp limit on</span> : null}
              </div>

              <div className="leg-grid">
                {(tripPlan.daily_legs || []).map((leg) => (
                  <article className="detail-card" key={`leg-${leg.day_number}`}>
                    <div className="keypoint-heading">
                      <div>
                        <strong>Day {leg.day_number}</strong>
                        <p>
                          {formatDistanceKm(leg.start_distance_km, preferences)} to{" "}
                          {formatDistanceKm(leg.end_distance_km, preferences)}
                        </p>
                      </div>
                      <span className="metric-badge metric-badge-soft">{leg.end_type}</span>
                    </div>
                    <p>Start {formatDateTime(leg.start_time, preferences)}</p>
                    <p>Arrive {formatDateTime(leg.end_time, preferences)}</p>
                    {leg.target_end_time ? <p>Target stop time {leg.target_end_time}</p> : null}
                    {leg.sunset_time ? <p>Sunset {formatDateTime(leg.sunset_time, preferences)}</p> : null}
                    {leg.lunch_distance_km ? (
                      <p>Lunch around {formatDistanceKm(leg.lunch_distance_km, preferences)}</p>
                    ) : null}
                  </article>
                ))}
              </div>
            </section>
          ) : null}

          <RouteMap
            onSelectSample={setSelectedSample}
            route={route}
            selectedSampleIndex={selectedSample?.index ?? 0}
          />
          <KeyPointsPanel keyPoints={route.key_points} />
        </div>

        <aside className="route-side-column">
          <section className="panel">
            <div className="panel-header">
              <div>
                <p className="eyebrow">Selected point</p>
                <h2>{selectedSample ? `Sample #${selectedSample.index + 1}` : "No point selected"}</h2>
              </div>
            </div>

            {selectedSample ? (
              <div className="detail-stack">
                <div className="detail-card">
                  <span className="detail-label">Estimated arrival</span>
                  <strong>{formatDateTime(selectedSample.timestamp, preferences)}</strong>
                </div>
                <div className="detail-card">
                  <span className="detail-label">Coordinates</span>
                  <strong>
                    {formatCoordinate(selectedSample.latitude)}, {formatCoordinate(selectedSample.longitude)}
                  </strong>
                </div>
                <div className="detail-card">
                  <span className="detail-label">Distance from start</span>
                  <strong>{formatDistanceKm(selectedSample.distance_from_start_km, preferences)}</strong>
                </div>
                <div className="detail-card">
                  <span className="detail-label">Weather snapshot</span>
                  <strong>{summarizeWeather(weather, preferences)}</strong>
                  <p>
                    Wind {weather?.wind_speed_kph ?? "--"} km/h | Cloud cover {weather?.cloud_cover_percent ?? "--"}%
                  </p>
                  <p>
                    Temperature {formatTemperatureC(weather?.temperature_c, preferences)} | Precipitation{" "}
                    {weather?.precipitation_probability ?? "--"}% / {weather?.precipitation_mm ?? "--"} mm
                  </p>
                </div>

                <button className="primary-button" disabled={isRefreshing} onClick={handleAddKeyPoint} type="button">
                  {isRefreshing ? "Refreshing forecasts..." : "Use this point for 24-hour forecast"}
                </button>
              </div>
            ) : (
              <p>Select a sampled point from the map or timeline.</p>
            )}
          </section>

          <TimelinePanel
            onSelectSample={setSelectedSample}
            points={route.sampled_points}
            selectedSampleIndex={selectedSample?.index ?? 0}
          />
        </aside>
      </div>
    </section>
  );
}

export default RouteDetailPage;
