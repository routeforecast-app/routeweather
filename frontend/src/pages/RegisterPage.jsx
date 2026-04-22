import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";
import { useAuth } from "../hooks/useAuth";

function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [formState, setFormState] = useState({
    first_name: "",
    last_name: "",
    phone_number: "",
    email: "",
    password: "",
  });
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      const user = await register(formState);
      navigate(user.must_change_password ? "/force-password-change" : "/", { replace: true });
    } catch (submitError) {
      setError(submitError.response?.data?.detail || "Unable to create account.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <section className="auth-card auth-card-accent">
        <p className="eyebrow">Start building saved route forecasts</p>
        <h1>Create your RouteForcast account</h1>
        <p>
          Accounts keep your uploaded GPX routes, sampled weather points, and key forecast snapshots
          available across sessions, and the support details help with safer account recovery later.
        </p>
      </section>

      <form className="auth-card" onSubmit={handleSubmit}>
        <div className="panel-header">
          <div>
            <p className="eyebrow">New account</p>
            <h2>Register</h2>
          </div>
        </div>

        <div className="form-grid">
          <label className="field">
            <span>First name</span>
            <input
              autoComplete="given-name"
              onChange={(event) => setFormState((current) => ({ ...current, first_name: event.target.value }))}
              required
              type="text"
              value={formState.first_name}
            />
          </label>

          <label className="field">
            <span>Last name</span>
            <input
              autoComplete="family-name"
              onChange={(event) => setFormState((current) => ({ ...current, last_name: event.target.value }))}
              required
              type="text"
              value={formState.last_name}
            />
          </label>

          <label className="field field-full">
            <span>Phone number</span>
            <input
              autoComplete="tel"
              onChange={(event) => setFormState((current) => ({ ...current, phone_number: event.target.value }))}
              required
              type="tel"
              value={formState.phone_number}
            />
          </label>

          <label className="field field-full">
            <span>Email</span>
            <input
              autoComplete="email"
              onChange={(event) => setFormState((current) => ({ ...current, email: event.target.value }))}
              required
              type="email"
              value={formState.email}
            />
          </label>

          <label className="field field-full">
            <span>Password</span>
            <input
              autoComplete="new-password"
              minLength={8}
              onChange={(event) => setFormState((current) => ({ ...current, password: event.target.value }))}
              required
              type="password"
              value={formState.password}
            />
          </label>
        </div>

        <p className="helper-text">
          Administration and System Manager accounts require at least 8 characters, 1 uppercase
          letter, 1 number, and 1 symbol.
        </p>

        {error ? <p className="form-error">{error}</p> : null}

        <button className="primary-button" disabled={isSubmitting} type="submit">
          {isSubmitting ? "Creating account..." : "Create account"}
        </button>

        <p className="helper-text">
          Already registered? <Link to="/login">Sign in</Link>
        </p>
      </form>
    </div>
  );
}

export default RegisterPage;
