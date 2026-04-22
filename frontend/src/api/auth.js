import apiClient from "./client";

export async function loginUser(payload) {
  const response = await apiClient.post("/auth/login", payload);
  return response.data;
}

export async function registerUser(payload) {
  const response = await apiClient.post("/auth/register", payload);
  return response.data;
}

export async function fetchCurrentUser() {
  const response = await apiClient.get("/users/me");
  return response.data;
}

export async function requestForgotPassword(payload) {
  const response = await apiClient.post("/auth/forgot-password", payload);
  return response.data;
}

export async function confirmPasswordReset(payload) {
  const response = await apiClient.post("/auth/reset-password/confirm", payload);
  return response.data;
}

export async function updateUserPreferences(payload) {
  const response = await apiClient.patch("/users/me/preferences", payload);
  return response.data;
}

export async function updateUserProfile(payload) {
  const response = await apiClient.patch("/users/me/profile", payload);
  return response.data;
}

export async function changeUserPassword(payload) {
  const response = await apiClient.post("/users/me/change-password", payload);
  return response.data;
}

export async function deactivateOwnAccount() {
  const response = await apiClient.post("/users/me/deactivate");
  return response.data;
}

export async function fetchAdminStats() {
  const response = await apiClient.get("/users/admin/stats");
  return response.data;
}

export async function fetchRoleGrants() {
  const response = await apiClient.get("/users/admin/role-grants");
  return response.data;
}

export async function createRoleGrant(payload) {
  const response = await apiClient.post("/users/admin/role-grants", payload);
  return response.data;
}

export async function deleteRoleGrant(roleGrantId) {
  const response = await apiClient.delete(`/users/admin/role-grants/${roleGrantId}`);
  return response.data;
}

export async function fetchVisitAnalytics() {
  const response = await apiClient.get("/analytics/admin/summary");
  return response.data;
}

export async function fetchSupportInactiveAccounts() {
  const response = await apiClient.get("/support/inactive-accounts");
  return response.data;
}

export async function fetchSupportFlaggedUsers() {
  const response = await apiClient.get("/support/flagged-users");
  return response.data;
}

export async function supportPasswordReset(payload) {
  const response = await apiClient.post("/support/password-reset", payload);
  return response.data;
}

export async function reactivateSupportAccount(payload) {
  const response = await apiClient.post("/support/reactivate", payload);
  return response.data;
}

export async function searchSupportAccounts(payload) {
  const response = await apiClient.post("/support/account-search", payload);
  return response.data;
}

export async function changeSupportAccountEmail(payload) {
  const response = await apiClient.post("/support/email-change", payload);
  return response.data;
}

export async function fetchSupportAuditLogs() {
  const response = await apiClient.get("/support/audit-logs");
  return response.data;
}

export async function adminDeactivateSupportAccount(payload) {
  const response = await apiClient.post("/support/admin-deactivate", payload);
  return response.data;
}

export async function adminDeleteSupportAccount(payload) {
  const response = await apiClient.post("/support/admin-delete", payload);
  return response.data;
}
