import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useState } from "react";
import { useAuth } from "../hooks/useAuth";

function ResetPasswordPage() {
  const { submitPasswordReset } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [formState, setFormState] = useState({ new_password: "", confirm_password: "" });
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const token = searchParams.get("token") || "";

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setMessage("");

    if (!token) {
      setError("This reset link is missing its token.");
      return;
    }
    if (formState.new_password !== formState.confirm_password) {
      setError("New password and confirmation do not match.");
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await submitPasswordReset({ token, new_password: formState.new_password });
      setMessage(response.message);
      setTimeout(() => navigate("/login", { replace: true }), 1200);
    } catch (submitError) {
      setError(submitError.response?.data?.detail || "Could not reset your password.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <section className="auth-card auth-card-accent">
        <p className="eyebrow">Password reset</p>
        <h1>Set a new password</h1>
        <p>
          Use the reset link you received to choose a new password. If this link has expired, request
          a new one or contact support.
        </p>
      </section>

      <form className="auth-card" onSubmit={handleSubmit}>
        <div className="panel-header">
          <div>
            <p className="eyebrow">Reset password</p>
            <h2>Choose a new password</h2>
          </div>
        </div>

        <label className="field">
          <span>New password</span>
          <input
            autoComplete="new-password"
            minLength={8}
            onChange={(event) => setFormState((current) => ({ ...current, new_password: event.target.value }))}
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
            onChange={(event) => setFormState((current) => ({ ...current, confirm_password: event.target.value }))}
            required
            type="password"
            value={formState.confirm_password}
          />
        </label>

        {error ? <p className="form-error">{error}</p> : null}
        {message ? <p className="helper-text">{message}</p> : null}

        <button className="primary-button" disabled={isSubmitting} type="submit">
          {isSubmitting ? "Resetting..." : "Reset password"}
        </button>

        <p className="helper-text">
          Back to <Link to="/login">sign in</Link>
        </p>
      </form>
    </div>
  );
}

export default ResetPasswordPage;
