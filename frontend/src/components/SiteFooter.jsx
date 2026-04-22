import { Link } from "react-router-dom";

function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="site-footer-content">
        <p className="site-footer-brand">RouteForcast</p>
        <nav className="site-footer-links">
          <Link to="/legal/terms">Terms and Conditions</Link>
          <Link to="/legal/privacy">Privacy Notice</Link>
          <Link to="/legal/cookies">Cookie Notice</Link>
          <Link to="/contact">Contact Details</Link>
        </nav>
      </div>
    </footer>
  );
}

export default SiteFooter;
