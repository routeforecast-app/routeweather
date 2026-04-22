import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { hasStoredCookieConsent, saveCookieConsent } from "../utils/cookieConsent";

function CookieBanner() {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    setIsVisible(!hasStoredCookieConsent());
  }, []);

  function handleConsent(choice) {
    saveCookieConsent(choice);
    setIsVisible(false);
  }

  if (!isVisible) {
    return null;
  }

  return (
    <aside className="cookie-banner">
      <div className="cookie-banner-content">
        <div>
          <strong>Cookies on RouteForcast</strong>
          <p>
            We use essential cookies to keep you signed in. If you allow analytics cookies, we also
            collect lightweight visit statistics. Read our <Link to="/legal/cookies">Cookie Notice</Link>,{" "}
            <Link to="/legal/privacy">Privacy Notice</Link>, and <Link to="/legal/terms">Terms</Link>.
          </p>
        </div>

        <div className="cookie-banner-actions">
          <button
            className="ghost-button"
            onClick={() => handleConsent({ essential: true, analytics: false, advertising: false })}
            type="button"
          >
            Essential only
          </button>
          <button
            className="primary-button"
            onClick={() => handleConsent({ essential: true, analytics: true, advertising: false })}
            type="button"
          >
            Accept analytics
          </button>
        </div>
      </div>
    </aside>
  );
}

export default CookieBanner;
