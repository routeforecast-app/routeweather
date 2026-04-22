import { createContext, useContext, useEffect, useState } from "react";
import {
  adminDeactivateSupportAccount,
  adminDeleteSupportAccount,
  changeSupportAccountEmail,
  changeUserPassword,
  confirmPasswordReset,
  createRoleGrant,
  deactivateOwnAccount,
  deleteRoleGrant,
  fetchAdminStats,
  fetchCurrentUser,
  fetchRoleGrants,
  fetchSupportAuditLogs,
  fetchSupportFlaggedUsers,
  fetchSupportInactiveAccounts,
  fetchVisitAnalytics,
  loginUser,
  reactivateSupportAccount,
  registerUser,
  requestForgotPassword,
  searchSupportAccounts,
  supportPasswordReset,
  updateUserPreferences,
  updateUserProfile,
} from "../api/auth";
import { setAuthTokenGetter } from "../api/client";
import { hasRole } from "../utils/roles";

const STORAGE_KEY = "routeweather.auth.token";
const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(STORAGE_KEY));
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setAuthTokenGetter(() => token);
  }, [token]);

  useEffect(() => {
    async function hydrateSession() {
      if (!token) {
        setIsLoading(false);
        return;
      }

      try {
        const currentUser = await fetchCurrentUser();
        setUser(currentUser);
      } catch (error) {
        console.error("Failed to restore session", error);
        localStorage.removeItem(STORAGE_KEY);
        setToken(null);
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    }

    hydrateSession();
  }, [token]);

  async function refreshUser() {
    if (!token) {
      setUser(null);
      return null;
    }

    const currentUser = await fetchCurrentUser();
    setUser(currentUser);
    return currentUser;
  }

  async function login(credentials) {
    const response = await loginUser(credentials);
    localStorage.setItem(STORAGE_KEY, response.access_token);
    setToken(response.access_token);
    setUser(response.user);
    return response.user;
  }

  async function register(credentials) {
    const response = await registerUser(credentials);
    localStorage.setItem(STORAGE_KEY, response.access_token);
    setToken(response.access_token);
    setUser(response.user);
    return response.user;
  }

  async function submitForgotPassword(payload) {
    return requestForgotPassword(payload);
  }

  async function submitPasswordReset(payload) {
    return confirmPasswordReset(payload);
  }

  function logout() {
    localStorage.removeItem(STORAGE_KEY);
    setToken(null);
    setUser(null);
  }

  async function savePreferences(preferences) {
    const updatedUser = await updateUserPreferences(preferences);
    setUser(updatedUser);
    return updatedUser;
  }

  async function saveProfile(profile) {
    const updatedUser = await updateUserProfile(profile);
    setUser(updatedUser);
    return updatedUser;
  }

  async function changePassword(payload) {
    const response = await changeUserPassword(payload);
    const refreshedUser = await refreshUser();
    return { ...response, user: refreshedUser };
  }

  async function deactivateAccount() {
    const response = await deactivateOwnAccount();
    logout();
    return response;
  }

  async function loadAdminStats() {
    return fetchAdminStats();
  }

  async function loadRoleGrants() {
    return fetchRoleGrants();
  }

  async function createAccessGrant(payload) {
    return createRoleGrant(payload);
  }

  async function removeAccessGrant(roleGrantId) {
    return deleteRoleGrant(roleGrantId);
  }

  async function loadVisitAnalytics() {
    return fetchVisitAnalytics();
  }

  async function loadSupportInactiveAccounts() {
    return fetchSupportInactiveAccounts();
  }

  async function loadSupportFlaggedUsers() {
    return fetchSupportFlaggedUsers();
  }

  async function requestSupportPasswordReset(payload) {
    return supportPasswordReset(payload);
  }

  async function reactivateAccountBySupport(payload) {
    return reactivateSupportAccount(payload);
  }

  async function searchAccountsBySupport(payload) {
    return searchSupportAccounts(payload);
  }

  async function changeAccountEmailBySupport(payload) {
    return changeSupportAccountEmail(payload);
  }

  async function loadSupportAuditLogs() {
    return fetchSupportAuditLogs();
  }

  async function adminDeactivateAccount(payload) {
    return adminDeactivateSupportAccount(payload);
  }

  async function adminDeleteAccount(payload) {
    return adminDeleteSupportAccount(payload);
  }

  const role = user?.role || "general_user";

  return (
    <AuthContext.Provider
      value={{
        token,
        user,
        role,
        isAuthenticated: Boolean(token && user),
        isLoading,
        isSupportOrHigher: hasRole(role, "support_user"),
        isSeniorSupportOrHigher: hasRole(role, "senior_support_user"),
        isAdministrationOrHigher: hasRole(role, "administration_user"),
        isSystemManager: hasRole(role, "system_manager"),
        login,
        register,
        submitForgotPassword,
        submitPasswordReset,
        logout,
        savePreferences,
        saveProfile,
        changePassword,
        deactivateAccount,
        refreshUser,
        loadAdminStats,
        loadRoleGrants,
        createAccessGrant,
        removeAccessGrant,
        loadVisitAnalytics,
        loadSupportInactiveAccounts,
        loadSupportFlaggedUsers,
        requestSupportPasswordReset,
        reactivateAccountBySupport,
        searchAccountsBySupport,
        changeAccountEmailBySupport,
        loadSupportAuditLogs,
        adminDeactivateAccount,
        adminDeleteAccount,
        hasRole: (minimumRole) => hasRole(role, minimumRole),
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
