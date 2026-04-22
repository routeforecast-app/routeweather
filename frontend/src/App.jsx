import { Navigate, Route, Routes } from "react-router-dom";
import AdminRoute from "./components/AdminRoute";
import AppShell from "./components/AppShell";
import CookieBanner from "./components/CookieBanner";
import ProtectedRoute from "./components/ProtectedRoute";
import RequireAccountAccess from "./components/RequireAccountAccess";
import RequirePasswordReset from "./components/RequirePasswordReset";
import SiteFooter from "./components/SiteFooter";
import SupportRoute from "./components/SupportRoute";
import VisitTracker from "./components/VisitTracker";
import AccountStatusPage from "./pages/AccountStatusPage";
import AdminPage from "./pages/AdminPage";
import DashboardPage from "./pages/DashboardPage";
import ForcePasswordChangePage from "./pages/ForcePasswordChangePage";
import ForgotPasswordPage from "./pages/ForgotPasswordPage";
import GpxLibraryPage from "./pages/GpxLibraryPage";
import LegalDocumentPage from "./pages/LegalDocumentPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import ResetPasswordPage from "./pages/ResetPasswordPage";
import RouteDetailPage from "./pages/RouteDetailPage";
import SettingsPage from "./pages/SettingsPage";
import SupportManagementPage from "./pages/SupportManagementPage";
import UploadRoutePage from "./pages/UploadRoutePage";
import { PreferencesProvider } from "./hooks/usePreferences";

function App() {
  return (
    <>
      <VisitTracker />
      <CookieBanner />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/legal/:documentType" element={<LegalDocumentPage />} />
        <Route path="/contact" element={<LegalDocumentPage defaultDocumentType="contact" eyebrow="Contact" />} />
        <Route
          path="/account-status"
          element={
            <ProtectedRoute>
              <AccountStatusPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/force-password-change"
          element={
            <ProtectedRoute>
              <ForcePasswordChangePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <RequireAccountAccess>
                <RequirePasswordReset>
                  <PreferencesProvider>
                    <AppShell />
                  </PreferencesProvider>
                </RequirePasswordReset>
              </RequireAccountAccess>
            </ProtectedRoute>
          }
        >
          <Route index element={<DashboardPage />} />
          <Route path="gpx-library" element={<GpxLibraryPage />} />
          <Route path="upload" element={<UploadRoutePage />} />
          <Route path="routes/:routeId" element={<RouteDetailPage />} />
          <Route
            path="support"
            element={
              <SupportRoute>
                <SupportManagementPage />
              </SupportRoute>
            }
          />
          <Route
            path="admin"
            element={
              <AdminRoute>
                <AdminPage />
              </AdminRoute>
            }
          />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <SiteFooter />
    </>
  );
}

export default App;
