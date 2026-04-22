import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { fetchLegalDocument } from "../api/content";
import { useAuth } from "../hooks/useAuth";

function AccountStatusPage() {
  const { logout, user } = useAuth();
  const [contactDocument, setContactDocument] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadContactDocument() {
      try {
        setContactDocument(await fetchLegalDocument("contact"));
      } catch (loadError) {
        setError(loadError.response?.data?.detail || "Could not load contact details.");
      }
    }

    loadContactDocument();
  }, []);

  if (!user) {
    return null;
  }

  if (user.account_status !== "admin_deactivated") {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="auth-page">
      <section className="auth-card auth-card-accent">
        <p className="eyebrow">Account access paused</p>
        <h1>Your account has been deactivated by an administrator</h1>
        <p>
          RouteForcast access is currently disabled for this account. Logging in does not cancel this
          deactivation. If you believe this is a mistake, please use the contact details below to
          appeal before the account reaches its deletion deadline.
        </p>
        {user.deactivation_reason ? <p>{user.deactivation_reason}</p> : null}
        {user.scheduled_deletion_at ? (
          <p>Scheduled deletion: {new Date(user.scheduled_deletion_at).toLocaleString()}</p>
        ) : null}
      </section>

      <section className="auth-card stack">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Appeals and support</p>
            <h2>Contact details</h2>
          </div>
        </div>

        {contactDocument ? (
          <article className="legal-document-content">{contactDocument.body}</article>
        ) : (
          <p>{error || "Loading contact details..."}</p>
        )}

        <div className="card-actions">
          <Link className="secondary-button" to="/contact">
            Open full contact page
          </Link>
          <button className="primary-button" onClick={logout} type="button">
            Sign out
          </button>
        </div>
      </section>
    </div>
  );
}

export default AccountStatusPage;
