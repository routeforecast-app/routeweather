import apiClient from "./client";

export async function fetchLegalDocuments() {
  const response = await apiClient.get("/content/legal");
  return response.data;
}

export async function fetchLegalDocument(documentType) {
  const response = await apiClient.get(`/content/legal/${documentType}`);
  return response.data;
}

export async function fetchAdminLegalDocuments() {
  const response = await apiClient.get("/content/admin/legal");
  return response.data;
}

export async function saveAdminLegalDocument(documentType, payload) {
  const response = await apiClient.put(`/content/admin/legal/${documentType}`, payload);
  return response.data;
}
