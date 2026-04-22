import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  deleteGpxFile,
  downloadGpxFile,
  fetchGpxFiles,
  uploadGpxFile,
} from "../api/routes";
import LoadingState from "../components/LoadingState";
import { usePreferences } from "../hooks/usePreferences";
import { downloadBlob } from "../utils/downloads";
import { formatDateTime, formatDistanceKm } from "../utils/formatters";

function GpxLibraryPage() {
  const navigate = useNavigate();
  const { preferences } = usePreferences();
  const [gpxFiles, setGpxFiles] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [activeDownloadId, setActiveDownloadId] = useState(null);
  const [error, setError] = useState("");
  const [libraryForm, setLibraryForm] = useState({
    name: "",
    gpx_file: null,
  });

  useEffect(() => {
    async function loadGpxFiles() {
      try {
        setGpxFiles(await fetchGpxFiles());
      } catch (loadError) {
        setError(loadError.response?.data?.detail || "Could not load your saved GPX files.");
      } finally {
        setIsLoading(false);
      }
    }

    loadGpxFiles();
  }, []);

  async function handleSaveGpxFile(event) {
    event.preventDefault();
    if (!libraryForm.gpx_file) {
      setError("Choose a GPX file to save into your account library.");
      return;
    }

    setError("");
    setIsUploading(true);
    try {
      const savedFile = await uploadGpxFile(libraryForm);
      setGpxFiles((current) => [savedFile, ...current]);
      setLibraryForm({ name: "", gpx_file: null });
      event.currentTarget.reset();
    } catch (uploadError) {
      setError(uploadError.response?.data?.detail || "Could not save that GPX file.");
    } finally {
      setIsUploading(false);
    }
  }

  async function handleDeleteGpxFile(gpxFileId) {
    const confirmed = window.confirm("Delete this saved GPX file from your account library?");
    if (!confirmed) {
      return;
    }

    setError("");
    try {
      await deleteGpxFile(gpxFileId);
      setGpxFiles((current) => current.filter((file) => file.id !== gpxFileId));
    } catch (deleteError) {
      setError(deleteError.response?.data?.detail || "Could not delete that GPX file.");
    }
  }

  async function handleDownloadGpxFile(gpxFileId) {
    setError("");
    setActiveDownloadId(gpxFileId);
    try {
      const file = await downloadGpxFile(gpxFileId);
      downloadBlob(file.blob, file.filename);
    } catch (downloadError) {
      setError(downloadError.response?.data?.detail || "Could not download that GPX file.");
    } finally {
      setActiveDownloadId(null);
    }
  }

  if (isLoading) {
    return <LoadingState label="Loading your saved GPX files..." />;
  }

  return (
    <section className="stack">
      <div className="panel hero-panel">
        <div>
          <p className="eyebrow">Saved GPX library</p>
          <h1>Your GPX files</h1>
          <p>Store raw GPX files on your account so you can reuse them for future route builds.</p>
        </div>
      </div>

      {error ? <p className="form-error">{error}</p> : null}

      <section className="panel stack">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Add to library</p>
            <h2>Save a GPX file</h2>
          </div>
        </div>

        <form className="form-grid compact-form" onSubmit={handleSaveGpxFile}>
          <label className="field">
            <span>Library name</span>
            <input
              onChange={(event) =>
                setLibraryForm((current) => ({ ...current, name: event.target.value }))
              }
              placeholder="Pennine Way original GPX"
              type="text"
              value={libraryForm.name}
            />
          </label>

          <label className="field">
            <span>GPX file</span>
            <input
              accept=".gpx"
              onChange={(event) =>
                setLibraryForm((current) => ({ ...current, gpx_file: event.target.files?.[0] || null }))
              }
              required
              type="file"
            />
          </label>

          <div className="button-row field-full">
            <button className="primary-button" disabled={isUploading} type="submit">
              {isUploading ? "Saving GPX..." : "Save GPX to account"}
            </button>
          </div>
        </form>
      </section>

      {!gpxFiles.length ? (
        <div className="panel empty-panel">
          <div>
            <h2>No saved GPX files yet</h2>
            <p>Save a reusable GPX here, then use it later without uploading it again.</p>
          </div>
        </div>
      ) : (
        <div className="resource-list">
          {gpxFiles.map((file) => (
            <article className="resource-card" key={file.id}>
              <div>
                <p className="eyebrow">Saved GPX</p>
                <h3>{file.name}</h3>
                <p>{file.original_filename}</p>
              </div>

              <dl className="metric-grid">
                <div>
                  <dt>Distance</dt>
                  <dd>{formatDistanceKm(file.total_distance_km, preferences)}</dd>
                </div>
                <div>
                  <dt>Points</dt>
                  <dd>{file.point_count}</dd>
                </div>
                <div>
                  <dt>Uploaded</dt>
                  <dd>{formatDateTime(file.uploaded_at, preferences)}</dd>
                </div>
              </dl>

              <div className="card-actions">
                <button
                  className="secondary-button"
                  onClick={() => navigate(`/upload?savedGpx=${file.id}`)}
                  type="button"
                >
                  Use for route
                </button>
                <button
                  className="ghost-button"
                  disabled={activeDownloadId === file.id}
                  onClick={() => handleDownloadGpxFile(file.id)}
                  type="button"
                >
                  {activeDownloadId === file.id ? "Downloading..." : "Download GPX"}
                </button>
                <button className="ghost-button" onClick={() => handleDeleteGpxFile(file.id)} type="button">
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

export default GpxLibraryPage;
