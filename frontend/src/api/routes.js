import apiClient from "./client";

export async function fetchRoutes() {
  const response = await apiClient.get("/routes");
  return response.data;
}

export async function fetchGpxFiles() {
  const response = await apiClient.get("/gpx-files");
  return response.data;
}

export async function fetchRouteById(routeId) {
  const response = await apiClient.get(`/routes/${routeId}`);
  return response.data;
}

export async function uploadRoute(payload) {
  const formData = new FormData();
  formData.append("name", payload.name);
  formData.append("start_time", payload.start_time);
  formData.append("speed_kmh", String(payload.speed_kmh));
  formData.append("sample_interval_minutes", String(payload.sample_interval_minutes));
  formData.append("overnight_camps_enabled", String(Boolean(payload.overnight_camps_enabled)));
  formData.append("plan_lunch_stops", String(Boolean(payload.plan_lunch_stops)));
  formData.append("avoid_camp_after_sunset", String(Boolean(payload.avoid_camp_after_sunset)));
  formData.append("lunch_rest_minutes", String(payload.lunch_rest_minutes ?? 0));
  if (payload.target_distance_per_day_km) {
    formData.append("target_distance_per_day_km", String(payload.target_distance_per_day_km));
  }
  if (payload.target_time_to_camp) {
    formData.append("target_time_to_camp", payload.target_time_to_camp);
  }
  if (payload.target_time_to_destination) {
    formData.append("target_time_to_destination", payload.target_time_to_destination);
  }
  if (payload.saved_gpx_file_id) {
    formData.append("saved_gpx_file_id", String(payload.saved_gpx_file_id));
  }
  if (payload.gpx_file) {
    formData.append("gpx_file", payload.gpx_file);
  }
  if (payload.selected_sample_indices?.length) {
    formData.append("selected_sample_indices", JSON.stringify(payload.selected_sample_indices));
  }

  const response = await apiClient.post("/routes/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 180000,
  });
  return response.data;
}

export async function previewManualRoute(payload) {
  const response = await apiClient.post("/routes/manual-preview", payload, {
    timeout: 20000,
  });
  return response.data;
}

export async function createManualRoute(payload) {
  const response = await apiClient.post("/routes/manual", payload, {
    timeout: 180000,
  });
  return response.data;
}

export async function uploadGpxFile(payload) {
  const formData = new FormData();
  if (payload.name?.trim()) {
    formData.append("name", payload.name.trim());
  }
  formData.append("gpx_file", payload.gpx_file);

  const response = await apiClient.post("/gpx-files/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 180000,
  });
  return response.data;
}

export async function downloadGpxFile(gpxFileId) {
  const response = await apiClient.get(`/gpx-files/${gpxFileId}/download`, {
    responseType: "blob",
    timeout: 180000,
  });
  return {
    blob: response.data,
    filename: parseDownloadFilename(response.headers["content-disposition"], "route.gpx"),
  };
}

export async function deleteGpxFile(gpxFileId) {
  await apiClient.delete(`/gpx-files/${gpxFileId}`);
}

export async function exportRoute(routeId) {
  const response = await apiClient.get(`/routes/${routeId}/export`, {
    responseType: "blob",
    timeout: 180000,
  });
  return {
    blob: response.data,
    filename: parseDownloadFilename(
      response.headers["content-disposition"],
      "routeweather-route.routeweather.json",
    ),
  };
}

export async function importRoute(routeFile) {
  const formData = new FormData();
  formData.append("route_file", routeFile);

  const response = await apiClient.post("/routes/import", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 180000,
  });
  return response.data;
}

export async function deleteRoute(routeId) {
  await apiClient.delete(`/routes/${routeId}`);
}

export async function refreshRouteWeather(routeId, sampleIndices) {
  const response = await apiClient.post(`/routes/${routeId}/refresh-weather`, {
    sample_indices: sampleIndices,
  }, {
    timeout: 180000,
  });
  return response.data;
}

function parseDownloadFilename(contentDisposition, fallback) {
  if (!contentDisposition) {
    return fallback;
  }

  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    return decodeURIComponent(utf8Match[1]);
  }

  const quotedMatch = contentDisposition.match(/filename="([^"]+)"/i);
  if (quotedMatch?.[1]) {
    return quotedMatch[1];
  }

  return fallback;
}
