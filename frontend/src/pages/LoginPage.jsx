import { Link, useLocation, useNavigate } from "react-router-dom";
import { useState } from "react";
import { useAuth } from "../hooks/useAuth";

function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [formState, setFormState] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      const user = await login(formState);
      const destination = user.account_status === "admin_deactivated"
        ? "/account-status"
        : user.must_change_password
          ? "/force-password-change"
          : location.state?.from?.pathname || "/";
      navigate(destination, { replace: true });
    } catch (submitError) {
      setError(submitError.response?.data?.detail || "Unable to sign in.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <section className="auth-card auth-card-accent">
        <p className="eyebrow">Forecast your route before you leave</p>
        <h1>Weather-aware route planning for GPX tracks</h1>
        <p>
          Upload a route, estimate arrival points, and inspect weather conditions along the way on a
          map and timeline.
        </p>
      </section>

      <form className="auth-card" onSubmit={handleSubmit}>
        <div className="panel-header">
          <div>
            <p className="eyebrow">Welcome back</p>
            <h2>Sign in</h2>
          </div>
        </div>

        <label className="field">
          <span>Email</span>
          <input
            autoComplete="email"
            onChange={(event) => setFormState((current) => ({ ...current, email: event.target.value }))}
            required
            type="email"
            value={formState.email}
          />
        </label>

        <label className="field">
          <span>Password</span>
          <input
            autoComplete="current-password"
            minLength={8}
            onChange={(event) => setFormState((current) => ({ ...current, password: event.target.value }))}
            required
            type="password"
            value={formState.password}
          />
        </label>

        {error ? <p className="form-error">{error}</p> : null}

        <button className="primary-button" disabled={isSubmitting} type="submit">
          {isSubmitting ? "Signing in..." : "Sign in"}
        </button>

        <p className="helper-text">
          <Link to="/forgot-password">Forgot password?</Link>
        </p>

        <p className="helper-text">
          Need an account? <Link to="/register">Create one</Link>
        </p>
      </form>
    </div>
  );
}

export default LoginPage;
