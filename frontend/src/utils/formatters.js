function padNumber(value) {
  return String(value).padStart(2, "0");
}

export function formatDateTime(value, preferences = { time_format: "24h" }) {
  const date = new Date(value);
  const datePart = date.toLocaleDateString([], { dateStyle: "medium" });
  const timePart =
    preferences.time_format === "12h"
      ? date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit", hour12: true })
      : date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
  return `${datePart}, ${timePart}`;
}

export function formatShortTime(value, preferences = { time_format: "24h" }) {
  const date = new Date(value);
  if (preferences.time_format === "12h") {
    return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit", hour12: true });
  }
  return `${padNumber(date.getHours())}:${padNumber(date.getMinutes())}`;
}

export function formatDistanceKm(value, preferences = { distance_unit: "km" }) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return `-- ${preferences.distance_unit === "miles" ? "mi" : "km"}`;
  }

  if (preferences.distance_unit === "miles") {
    return `${(Number(value) * 0.621371).toFixed(1)} mi`;
  }
  return `${Number(value).toFixed(1)} km`;
}

export function formatSpeedKmh(value, preferences = { distance_unit: "km" }) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return `-- ${preferences.distance_unit === "miles" ? "mph" : "km/h"}`;
  }
  if (preferences.distance_unit === "miles") {
    return `${(Number(value) * 0.621371).toFixed(1)} mph`;
  }
  return `${Number(value).toFixed(1)} km/h`;
}

export function formatMetric(value, unit) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return `-- ${unit}`;
  }
  const digits = unit === "sample" ? 0 : 1;
  return `${Number(value).toFixed(digits)} ${unit}`;
}

export function formatTemperatureC(value, preferences = { temperature_unit: "c" }) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return `--°${preferences.temperature_unit === "f" ? "F" : "C"}`;
  }
  if (preferences.temperature_unit === "f") {
    return `${((Number(value) * 9) / 5 + 32).toFixed(1)}°F`;
  }
  return `${Number(value).toFixed(1)}°C`;
}

export function formatCoordinate(value) {
  return Number(value).toFixed(4);
}

export function summarizeWeather(weather, preferences = { temperature_unit: "c" }) {
  if (!weather) {
    return "Forecast unavailable";
  }
  const temperature = formatTemperatureC(weather.temperature_c, preferences);
  return `${weather.summary} | ${temperature}`;
}
