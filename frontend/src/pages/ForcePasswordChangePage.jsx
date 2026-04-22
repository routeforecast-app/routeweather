import { Navigate, useNavigate } from "react-router-dom";
import { useState } from "react";
import { useAuth } from "../hooks/useAuth";

const ADMIN_PASSWORD_HINT =
  "Administrator passwords must be at least 8 characters long and include 1 uppercase letter, 1 number, and 1 symbol.";

function ForcePasswordChangePage() {
  const navigate = useNavigate();
  const { changePassword, logout, user } = useAuth();
  const [formState, setFormState] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!user) {
    return null;
  }

  if (!user.must_change_password) {
    return <Navigate to="/" replace />;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setMessage("");

    if (formState.new_password !== formState.confirm_password) {
      setError("New password and confirmation do not match.");
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await changePassword({
        current_password: formState.current_password,
        new_password: formState.new_password,
      });
      setMessage(response.message);
      navigate("/", { replace: true });
    } catch (submitError) {
      setError(submitError.response?.data?.detail || "Could not update your password.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <section className="auth-card auth-card-accent">
        <p className="eyebrow">Administrator security update</p>
        <h1>Password update required</h1>
        <p>
          Your account now has administrator access, so you need to set a stronger password before
          RouteForcast unlocks the rest of the app.
        </p>
        <p>{ADMIN_PASSWORD_HINT}</p>
      </section>

      <form className="auth-card" onSubmit={handleSubmit}>
        <div className="panel-header">
          <div>
            <p className="eyebrow">Security first</p>
            <h2>Change administrator password</h2>
          </div>
        </div>

        <label className="field field-full">
          <span>Current password</span>
          <input
            autoComplete="current-password"
            minLength={8}
            onChange={(event) =>
              setFormState((current) => ({ ...current, current_password: event.target.value }))
            }
            required
            type="password"
            value={formState.current_password}
          />
        </label>

        <label className="field">
          <span>New password</span>
          <input
            autoComplete="new-password"
            minLength={8}
            onChange={(event) =>
              setFormState((current) => ({ ...current, new_password: event.target.value }))
            }
            required
            type="password"
            value={formState.new_password}
          />
        </label>

        <label className="field">
          <span>Confirm new password</span>
          <input
            autoComplete="new-password"
            minLength={8}
            onChange={(event) =>
              setFormState((current) => ({ ...current, confirm_password: event.target.value }))
            }
            required
            type="password"
            value={formState.confirm_password}
          />
        </label>

        <p className="helper-text">{ADMIN_PASSWORD_HINT}</p>
        {error ? <p className="form-error">{error}</p> : null}
        {message ? <p className="helper-text">{message}</p> : null}

        <button className="primary-button" disabled={isSubmitting} type="submit">
          {isSubmitting ? "Updating password..." : "Update password and continue"}
        </button>

        <button className="text-button" onClick={logout} type="button">
          Sign out instead
        </button>
      </form>
    </div>
  );
}

export default ForcePasswordChangePage;
