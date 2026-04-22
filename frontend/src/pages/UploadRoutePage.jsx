import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import RouteBuilderMap from "../components/RouteBuilderMap";
import { createManualRoute, fetchGpxFiles, previewManualRoute, uploadRoute } from "../api/routes";
import { toDateTimeLocalValue, toOffsetIsoString } from "../utils/dateHelpers";

const DEFAULT_START = toDateTimeLocalValue(new Date(Date.now() + 60 * 60 * 1000));

function UploadRoutePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [formState, setFormState] = useState({
    name: "",
    start_time: DEFAULT_START,
    speed_kmh: 5,
    sample_interval_minutes: 30,
    overnight_camps_enabled: false,
    target_distance_per_day_km: "",
    target_time_to_camp: "18:00",
    target_time_to_destination: "15:00",
    plan_lunch_stops: false,
    lunch_rest_minutes: 45,
    avoid_camp_after_sunset: false,
    gpx_source: "upload",
    saved_gpx_file_id: "",
    manual_mode: "endpoints",
    gpx_file: null,
  });
  const [savedGpxFiles, setSavedGpxFiles] = useState([]);
  const [manualWaypoints, setManualWaypoints] = useState([]);
  const [manualPreview, setManualPreview] = useState(null);
  const [manualPreviewError, setManualPreviewError] = useState("");
  const [isLoadingSavedGpx, setIsLoadingSavedGpx] = useState(true);
  const [isLoadingManualPreview, setIsLoadingManualPreview] = useState(false);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const requestedSavedGpxId = searchParams.get("savedGpx");

  useEffect(() => {
    async function loadSavedGpxFiles() {
      try {
        const files = await fetchGpxFiles();
        setSavedGpxFiles(files);
      } catch (loadError) {
        setError(loadError.response?.data?.detail || "Could not load your saved GPX library.");
      } finally {
        setIsLoadingSavedGpx(false);
      }
    }

    loadSavedGpxFiles();
  }, []);

  useEffect(() => {
    if (!requestedSavedGpxId || !savedGpxFiles.length) {
      return;
    }

    const matchingFile = savedGpxFiles.find((file) => String(file.id) === requestedSavedGpxId);
    if (!matchingFile) {
      return;
    }

    setFormState((current) => ({
      ...current,
      gpx_source: "saved",
      saved_gpx_file_id: String(matchingFile.id),
    }));
  }, [requestedSavedGpxId, savedGpxFiles]);

  const selectedSavedGpx = useMemo(
    () => savedGpxFiles.find((file) => String(file.id) === formState.saved_gpx_file_id) || null,
    [formState.saved_gpx_file_id, savedGpxFiles],
  );

  useEffect(() => {
    if (formState.gpx_source !== "manual") {
      return;
    }

    const hasEnoughPoints =
      formState.manual_mode === "endpoints" ? manualWaypoints.length === 2 : manualWaypoints.length >= 2;

    if (!hasEnoughPoints) {
      setManualPreview(null);
      setManualPreviewError("");
      setIsLoadingManualPreview(false);
      return;
    }

    let isActive = true;
    setManualPreviewError("");
    setIsLoadingManualPreview(true);

    const timeoutId = window.setTimeout(async () => {
      try {
        const preview = await previewManualRoute({
          mode: formState.manual_mode,
          waypoints: manualWaypoints,
        });
        if (!isActive) {
          return;
        }
        setManualPreview(preview);
      } catch (previewError) {
        if (!isActive) {
          return;
        }
        setManualPreview(null);
        setManualPreviewError(
          previewError.response?.data?.detail || "Could not preview the manual walking route.",
        );
      } finally {
        if (isActive) {
          setIsLoadingManualPreview(false);
        }
      }
    }, 350);

    return () => {
      isActive = false;
      window.clearTimeout(timeoutId);
    };
  }, [formState.gpx_source, formState.manual_mode, manualWaypoints]);

  async function handleSubmit(event) {
    event.preventDefault();
    if (formState.gpx_source === "upload" && !formState.gpx_file) {
      setError("Please choose a GPX file.");
      return;
    }

    if (formState.gpx_source === "saved" && !formState.saved_gpx_file_id) {
      setError("Please choose one of your saved GPX files.");
      return;
    }

    if (formState.gpx_source === "manual") {
      const hasEnoughPoints =
        formState.manual_mode === "endpoints" ? manualWaypoints.length === 2 : manualWaypoints.length >= 2;
      if (!hasEnoughPoints) {
        setError(
          formState.manual_mode === "endpoints"
            ? "Please choose a start and finish point on the map."
            : "Please choose at least two route points on the map.",
        );
        return;
      }
    }

    setError("");
    setIsSubmitting(true);

    try {
      const basePayload = {
        ...formState,
        start_time: toOffsetIsoString(formState.start_time),
        target_distance_per_day_km: formState.target_distance_per_day_km
          ? Number(formState.target_distance_per_day_km)
          : undefined,
      };
      const route = formState.gpx_source === "manual"
        ? await createManualRoute({
          ...basePayload,
          mode: formState.manual_mode,
          waypoints: manualWaypoints,
        })
        : await uploadRoute({
          ...basePayload,
          saved_gpx_file_id:
            formState.gpx_source === "saved" && formState.saved_gpx_file_id
              ? Number(formState.saved_gpx_file_id)
              : undefined,
          gpx_file: formState.gpx_source === "upload" ? formState.gpx_file : undefined,
        });
      navigate(`/routes/${route.id}`);
    } catch (submitError) {
      setError(submitError.response?.data?.detail || "Could not build the route.");
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleAddManualWaypoint(point) {
    setManualWaypoints((current) => {
      if (formState.manual_mode === "endpoints") {
        if (current.length === 0) {
          return [point];
        }
        if (current.length === 1) {
          return [current[0], point];
        }
        return [current[0], point];
      }
      return [...current, point];
    });
  }

  function handleRemoveLastWaypoint() {
    setManualWaypoints((current) => current.slice(0, -1));
  }

  function handleClearWaypoints() {
    setManualWaypoints([]);
    setManualPreview(null);
    setManualPreviewError("");
  }

  return (
    <section className="panel form-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Upload and process</p>
          <h1>Build a route forecast</h1>
        </div>
      </div>

      <form className="form-grid" onSubmit={handleSubmit}>
        <label className="field">
          <span>Route name</span>
          <input
            onChange={(event) => setFormState((current) => ({ ...current, name: event.target.value }))}
            placeholder="Weekend ridge walk"
            required
            type="text"
            value={formState.name}
          />
        </label>

        <label className="field">
          <span>Planned start date and time</span>
          <input
            onChange={(event) => setFormState((current) => ({ ...current, start_time: event.target.value }))}
            required
            type="datetime-local"
            value={formState.start_time}
          />
        </label>

        <label className="field">
          <span>Average speed (km/h)</span>
          <input
            min="1"
            onChange={(event) =>
              setFormState((current) => ({ ...current, speed_kmh: Number(event.target.value) }))
            }
            required
            step="0.1"
            type="number"
            value={formState.speed_kmh}
          />
        </label>

        <label className="field">
          <span>Sampling interval (minutes)</span>
          <select
            onChange={(event) =>
              setFormState((current) => ({
                ...current,
                sample_interval_minutes: Number(event.target.value),
              }))
            }
            value={formState.sample_interval_minutes}
          >
            <option value="15">15 minutes</option>
            <option value="30">30 minutes</option>
            <option value="60">60 minutes</option>
          </select>
        </label>

        <div className="field field-full">
          <span>Route source</span>
          <div className="choice-grid">
            <label className="toggle-field">
              <input
                checked={formState.gpx_source === "upload"}
                onChange={() =>
                  setFormState((current) => ({
                    ...current,
                    gpx_source: "upload",
                    saved_gpx_file_id: "",
                  }))
                }
                name="gpx_source"
                type="radio"
              />
              <div>
                <strong>Upload a new GPX</strong>
                <p>Use a GPX file from this device just for this route build.</p>
              </div>
            </label>

            <label className="toggle-field">
              <input
                checked={formState.gpx_source === "saved"}
                disabled={!savedGpxFiles.length}
                onChange={() =>
                  setFormState((current) => ({
                    ...current,
                    gpx_source: "saved",
                    saved_gpx_file_id: current.saved_gpx_file_id || String(savedGpxFiles[0]?.id || ""),
                    gpx_file: null,
                  }))
                }
                name="gpx_source"
                type="radio"
              />
              <div>
                <strong>Use a saved GPX</strong>
                <p>Pick one from your account library and build another route from it.</p>
              </div>
            </label>

            <label className="toggle-field">
              <input
                checked={formState.gpx_source === "manual"}
                onChange={() =>
                  setFormState((current) => ({
                    ...current,
                    gpx_source: "manual",
                    gpx_file: null,
                    saved_gpx_file_id: "",
                  }))
                }
                name="gpx_source"
                type="radio"
              />
              <div>
                <strong>Plot on the map</strong>
                <p>Create a walking route from two end points or build it point by point on the map.</p>
              </div>
            </label>
          </div>
        </div>

        {formState.gpx_source === "upload" ? (
          <label className="field field-full">
            <span>GPX file</span>
            <input
              accept=".gpx"
              onChange={(event) =>
                setFormState((current) => ({ ...current, gpx_file: event.target.files?.[0] || null }))
              }
              required
              type="file"
            />
          </label>
        ) : formState.gpx_source === "saved" ? (
          <label className="field field-full">
            <span>Saved GPX file</span>
            <select
              disabled={isLoadingSavedGpx || !savedGpxFiles.length}
              onChange={(event) =>
                setFormState((current) => ({ ...current, saved_gpx_file_id: event.target.value }))
              }
              required
              value={formState.saved_gpx_file_id}
            >
              <option value="">
                {isLoadingSavedGpx ? "Loading saved GPX files..." : "Choose a saved GPX"}
              </option>
              {savedGpxFiles.map((file) => (
                <option key={file.id} value={file.id}>
                  {file.name} ({file.point_count} points)
                </option>
              ))}
            </select>
            {selectedSavedGpx ? (
              <p className="helper-text">
                Using {selectedSavedGpx.original_filename} with {selectedSavedGpx.point_count} points.
              </p>
            ) : !isLoadingSavedGpx ? (
              <p className="helper-text">
                Save GPX files from your dashboard first if you want to reuse them here.
              </p>
            ) : null}
          </label>
        ) : formState.gpx_source === "manual" ? (
          <div className="field field-full stack">
            <label className="field">
              <span>Map plotting mode</span>
              <select
                onChange={(event) => {
                  const nextMode = event.target.value;
                  setFormState((current) => ({ ...current, manual_mode: nextMode }));
                  setManualWaypoints((current) => (nextMode === "endpoints" ? current.slice(0, 2) : current));
                  setManualPreview(null);
                  setManualPreviewError("");
                }}
                value={formState.manual_mode}
              >
                <option value="endpoints">Fastest walking route between start and finish</option>
                <option value="waypoints">Build route by placing points along the way</option>
              </select>
            </label>

            <div className="builder-instructions">
              <p className="helper-text">
                {formState.manual_mode === "endpoints"
                  ? "Click once for the start point and once for the finish point. Clicking again updates the finish."
                  : "Click points along the route in order. The route will follow walking paths between them."}
              </p>
              <div className="card-actions">
                <button className="secondary-button" onClick={handleRemoveLastWaypoint} type="button">
                  Undo last point
                </button>
                <button className="ghost-button" onClick={handleClearWaypoints} type="button">
                  Clear route
                </button>
              </div>
            </div>

            <RouteBuilderMap
              mode={formState.manual_mode}
              onAddWaypoint={handleAddManualWaypoint}
              previewGeojson={manualPreview?.route_geojson}
              waypoints={manualWaypoints}
            />

            <div className="builder-summary-grid">
              <article className="detail-card">
                <span className="detail-label">Selected points</span>
                <strong>{manualWaypoints.length}</strong>
              </article>
              <article className="detail-card">
                <span className="detail-label">Preview status</span>
                <strong>
                  {isLoadingManualPreview
                    ? "Calculating..."
                    : manualPreview
                      ? `${manualPreview.total_distance_km} km route`
                      : "Add points to preview"}
                </strong>
              </article>
            </div>

            {manualPreview ? (
              <p className="helper-text">
                Preview route distance: {manualPreview.total_distance_km} km across {manualPreview.point_count} route points.
              </p>
            ) : null}
            {manualPreviewError ? <p className="form-error">{manualPreviewError}</p> : null}
          </div>
        ) : null}

        <label className="toggle-field field-full">
          <input
            checked={formState.overnight_camps_enabled}
            onChange={(event) =>
              setFormState((current) => ({
                ...current,
                overnight_camps_enabled: event.target.checked,
              }))
            }
            type="checkbox"
          />
          <div>
            <strong>Plan overnight camps</strong>
            <p>Add daily camp planning targets, sunset limits, and overnight stop forecasts.</p>
          </div>
        </label>

        {formState.overnight_camps_enabled ? (
          <>
            <label className="field">
              <span>Target distance each day (km)</span>
              <input
                min="1"
                onChange={(event) =>
                  setFormState((current) => ({
                    ...current,
                    target_distance_per_day_km: event.target.value,
                  }))
                }
                required
                step="0.1"
                type="number"
                value={formState.target_distance_per_day_km}
              />
            </label>

            <label className="field">
              <span>Target time to camp</span>
              <input
                onChange={(event) =>
                  setFormState((current) => ({
                    ...current,
                    target_time_to_camp: event.target.value,
                  }))
                }
                required
                type="time"
                value={formState.target_time_to_camp}
              />
            </label>

            <label className="field">
              <span>Target time to destination</span>
              <input
                onChange={(event) =>
                  setFormState((current) => ({
                    ...current,
                    target_time_to_destination: event.target.value,
                  }))
                }
                required
                type="time"
                value={formState.target_time_to_destination}
              />
            </label>

            <label className="toggle-field">
              <input
                checked={formState.avoid_camp_after_sunset}
                onChange={(event) =>
                  setFormState((current) => ({
                    ...current,
                    avoid_camp_after_sunset: event.target.checked,
                  }))
                }
                type="checkbox"
              />
              <div>
                <strong>Do not camp later than sunset</strong>
                <p>Camp legs shorten automatically when the current day's sunset arrives earlier.</p>
              </div>
            </label>
          </>
        ) : null}

        <label className="toggle-field field-full">
          <input
            checked={formState.plan_lunch_stops}
            onChange={(event) =>
              setFormState((current) => ({
                ...current,
                plan_lunch_stops: event.target.checked,
              }))
            }
            type="checkbox"
          />
          <div>
            <strong>Plan lunch stops</strong>
            <p>Add one lunch stop per day and forecast that stop for the next 24 hours.</p>
          </div>
        </label>

        {formState.plan_lunch_stops ? (
          <label className="field">
            <span>Lunch rest duration (minutes)</span>
            <input
              min="5"
              onChange={(event) =>
                setFormState((current) => ({
                  ...current,
                  lunch_rest_minutes: Number(event.target.value),
                }))
              }
              required
              step="5"
              type="number"
              value={formState.lunch_rest_minutes}
            />
          </label>
        ) : null}

        {error ? <p className="form-error field-full">{error}</p> : null}

        <div className="field-full button-row">
          <button className="primary-button" disabled={isSubmitting} type="submit">
            {isSubmitting ? "Processing route..." : "Generate route forecast"}
          </button>
        </div>
      </form>
    </section>
  );
}

export default UploadRoutePage;
