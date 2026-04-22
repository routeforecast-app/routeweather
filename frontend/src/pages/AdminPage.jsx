import { useEffect, useState } from "react";
import { fetchAdminLegalDocuments, saveAdminLegalDocument } from "../api/content";
import { useAuth } from "../hooks/useAuth";
import { roleLabel } from "../utils/roles";

function formatLegalDate(date = new Date()) {
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(date);
}

function replaceLegalDateMarkers(text, formattedDate) {
  return text
    .replaceAll("[DATE]", formattedDate)
    .replace(/(Last\s+updated:\s*)(.*)$/im, `$1${formattedDate}`);
}

function formatDateTime(value) {
  return value ? new Date(value).toLocaleString() : "Not recorded";
}

function EmptyState({ children }) {
  return <p>{children}</p>;
}

function AdminPage() {
  const {
    loadAdminStats,
    loadRoleGrants,
    createAccessGrant,
    removeAccessGrant,
    loadVisitAnalytics,
    isSystemManager,
  } = useAuth();

  const [stats, setStats] = useState(null);
  const [roleGrants, setRoleGrants] = useState([]);
  const [visitAnalytics, setVisitAnalytics] = useState(null);
  const [legalDocuments, setLegalDocuments] = useState([]);
  const [selectedLegalType, setSelectedLegalType] = useState("privacy");
  const [legalEditor, setLegalEditor] = useState({ title: "", body: "" });
  const [roleGrantForm, setRoleGrantForm] = useState({ email: "", role: "support_user" });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSavingLegal, setIsSavingLegal] = useState(false);
  const [isSubmittingGrant, setIsSubmittingGrant] = useState(false);
  const [activeRemovalId, setActiveRemovalId] = useState(null);

  async function loadAdminData() {
    const [loadedStats, loadedVisitAnalytics, loadedLegalDocuments, loadedRoleGrants] = await Promise.all([
      loadAdminStats(),
      loadVisitAnalytics(),
      fetchAdminLegalDocuments(),
      loadRoleGrants(),
    ]);
    setStats(loadedStats);
    setVisitAnalytics(loadedVisitAnalytics);
    setLegalDocuments(loadedLegalDocuments);
    setRoleGrants(loadedRoleGrants);

    const initialDocument = loadedLegalDocuments.find((document) => document.document_type === selectedLegalType)
      || loadedLegalDocuments[0];
    if (initialDocument) {
      setSelectedLegalType(initialDocument.document_type);
      setLegalEditor({ title: initialDocument.title, body: initialDocument.body });
    }
  }

  useEffect(() => {
    async function hydrate() {
      try {
        await loadAdminData();
      } catch (loadError) {
        setError(loadError.response?.data?.detail || "Could not load administrator tools.");
      } finally {
        setIsLoading(false);
      }
    }

    hydrate();
  }, []);

  async function refreshAdminData(successMessage = "") {
    try {
      await loadAdminData();
      if (successMessage) {
        setMessage(successMessage);
      }
    } catch (loadError) {
      setError(loadError.response?.data?.detail || "Could not refresh administrator tools.");
    }
  }

  async function handleRoleGrantSubmit(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    setIsSubmittingGrant(true);
    try {
      const roleGrant = await createAccessGrant(roleGrantForm);
      setRoleGrantForm({ email: "", role: "support_user" });
      await refreshAdminData(`${roleGrant.email} now has the ${roleGrant.role_label} access level.`);
    } catch (submitError) {
      setError(submitError.response?.data?.detail || "Could not update that access role.");
    } finally {
      setIsSubmittingGrant(false);
    }
  }

  async function handleRemoveRoleGrant(roleGrant) {
    const confirmed = window.confirm(`Remove privileged access for ${roleGrant.email}?`);
    if (!confirmed) {
      return;
    }

    setError("");
    setMessage("");
    setActiveRemovalId(roleGrant.id);
    try {
      const response = await removeAccessGrant(roleGrant.id);
      await refreshAdminData(response.message);
    } catch (submitError) {
      setError(submitError.response?.data?.detail || "Could not remove that access role.");
    } finally {
      setActiveRemovalId(null);
    }
  }

  function handleSelectLegalDocument(documentType) {
    const selectedDocument = legalDocuments.find((document) => document.document_type === documentType);
    if (!selectedDocument) {
      return;
    }
    setSelectedLegalType(documentType);
    setLegalEditor({
      title: selectedDocument.title,
      body: selectedDocument.body,
    });
  }

  async function handleSaveLegalDocument(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    setIsSavingLegal(true);
    const today = formatLegalDate();
    const preparedDocument = {
      title: replaceLegalDateMarkers(legalEditor.title, today),
      body: replaceLegalDateMarkers(legalEditor.body, today),
    };

    try {
      const savedDocument = await saveAdminLegalDocument(selectedLegalType, preparedDocument);
      const updatedDocuments = legalDocuments.map((document) =>
        document.document_type === savedDocument.document_type ? savedDocument : document,
      );
      setLegalDocuments(updatedDocuments);
      setLegalEditor({ title: savedDocument.title, body: savedDocument.body });
      setMessage(`${savedDocument.title} has been updated.`);
    } catch (submitError) {
      setError(submitError.response?.data?.detail || "Could not save that legal document.");
    } finally {
      setIsSavingLegal(false);
    }
  }

  function handleApplyTodayDate() {
    const today = formatLegalDate();
    setLegalEditor((current) => ({
      title: replaceLegalDateMarkers(current.title, today),
      body: replaceLegalDateMarkers(current.body, today),
    }));
    setMessage(`Updated [DATE] placeholders and any 'Last updated:' line to ${today}.`);
    setError("");
  }

  return (
    <section className="stack">
      <div className="panel hero-panel">
        <div>
          <p className="eyebrow">Administration tools</p>
          <h1>Admin overview</h1>
          <p>
            Review platform usage, manage legal and contact content, and assign elevated access
            roles for support and system staff.
          </p>
        </div>
      </div>

      {error ? <p className="form-error">{error}</p> : null}
      {message ? <p className="helper-text">{message}</p> : null}

      <div className="settings-grid">
        <section className="panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Usage</p>
              <h2>Platform counts</h2>
            </div>
          </div>

          {isLoading || !stats ? (
            <p>Loading administrator stats...</p>
          ) : (
            <div className="stats-grid">
              <article className="detail-card">
                <span className="detail-label">Accounts created</span>
                <strong>{stats.total_users}</strong>
              </article>
              <article className="detail-card">
                <span className="detail-label">Saved routes</span>
                <strong>{stats.total_routes}</strong>
              </article>
              <article className="detail-card">
                <span className="detail-label">Saved GPX files</span>
                <strong>{stats.total_saved_gpx_files}</strong>
              </article>
              <article className="detail-card">
                <span className="detail-label">Administration and above</span>
                <strong>{stats.total_admin_users}</strong>
              </article>
            </div>
          )}
        </section>

        <section className="panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Traffic</p>
              <h2>Visit summary</h2>
            </div>
          </div>

          {isLoading || !visitAnalytics ? (
            <p>Loading visit analytics...</p>
          ) : (
            <div className="stats-grid">
              <article className="detail-card">
                <span className="detail-label">Total visits</span>
                <strong>{visitAnalytics.total_visits}</strong>
              </article>
              <article className="detail-card">
                <span className="detail-label">Unique visitors</span>
                <strong>{visitAnalytics.unique_visitors}</strong>
              </article>
              <article className="detail-card">
                <span className="detail-label">Visits last 7 days</span>
                <strong>{visitAnalytics.visits_last_7_days}</strong>
              </article>
              <article className="detail-card">
                <span className="detail-label">Visits last 30 days</span>
                <strong>{visitAnalytics.visits_last_30_days}</strong>
              </article>
            </div>
          )}
        </section>
      </div>

      {isSystemManager ? (
        <div className="settings-grid">
          <form className="panel" onSubmit={handleRoleGrantSubmit}>
            <div className="panel-header">
              <div>
                <p className="eyebrow">Access control</p>
                <h2>Assign a privileged role</h2>
              </div>
            </div>

            <div className="form-grid">
              <label className="field">
                <span>User email</span>
                <input
                  autoComplete="email"
                  onChange={(event) => setRoleGrantForm((current) => ({ ...current, email: event.target.value }))}
                  placeholder="person@example.com"
                  required
                  type="email"
                  value={roleGrantForm.email}
                />
              </label>

              <label className="field">
                <span>Access role</span>
                <select
                  onChange={(event) => setRoleGrantForm((current) => ({ ...current, role: event.target.value }))}
                  value={roleGrantForm.role}
                >
                  <option value="support_user">Support User</option>
                  <option value="senior_support_user">Senior Support User</option>
                  <option value="administration_user">Administration User</option>
                  <option value="system_manager">System Manager</option>
                </select>
              </label>
            </div>

            <p className="helper-text">
              Use this to assign support, senior support, administration, or system manager access by
              email. Existing accounts will pick up the new role automatically.
            </p>

            <div className="button-row">
              <button className="primary-button" disabled={isSubmittingGrant} type="submit">
                {isSubmittingGrant ? "Saving role..." : "Save access role"}
              </button>
            </div>
          </form>

          <section className="panel">
            <div className="panel-header">
              <div>
                <p className="eyebrow">Privileged access</p>
                <h2>Current access grants</h2>
              </div>
            </div>

            {isLoading ? (
              <p>Loading access grants...</p>
            ) : !roleGrants.length ? (
              <EmptyState>No privileged access grants configured yet.</EmptyState>
            ) : (
              <div className="resource-list">
                {roleGrants.map((roleGrant) => (
                  <article className="resource-card" key={roleGrant.id}>
                    <div className="keypoint-heading">
                      <div>
                        <h3>{roleGrant.email}</h3>
                        <p>{roleGrant.role_label} | Added {formatDateTime(roleGrant.created_at)}</p>
                      </div>
                      {roleGrant.is_seeded ? (
                        <span className="metric-badge">Seeded {roleLabel(roleGrant.role)}</span>
                      ) : (
                        <button
                          className="ghost-button"
                          disabled={activeRemovalId === roleGrant.id}
                          onClick={() => handleRemoveRoleGrant(roleGrant)}
                          type="button"
                        >
                          {activeRemovalId === roleGrant.id ? "Removing..." : "Remove"}
                        </button>
                      )}
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>
        </div>
      ) : null}

      <div className="settings-grid">
        <section className="panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Where in the world</p>
              <h2>Top countries</h2>
            </div>
          </div>

          {isLoading || !visitAnalytics ? (
            <p>Loading country analytics...</p>
          ) : !visitAnalytics.top_countries.length ? (
            <EmptyState>No visit geography data yet.</EmptyState>
          ) : (
            <div className="resource-list">
              {visitAnalytics.top_countries.map((country) => (
                <article className="resource-card" key={country.country_code}>
                  <div className="keypoint-heading">
                    <strong>{country.country_code}</strong>
                    <span className="metric-badge metric-badge-soft">{country.visits} visits</span>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        <section className="panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Popular pages</p>
              <h2>Most visited paths</h2>
            </div>
          </div>

          {isLoading || !visitAnalytics ? (
            <p>Loading path analytics...</p>
          ) : !visitAnalytics.top_paths.length ? (
            <EmptyState>No path analytics yet.</EmptyState>
          ) : (
            <div className="resource-list">
              {visitAnalytics.top_paths.map((path) => (
                <article className="resource-card" key={path.path}>
                  <div className="keypoint-heading">
                    <strong>{path.path}</strong>
                    <span className="metric-badge metric-badge-soft">{path.visits} visits</span>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </div>

      <section className="panel">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Footer content</p>
            <h2>Edit footer legal and contact pages</h2>
          </div>
        </div>

        {isLoading ? (
          <p>Loading legal documents...</p>
        ) : (
          <form className="stack" onSubmit={handleSaveLegalDocument}>
            <div className="choice-grid">
              {legalDocuments.map((document) => (
                <button
                  className={document.document_type === selectedLegalType ? "primary-button" : "secondary-button"}
                  key={document.document_type}
                  onClick={() => handleSelectLegalDocument(document.document_type)}
                  type="button"
                >
                  {document.title}
                </button>
              ))}
            </div>

            <label className="field">
              <span>Title</span>
              <input
                onChange={(event) => setLegalEditor((current) => ({ ...current, title: event.target.value }))}
                required
                type="text"
                value={legalEditor.title}
              />
            </label>

            <label className="field">
              <span>Body</span>
              <textarea
                className="legal-editor"
                onChange={(event) => setLegalEditor((current) => ({ ...current, body: event.target.value }))}
                required
                value={legalEditor.body}
              />
            </label>

            <div className="card-actions">
              <button className="secondary-button" onClick={handleApplyTodayDate} type="button">
                Update the Date
              </button>
              <button className="primary-button" disabled={isSavingLegal} type="submit">
                {isSavingLegal ? "Saving legal page..." : "Save legal page"}
              </button>
            </div>
          </form>
        )}
      </section>
    </section>
  );
}

export default AdminPage;
