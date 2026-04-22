import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { trackVisit } from "../api/analytics";
import { hasAnalyticsConsent } from "../utils/cookieConsent";

const SESSION_STORAGE_KEY = "routeweather.lastTrackedVisit";

function VisitTracker() {
  const location = useLocation();
  const [consentVersion, setConsentVersion] = useState(0);

  useEffect(() => {
    function handleConsentUpdate() {
      setConsentVersion((current) => current + 1);
    }

    window.addEventListener("routeweather-cookie-consent-updated", handleConsentUpdate);
    return () => {
      window.removeEventListener("routeweather-cookie-consent-updated", handleConsentUpdate);
    };
  }, []);

  useEffect(() => {
    if (!hasAnalyticsConsent()) {
      return;
    }

    const path = `${location.pathname}${location.search}${location.hash}`;
    const now = Date.now();

    try {
      const previous = JSON.parse(sessionStorage.getItem(SESSION_STORAGE_KEY) || "null");
      if (previous?.path === path && now - previous.timestamp < 2000) {
        return;
      }
      sessionStorage.setItem(
        SESSION_STORAGE_KEY,
        JSON.stringify({
          path,
          timestamp: now,
        }),
      );
    } catch (error) {
      console.error("Visit tracking cache failed", error);
    }

    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    const language = navigator.language || "";

    trackVisit({
      path,
      referrer: document.referrer || null,
      timezone,
      language,
    }).catch((error) => {
      console.error("Visit tracking failed", error);
    });
  }, [consentVersion, location.hash, location.pathname, location.search]);

  return null;
}

export default VisitTracker;
