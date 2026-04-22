import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

function AppShell() {
  const { logout, user, isSupportOrHigher, isAdministrationOrHigher } = useAuth();

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Route planning with weather context</p>
          <NavLink className="brand" to="/">
            RouteForcast
          </NavLink>
        </div>

        <nav className="topbar-actions">
          <NavLink className="nav-pill" to="/">
            My Routes
          </NavLink>
          <NavLink className="nav-pill" to="/gpx-library">
            GPX Library
          </NavLink>
          <NavLink className="nav-pill nav-pill-primary" to="/upload">
            Upload Route
          </NavLink>
          {isSupportOrHigher ? (
            <NavLink className="nav-pill" to="/support">
              Support
            </NavLink>
          ) : null}
          {isAdministrationOrHigher ? (
            <NavLink className="nav-pill" to="/admin">
              Admin
            </NavLink>
          ) : null}
          <NavLink className="nav-pill" to="/settings">
            Settings
          </NavLink>
          <div className="user-chip">
            <span>{user?.email}</span>
            <button className="text-button" onClick={logout} type="button">
              Logout
            </button>
          </div>
        </nav>
      </header>

      {user?.needs_support_profile ? (
        <section className="panel support-banner">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Support details needed</p>
              <h2>Add your name and phone number</h2>
              <p>
                To make account recovery and support checks easier, please add your first name, last
                name, and phone number in Settings.
              </p>
            </div>
            <NavLink className="primary-button" to="/settings">
              Update support details
            </NavLink>
          </div>
        </section>
      ) : null}

      <main className="page-shell">
        <Outlet />
      </main>
    </div>
  );
}

export default AppShell;
