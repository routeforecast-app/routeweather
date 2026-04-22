const COOKIE_CONSENT_KEY = "routeweather.cookieConsent";

export function getCookieConsent() {
  try {
    return JSON.parse(localStorage.getItem(COOKIE_CONSENT_KEY) || "null");
  } catch (error) {
    console.error("Could not parse cookie consent", error);
    return null;
  }
}

export function saveCookieConsent(consent) {
  localStorage.setItem(COOKIE_CONSENT_KEY, JSON.stringify(consent));
  window.dispatchEvent(new CustomEvent("routeweather-cookie-consent-updated", { detail: consent }));
}

export function hasAnalyticsConsent() {
  return Boolean(getCookieConsent()?.analytics);
}

export function hasStoredCookieConsent() {
  return Boolean(getCookieConsent());
}
