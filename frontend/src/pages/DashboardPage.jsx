import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  deleteRoute,
  exportRoute,
  fetchRoutes,
  importRoute,
} from "../api/routes";
import LoadingState from "../components/LoadingState";
import { usePreferences } from "../hooks/usePreferences";
import { downloadBlob } from "../utils/downloads";
import { formatDateTime, formatDistanceKm, formatSpeedKmh } from "../utils/formatters";

function DashboardPage() {
  const navigate = useNavigate();
  const { preferences } = usePreferences();
  const [routes, setRoutes] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isImportingRoute, setIsImportingRoute] = useState(false);
  const [activeDownloadId, setActiveDownloadId] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadRoutes() {
      try {
        setRoutes(await fetchRoutes());
      } catch (loadError) {
        setError(loadError.response?.data?.detail || "Could not load your saved routes.");
      } finally {
        setIsLoading(false);
      }
    }

    loadRoutes();
  }, []);

  async function handleDelete(routeId) {
    const confirmed = window.confirm("Delete this saved route?");
    if (!confirmed) {
      return;
    }

    try {
      await deleteRoute(routeId);
      setRoutes((current) => current.filter((route) => route.id !== routeId));
    } catch (deleteError) {
      setError(deleteError.response?.data?.detail || "Could not delete the route.");
    }
  }

  async function handleExportRoute(routeId) {
    setError("");
    setActiveDownloadId(`route-${routeId}`);
    try {
      const file = await exportRoute(routeId);
      downloadBlob(file.blob, file.filename);
    } catch (downloadError) {
      setError(downloadError.response?.data?.detail || "Could not export that route.");
    } finally {
      setActiveDownloadId(null);
    }
  }

  async function handleImportRoute(event) {
    const routeFile = event.target.files?.[0];
    if (!routeFile) {
      return;
    }

    setError("");
    setIsImportingRoute(true);
    try {
      const importedRoute = await importRoute(routeFile);
      navigate(`/routes/${importedRoute.id}`);
    } catch (importError) {
      setError(importError.response?.data?.detail || "Could not import that shared route.");
    } finally {
      setIsImportingRoute(false);
      event.target.value = "";
    }
  }

  if (isLoading) {
    return <LoadingState label="Loading your saved routes..." />;
  }

  return (
    <section className="stack">
      <div className="panel hero-panel">
        <div>
          <p className="eyebrow">Saved route forecasts</p>
          <h1>Your routes</h1>
          <p>
            Reopen processed GPX routes to see their sampled weather timeline and key-point hourly
            outlooks.
          </p>
        </div>
        <div className="card-actions">
          <label className="secondary-button inline-button file-button">
            {isImportingRoute ? "Importing route..." : "Import shared route"}
            <input
              accept=".json,.routeweather.json"
              disabled={isImportingRoute}
              onChange={handleImportRoute}
              type="file"
            />
          </label>
          <button className="primary-button" onClick={() => navigate("/upload")} type="button">
            Upload a new route
          </button>
        </div>
      </div>

      {error ? <p className="form-error">{error}</p> : null}

      {!routes.length ? (
        <div className="panel empty-panel">
          <h2>No routes yet</h2>
          <p>Upload your first GPX file to generate a route-aware forecast timeline.</p>
          <div className="card-actions">
            <Link className="primary-button inline-button" to="/upload">
              Upload route
            </Link>
            <Link className="secondary-button inline-button" to="/gpx-library">
              Open GPX library
            </Link>
          </div>
        </div>
      ) : (
        <div className="route-list">
          {routes.map((route) => (
            <article className="route-summary-card" key={route.id}>
              <div>
                <p className="eyebrow">Saved route</p>
                <h2>{route.name}</h2>
                <p>{formatDateTime(route.start_time, preferences)}</p>
              </div>

              <dl className="metric-grid">
                <div>
                  <dt>Distance</dt>
                  <dd>{formatDistanceKm(route.total_distance_km, preferences)}</dd>
                </div>
                <div>
                  <dt>Samples</dt>
                  <dd>{route.sampled_points_count}</dd>
                </div>
                <div>
                  <dt>Speed</dt>
                  <dd>{formatSpeedKmh(route.speed_kmh, preferences)}</dd>
                </div>
                <div>
                  <dt>Interval</dt>
                  <dd>{route.sample_interval_minutes} min</dd>
                </div>
              </dl>

              <div className="card-actions">
                <Link className="secondary-button inline-button" to={`/routes/${route.id}`}>
                  Open route
                </Link>
                <button
                  className="ghost-button"
                  disabled={activeDownloadId === `route-${route.id}`}
                  onClick={() => handleExportRoute(route.id)}
                  type="button"
                >
                  {activeDownloadId === `route-${route.id}` ? "Exporting..." : "Download route"}
                </button>
                <button className="ghost-button" onClick={() => handleDelete(route.id)} type="button">
                  Delete
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

export default DashboardPage;
