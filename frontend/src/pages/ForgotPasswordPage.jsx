import { Link } from "react-router-dom";
import { useState } from "react";
import { useAuth } from "../hooks/useAuth";

function ForgotPasswordPage() {
  const { submitForgotPassword } = useAuth();
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    setIsSubmitting(true);

    try {
      const response = await submitForgotPassword({ email });
      setMessage(response.message);
    } catch (submitError) {
      setError(submitError.response?.data?.detail || "Could not submit password reset request.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <section className="auth-card auth-card-accent">
        <p className="eyebrow">Password reset</p>
        <h1>Forgot your password?</h1>
        <p>
          RouteForcast will queue a password reset link if that email exists. Support users can also
          help with verified recovery from the Support Management area.
        </p>
      </section>

      <form className="auth-card" onSubmit={handleSubmit}>
        <div className="panel-header">
          <div>
            <p className="eyebrow">Reset access</p>
            <h2>Request password reset</h2>
          </div>
        </div>

        <label className="field">
          <span>Email</span>
          <input
            autoComplete="email"
            onChange={(event) => setEmail(event.target.value)}
            required
            type="email"
            value={email}
          />
        </label>

        {error ? <p className="form-error">{error}</p> : null}
        {message ? <p className="helper-text">{message}</p> : null}

        <button className="primary-button" disabled={isSubmitting} type="submit">
          {isSubmitting ? "Submitting..." : "Request reset"}
        </button>

        <p className="helper-text">
          Back to <Link to="/login">sign in</Link>
        </p>
      </form>
    </div>
  );
}

export default ForgotPasswordPage;
