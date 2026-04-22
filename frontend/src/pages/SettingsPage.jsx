import { useEffect, useState } from "react";
import { useAuth } from "../hooks/useAuth";

const ADMIN_PASSWORD_HINT =
  "Administration and System Manager passwords must be at least 8 characters long and include 1 uppercase letter, 1 number, and 1 symbol.";

function SettingsPage() {
  const { user, savePreferences, saveProfile, changePassword, deactivateAccount, isAdministrationOrHigher } = useAuth();
  const [preferencesState, setPreferencesState] = useState({
    distance_unit: user?.distance_unit || "km",
    temperature_unit: user?.temperature_unit || "c",
    time_format: user?.time_format || "24h",
  });
  const [profileState, setProfileState] = useState({
    first_name: user?.first_name || "",
    last_name: user?.last_name || "",
    phone_number: user?.phone_number || "",
  });
  const [passwordState, setPasswordState] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });
  const [profileMessage, setProfileMessage] = useState("");
  const [preferencesMessage, setPreferencesMessage] = useState("");
  const [passwordMessage, setPasswordMessage] = useState("");
  const [error, setError] = useState("");
  const [isSavingPreferences, setIsSavingPreferences] = useState(false);
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [isDeactivating, setIsDeactivating] = useState(false);

  useEffect(() => {
    setProfileState({
      first_name: user?.first_name || "",
      last_name: user?.last_name || "",
      phone_number: user?.phone_number || "",
    });
  }, [user?.first_name, user?.last_name, user?.phone_number]);

  async function handleProfileSubmit(event) {
    event.preventDefault();
    setError("");
    setProfileMessage("");
    setIsSavingProfile(true);

    try {
      await saveProfile(profileState);
      setProfileMessage("Support details updated.");
    } catch (submitError) {
      setError(submitError.response?.data?.detail || "Could not update support details.");
    } finally {
      setIsSavingProfile(false);
    }
  }

  async function handlePreferencesSubmit(event) {
    event.preventDefault();
    setError("");
    setPreferencesMessage("");
    setIsSavingPreferences(true);

    try {
      await savePreferences(preferencesState);
      setPreferencesMessage("Display settings updated.");
    } catch (submitError) {
      setError(submitError.response?.data?.detail || "Could not update display settings.");
    } finally {
      setIsSavingPreferences(false);
    }
  }

  async function handlePasswordSubmit(event) {
    event.preventDefault();
    setError("");
    setPasswordMessage("");
    if (passwordState.new_password !== passwordState.confirm_password) {
      setError("New password and confirmation do not match.");
      return;
    }

    setIsChangingPassword(true);
    try {
      const response = await changePassword({
        current_password: passwordState.current_password,
        new_password: passwordState.new_password,
      });
      setPasswordMessage(response.message);
      setPasswordState({
        current_password: "",
        new_password: "",
        confirm_password: "",
      });
    } catch (submitError) {
      setError(submitError.response?.data?.detail || "Could not change password.");
    } finally {
      setIsChangingPassword(false);
    }
  }

  async function handleDeactivateAccount() {
    const confirmed = window.confirm(
      "Deactivate your account now? It will be scheduled for deletion in 60 days unless you sign in again before then.",
    );
    if (!confirmed) {
      return;
    }

    setError("");
    setPasswordMessage("");
    setPreferencesMessage("");
    setProfileMessage("");
    setIsDeactivating(true);
    try {
      await deactivateAccount();
    } catch (submitError) {
      setError(submitError.response?.data?.detail || "Could not deactivate your account.");
      setIsDeactivating(false);
    }
  }

  return (
    <section className="stack">
      <div className="panel hero-panel">
        <div>
          <p className="eyebrow">Account settings</p>
          <h1>Profile, display, and security</h1>
          <p>
            Keep your support details up to date, choose your preferred units and time format, then
            manage your password and account lifecycle from one place.
          </p>
        </div>
      </div>

      <section className="panel">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Account</p>
            <h2>Status and activity</h2>
          </div>
        </div>

        <div className="details-inline">
          <span>Role {user?.role_label || "General User"}</span>
          <span>Created {user?.created_at ? new Date(user.created_at).toLocaleString() : "Unknown"}</span>
          <span>Last login {user?.last_login_at ? new Date(user.last_login_at).toLocaleString() : "Not yet recorded"}</span>
          <span>Last active {user?.last_active_at ? new Date(user.last_active_at).toLocaleString() : "Not yet recorded"}</span>
        </div>
      </section>

      {error ? <p className="form-error">{error}</p> : null}

      <div className="settings-grid">
        <form className="panel" onSubmit={handleProfileSubmit}>
          <div className="panel-header">
            <div>
              <p className="eyebrow">Support profile</p>
              <h2>Name and phone number</h2>
            </div>
          </div>

          <div className="form-grid">
            <label className="field">
              <span>First name</span>
              <input
                autoComplete="given-name"
                onChange={(event) => setProfileState((current) => ({ ...current, first_name: event.target.value }))}
                required
                type="text"
                value={profileState.first_name}
              />
            </label>

            <label className="field">
              <span>Last name</span>
              <input
                autoComplete="family-name"
                onChange={(event) => setProfileState((current) => ({ ...current, last_name: event.target.value }))}
                required
                type="text"
                value={profileState.last_name}
              />
            </label>

            <label className="field field-full">
              <span>Phone number</span>
              <input
                autoComplete="tel"
                onChange={(event) => setProfileState((current) => ({ ...current, phone_number: event.target.value }))}
                required
                type="tel"
                value={profileState.phone_number}
              />
            </label>
          </div>

          <p className="helper-text">
            These details are used by support for safer identity checks during account recovery.
          </p>
          {profileMessage ? <p className="helper-text">{profileMessage}</p> : null}

          <div className="button-row">
            <button className="primary-button" disabled={isSavingProfile} type="submit">
              {isSavingProfile ? "Saving..." : "Save support details"}
            </button>
          </div>
        </form>

        <form className="panel" onSubmit={handlePreferencesSubmit}>
          <div className="panel-header">
            <div>
              <p className="eyebrow">Display</p>
              <h2>Formatting preferences</h2>
            </div>
          </div>

          <div className="form-grid">
            <label className="field">
              <span>Distance</span>
              <select
                onChange={(event) =>
                  setPreferencesState((current) => ({ ...current, distance_unit: event.target.value }))
                }
                value={preferencesState.distance_unit}
              >
                <option value="km">Kilometres</option>
                <option value="miles">Miles</option>
              </select>
            </label>

            <label className="field">
              <span>Temperature</span>
              <select
                onChange={(event) =>
                  setPreferencesState((current) => ({ ...current, temperature_unit: event.target.value }))
                }
                value={preferencesState.temperature_unit}
              >
                <option value="c">Celsius</option>
                <option value="f">Fahrenheit</option>
              </select>
            </label>

            <label className="field">
              <span>Time format</span>
              <select
                onChange={(event) =>
                  setPreferencesState((current) => ({ ...current, time_format: event.target.value }))
                }
                value={preferencesState.time_format}
              >
                <option value="24h">24-hour</option>
                <option value="12h">12-hour</option>
              </select>
            </label>
          </div>

          {preferencesMessage ? <p className="helper-text">{preferencesMessage}</p> : null}

          <div className="button-row">
            <button className="primary-button" disabled={isSavingPreferences} type="submit">
              {isSavingPreferences ? "Saving..." : "Save display settings"}
            </button>
          </div>
        </form>
      </div>

      <div className="settings-grid">
        <form className="panel" onSubmit={handlePasswordSubmit}>
          <div className="panel-header">
            <div>
              <p className="eyebrow">Security</p>
              <h2>Change password</h2>
            </div>
          </div>

          <div className="form-grid">
            <label className="field field-full">
              <span>Current password</span>
              <input
                autoComplete="current-password"
                minLength={8}
                onChange={(event) =>
                  setPasswordState((current) => ({ ...current, current_password: event.target.value }))
                }
                required
                type="password"
                value={passwordState.current_password}
              />
            </label>

            <label className="field">
              <span>New password</span>
              <input
                autoComplete="new-password"
                minLength={8}
                onChange={(event) =>
                  setPasswordState((current) => ({ ...current, new_password: event.target.value }))
                }
                required
                type="password"
                value={passwordState.new_password}
              />
            </label>

            <label className="field">
              <span>Confirm new password</span>
              <input
                autoComplete="new-password"
                minLength={8}
                onChange={(event) =>
                  setPasswordState((current) => ({ ...current, confirm_password: event.target.value }))
                }
                required
                type="password"
                value={passwordState.confirm_password}
              />
            </label>
          </div>

          {isAdministrationOrHigher ? <p className="helper-text">{ADMIN_PASSWORD_HINT}</p> : null}
          {passwordMessage ? <p className="helper-text">{passwordMessage}</p> : null}

          <div className="button-row">
            <button className="primary-button" disabled={isChangingPassword} type="submit">
              {isChangingPassword ? "Updating..." : "Change password"}
            </button>
          </div>
        </form>

        <section className="panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Account lifecycle</p>
              <h2>Deactivate account</h2>
            </div>
          </div>

          <p className="helper-text">
            If you deactivate your account, it will be scheduled for permanent deletion after 60 days.
            Signing in again before that deadline will cancel the deletion and reactivate the account.
          </p>

          <div className="button-row">
            <button className="ghost-button" disabled={isDeactivating} onClick={handleDeactivateAccount} type="button">
              {isDeactivating ? "Deactivating account..." : "Deactivate my account"}
            </button>
          </div>
        </section>
      </div>
    </section>
  );
}

export default SettingsPage;
