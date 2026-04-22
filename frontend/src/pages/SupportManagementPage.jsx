import { useEffect, useState } from "react";
import { useAuth } from "../hooks/useAuth";

function formatDateTime(value) {
  return value ? new Date(value).toLocaleString() : "Not recorded";
}

function EmptyState({ children }) {
  return <p>{children}</p>;
}

function SupportManagementPage() {
  const {
    loadSupportInactiveAccounts,
    loadSupportFlaggedUsers,
    requestSupportPasswordReset,
    reactivateAccountBySupport,
    searchAccountsBySupport,
    changeAccountEmailBySupport,
    loadSupportAuditLogs,
    adminDeactivateAccount,
    adminDeleteAccount,
    isSeniorSupportOrHigher,
    isAdministrationOrHigher,
  } = useAuth();

  const [inactiveAccounts, setInactiveAccounts] = useState([]);
  const [flaggedUsers, setFlaggedUsers] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [searchResults, setSearchResults] = useState([]);
  const [supportResetForm, setSupportResetForm] = useState({ email: "", first_name: "", last_name: "" });
  const [reactivateForm, setReactivateForm] = useState({ email: "", confirm_email: "", reason: "" });
  const [searchForm, setSearchForm] = useState({ first_name: "", last_name: "", phone_number: "" });
  const [adminDeactivateForm, setAdminDeactivateForm] = useState({ email: "", confirm_email: "", reason: "" });
  const [adminDeleteForm, setAdminDeleteForm] = useState({ email: "", confirm_email: "", admin_password: "" });
  const [emailChangeState, setEmailChangeState] = useState({});
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [activeAction, setActiveAction] = useState("");

  async function loadSupportData() {
    const [loadedInactiveAccounts, loadedFlaggedUsers] = await Promise.all([
      loadSupportInactiveAccounts(),
      loadSupportFlaggedUsers(),
    ]);
    setInactiveAccounts(loadedInactiveAccounts);
    setFlaggedUsers(loadedFlaggedUsers);

    if (isSeniorSupportOrHigher) {
      const loadedAuditLogs = await loadSupportAuditLogs();
      setAuditLogs(loadedAuditLogs);
    }
  }

  useEffect(() => {
    async function hydrate() {
      try {
        await loadSupportData();
      } catch (loadError) {
        setError(loadError.response?.data?.detail || "Could not load support tools.");
      } finally {
        setIsLoading(false);
      }
    }

    hydrate();
  }, [isSeniorSupportOrHigher]);

  async function refreshSupportData(successMessage = "") {
    try {
      await loadSupportData();
      if (successMessage) {
        setMessage(successMessage);
      }
    } catch (loadError) {
      setError(loadError.response?.data?.detail || "Could not refresh support tools.");
    }
  }

  async function handleSupportPasswordReset(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    setActiveAction("support-reset");
    try {
      const response = await requestSupportPasswordReset(supportResetForm);
      setSupportResetForm({ email: "", first_name: "", last_name: "" });
      await refreshSupportData(response.message);
    } catch (submitError) {
      setError(submitError.response?.data?.detail || "Could not queue the password reset.");
    } finally {
      setActiveAction("");
    }
  }

  async function handleReactivateAccount(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    setActiveAction("reactivate");
    try {
      const response = await reactivateAccountBySupport(reactivateForm);
      setReactivateForm({ email: "", confirm_email: "", reason: "" });
      await refreshSupportData(response.message);
    } catch (submitError) {
      setError(submitError.response?.data?.detail || "Could not reactivate that account.");
    } finally {
      setActiveAction("");
    }
  }

  async function handleSearchAccounts(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    setActiveAction("search");
    try {
      const matches = await searchAccountsBySupport(searchForm);
      setSearchResults(matches);
      if (!matches.length) {
        setMessage("No matching accounts were found.");
      } else {
        setMessage(`Found ${matches.length} matching account${matches.length === 1 ? "" : "s"}.`);
      }
      await refreshSupportData();
    } catch (submitError) {
      setError(submitError.response?.data?.detail || "Could not search for matching accounts.");
    } finally {
      setActiveAction("");
    }
  }

  async function handleEmailChange(userId) {
    const newEmail = emailChangeState[userId] || "";
    if (!newEmail.trim()) {
      setError("Enter a new email address before sending the recovery reset.");
      return;
    }

    setError("");
    setMessage("");
    setActiveAction(`email-change-${userId}`);
    try {
      const response = await changeAccountEmailBySupport({ user_id: userId, new_email: newEmail });
      setEmailChangeState((current) => ({ ...current, [userId]: "" }));
      await refreshSupportData(response.message);
    } catch (submitError) {
      setError(submitError.response?.data?.detail || "Could not change that account email.");
    } finally {
      setActiveAction("");
    }
  }

  async function handleAdminDeactivate(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    setActiveAction("admin-deactivate");
    try {
      const response = await adminDeactivateAccount(adminDeactivateForm);
      setAdminDeactivateForm({ email: "", confirm_email: "", reason: "" });
      await refreshSupportData(response.message);
    } catch (submitError) {
      setError(submitError.response?.data?.detail || "Could not admin-deactivate that account.");
    } finally {
      setActiveAction("");
    }
  }

  async function handleAdminDelete(event) {
    event.preventDefault();
    const confirmed = window.confirm(
      "Permanently delete this account now? This removes the user, saved routes, saved GPX files, and related account activity.",
    );
    if (!confirmed) {
      return;
    }

    setError("");
    setMessage("");
    setActiveAction("admin-delete");
    try {
      const response = await adminDeleteAccount(adminDeleteForm);
      setAdminDeleteForm({ email: "", confirm_email: "", admin_password: "" });
      await refreshSupportData(response.message);
    } catch (submitError) {
      setError(submitError.response?.data?.detail || "Could not permanently delete that account.");
    } finally {
      setActiveAction("");
    }
  }

  return (
    <section className="stack">
      <div className="panel hero-panel">
        <div>
          <p className="eyebrow">Support tools</p>
          <h1>Support Management</h1>
          <p>
            Handle support-assisted password recovery, review inactive or suspicious accounts, and
            escalate recovery or enforcement actions based on your support role.
          </p>
        </div>
      </div>

      {error ? <p className="form-error">{error}</p> : null}
      {message ? <p className="helper-text">{message}</p> : null}

      <div className="settings-grid">
        <form className="panel" onSubmit={handleSupportPasswordReset}>
          <div className="panel-header">
            <div>
              <p className="eyebrow">Support recovery</p>
              <h2>Support password reset</h2>
            </div>
          </div>

          <div className="form-grid">
            <label className="field field-full">
              <span>User email</span>
              <input
                autoComplete="email"
                onChange={(event) => setSupportResetForm((current) => ({ ...current, email: event.target.value }))}
                required
                type="email"
                value={supportResetForm.email}
              />
            </label>

            <label className="field">
              <span>First name</span>
              <input
                onChange={(event) => setSupportResetForm((current) => ({ ...current, first_name: event.target.value }))}
                required
                type="text"
                value={supportResetForm.first_name}
              />
            </label>

            <label className="field">
              <span>Last name</span>
              <input
                onChange={(event) => setSupportResetForm((current) => ({ ...current, last_name: event.target.value }))}
                required
                type="text"
                value={supportResetForm.last_name}
              />
            </label>
          </div>

          <p className="helper-text">
            This queues a password reset link only when the email, first name, and last name match the
            stored account details.
          </p>

          <div className="button-row">
            <button className="primary-button" disabled={activeAction === "support-reset"} type="submit">
              {activeAction === "support-reset" ? "Queuing reset..." : "Queue password reset"}
            </button>
          </div>
        </form>

        <form className="panel" onSubmit={handleReactivateAccount}>
          <div className="panel-header">
            <div>
              <p className="eyebrow">Reactivation</p>
              <h2>Reactivate an account</h2>
            </div>
          </div>

          <div className="form-grid">
            <label className="field">
              <span>User email</span>
              <input
                autoComplete="email"
                onChange={(event) => setReactivateForm((current) => ({ ...current, email: event.target.value }))}
                required
                type="email"
                value={reactivateForm.email}
              />
            </label>

            <label className="field">
              <span>Confirm user email</span>
              <input
                onChange={(event) => setReactivateForm((current) => ({ ...current, confirm_email: event.target.value }))}
                required
                type="email"
                value={reactivateForm.confirm_email}
              />
            </label>

            <label className="field field-full">
              <span>Reason</span>
              <input
                onChange={(event) => setReactivateForm((current) => ({ ...current, reason: event.target.value }))}
                placeholder="Optional support note"
                type="text"
                value={reactivateForm.reason}
              />
            </label>
          </div>

          <div className="button-row">
            <button className="secondary-button" disabled={activeAction === "reactivate"} type="submit">
              {activeAction === "reactivate" ? "Reactivating..." : "Reactivate account"}
            </button>
          </div>
        </form>
      </div>

      <div className="settings-grid">
        <section className="panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Lifecycle</p>
              <h2>Inactive accounts</h2>
            </div>
          </div>

          {isLoading ? (
            <p>Loading inactive account information...</p>
          ) : !inactiveAccounts.length ? (
            <EmptyState>No accounts currently need lifecycle attention.</EmptyState>
          ) : (
            <div className="resource-list">
              {inactiveAccounts.map((account) => (
                <article className="resource-card" key={`${account.email}-${account.account_status}-${account.deleted_at || account.scheduled_deletion_at || account.created_at}`}>
                  <div className="keypoint-heading">
                    <div>
                      <h3>{account.email}</h3>
                      <p>Created {formatDateTime(account.created_at)}</p>
                    </div>
                    <div className="badge-stack">
                      <span className="metric-badge">{account.status_label}</span>
                      {account.deletion_phase ? (
                        <span className="metric-badge metric-badge-soft">{account.deletion_phase}</span>
                      ) : null}
                    </div>
                  </div>

                  <div className="details-inline">
                    <span>Last login {formatDateTime(account.last_login_at)}</span>
                    <span>Last active {formatDateTime(account.last_active_at)}</span>
                    {account.deactivated_at ? <span>Deactivated {formatDateTime(account.deactivated_at)}</span> : null}
                    {account.scheduled_deletion_at ? (
                      <span>Deletion due {formatDateTime(account.scheduled_deletion_at)}</span>
                    ) : null}
                    {account.deleted_at ? <span>Deleted {formatDateTime(account.deleted_at)}</span> : null}
                  </div>

                  {account.deletion_reason ? <p className="helper-text">{account.deletion_reason}</p> : null}
                </article>
              ))}
            </div>
          )}
        </section>

        <section className="panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Abuse review</p>
              <h2>Flagged users</h2>
            </div>
          </div>

          {isLoading ? (
            <p>Loading flagged users...</p>
          ) : !flaggedUsers.length ? (
            <EmptyState>No suspicious user patterns detected right now.</EmptyState>
          ) : (
            <div className="resource-list">
              {flaggedUsers.map((user) => (
                <article className="resource-card" key={user.email}>
                  <div className="keypoint-heading">
                    <div>
                      <h3>{user.email}</h3>
                      <p>Created {formatDateTime(user.created_at)}</p>
                    </div>
                    <span className="metric-badge">{user.routes_created_total} routes total</span>
                  </div>

                  <div className="details-inline">
                    <span>Last active {formatDateTime(user.last_active_at)}</span>
                    <span>Last login {formatDateTime(user.last_login_at)}</span>
                    <span>{user.routes_created_last_hour} routes in the last hour</span>
                    <span>{user.visit_count_last_10_minutes} visits in 10 minutes</span>
                    <span>{user.distinct_paths_last_10_minutes} distinct paths in 10 minutes</span>
                  </div>

                  {user.flag_reasons.map((reason) => (
                    <p className="helper-text" key={reason}>{reason}</p>
                  ))}
                </article>
              ))}
            </div>
          )}
        </section>
      </div>

      {isSeniorSupportOrHigher ? (
        <div className="settings-grid">
          <form className="panel" onSubmit={handleSearchAccounts}>
            <div className="panel-header">
              <div>
                <p className="eyebrow">Senior support recovery</p>
                <h2>Search by support identity</h2>
              </div>
            </div>

            <div className="form-grid">
              <label className="field">
                <span>First name</span>
                <input
                  onChange={(event) => setSearchForm((current) => ({ ...current, first_name: event.target.value }))}
                  required
                  type="text"
                  value={searchForm.first_name}
                />
              </label>

              <label className="field">
                <span>Last name</span>
                <input
                  onChange={(event) => setSearchForm((current) => ({ ...current, last_name: event.target.value }))}
                  required
                  type="text"
                  value={searchForm.last_name}
                />
              </label>

              <label className="field field-full">
                <span>Phone number</span>
                <input
                  onChange={(event) => setSearchForm((current) => ({ ...current, phone_number: event.target.value }))}
                  required
                  type="tel"
                  value={searchForm.phone_number}
                />
              </label>
            </div>

            <div className="button-row">
              <button className="primary-button" disabled={activeAction === "search"} type="submit">
                {activeAction === "search" ? "Searching..." : "Search accounts"}
              </button>
            </div>
          </form>

          <section className="panel">
            <div className="panel-header">
              <div>
                <p className="eyebrow">Matching accounts</p>
                <h2>Recovery results</h2>
              </div>
            </div>

            {!searchResults.length ? (
              <EmptyState>Search results will appear here once a matching account is found.</EmptyState>
            ) : (
              <div className="resource-list">
                {searchResults.map((account) => (
                  <article className="resource-card" key={account.user_id}>
                    <div className="keypoint-heading">
                      <div>
                        <h3>{account.email}</h3>
                        <p>{account.first_name} {account.last_name} | {account.role_label}</p>
                      </div>
                      <span className="metric-badge">{account.paid_member_status}</span>
                    </div>

                    <div className="details-inline">
                      <span>Created {formatDateTime(account.created_at)}</span>
                      <span>Last active {formatDateTime(account.last_active_at)}</span>
                    </div>

                    <label className="field">
                      <span>New email for recovery</span>
                      <input
                        onChange={(event) => setEmailChangeState((current) => ({ ...current, [account.user_id]: event.target.value }))}
                        placeholder="new-address@example.com"
                        type="email"
                        value={emailChangeState[account.user_id] || ""}
                      />
                    </label>

                    <div className="button-row">
                      <button
                        className="secondary-button"
                        disabled={activeAction === `email-change-${account.user_id}`}
                        onClick={() => handleEmailChange(account.user_id)}
                        type="button"
                      >
                        {activeAction === `email-change-${account.user_id}` ? "Updating..." : "Change email and queue reset"}
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>
        </div>
      ) : null}

      {isAdministrationOrHigher ? (
        <div className="settings-grid">
          <form className="panel" onSubmit={handleAdminDeactivate}>
            <div className="panel-header">
              <div>
                <p className="eyebrow">Administration actions</p>
                <h2>Admin deactivate a user</h2>
              </div>
            </div>

            <div className="form-grid">
              <label className="field">
                <span>User email</span>
                <input
                  onChange={(event) => setAdminDeactivateForm((current) => ({ ...current, email: event.target.value }))}
                  required
                  type="email"
                  value={adminDeactivateForm.email}
                />
              </label>

              <label className="field">
                <span>Confirm user email</span>
                <input
                  onChange={(event) => setAdminDeactivateForm((current) => ({ ...current, confirm_email: event.target.value }))}
                  required
                  type="email"
                  value={adminDeactivateForm.confirm_email}
                />
              </label>

              <label className="field field-full">
                <span>Reason shown on the blocked account page</span>
                <textarea
                  onChange={(event) => setAdminDeactivateForm((current) => ({ ...current, reason: event.target.value }))}
                  value={adminDeactivateForm.reason}
                />
              </label>
            </div>

            <div className="button-row">
              <button className="primary-button" disabled={activeAction === "admin-deactivate"} type="submit">
                {activeAction === "admin-deactivate" ? "Deactivating..." : "Admin deactivate account"}
              </button>
            </div>
          </form>

          <form className="panel" onSubmit={handleAdminDelete}>
            <div className="panel-header">
              <div>
                <p className="eyebrow">Permanent removal</p>
                <h2>Delete an account now</h2>
              </div>
            </div>

            <div className="form-grid">
              <label className="field">
                <span>User email</span>
                <input
                  onChange={(event) => setAdminDeleteForm((current) => ({ ...current, email: event.target.value }))}
                  required
                  type="email"
                  value={adminDeleteForm.email}
                />
              </label>

              <label className="field">
                <span>Confirm user email</span>
                <input
                  onChange={(event) => setAdminDeleteForm((current) => ({ ...current, confirm_email: event.target.value }))}
                  required
                  type="email"
                  value={adminDeleteForm.confirm_email}
                />
              </label>

              <label className="field field-full">
                <span>Your administration password</span>
                <input
                  autoComplete="current-password"
                  minLength={8}
                  onChange={(event) => setAdminDeleteForm((current) => ({ ...current, admin_password: event.target.value }))}
                  required
                  type="password"
                  value={adminDeleteForm.admin_password}
                />
              </label>
            </div>

            <div className="button-row">
              <button className="ghost-button" disabled={activeAction === "admin-delete"} type="submit">
                {activeAction === "admin-delete" ? "Deleting..." : "Permanently delete account"}
              </button>
            </div>
          </form>
        </div>
      ) : null}

      {isSeniorSupportOrHigher ? (
        <section className="panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Support audit trail</p>
              <h2>Recent support actions</h2>
            </div>
          </div>

          {isLoading ? (
            <p>Loading support audit logs...</p>
          ) : !auditLogs.length ? (
            <EmptyState>No support actions logged yet.</EmptyState>
          ) : (
            <div className="resource-list">
              {auditLogs.map((log) => (
                <article className="resource-card" key={log.id}>
                  <div className="keypoint-heading">
                    <div>
                      <h3>{log.action}</h3>
                      <p>{formatDateTime(log.created_at)}</p>
                    </div>
                    <span className="metric-badge">{log.actor_role_label}</span>
                  </div>

                  <div className="details-inline">
                    <span>Actor {log.actor_email}</span>
                    <span>Target {log.target_email || "n/a"}</span>
                  </div>

                  {Object.keys(log.details || {}).length ? (
                    <pre className="audit-log-pre">{JSON.stringify(log.details, null, 2)}</pre>
                  ) : null}
                </article>
              ))}
            </div>
          )}
        </section>
      ) : null}
    </section>
  );
}

export default SupportManagementPage;
