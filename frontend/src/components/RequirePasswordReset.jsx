import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

function RequirePasswordReset({ children }) {
  const { user } = useAuth();
  const location = useLocation();

  if (user?.account_status !== "admin_deactivated" && user?.must_change_password) {
    return <Navigate to="/force-password-change" replace state={{ from: location }} />;
  }

  return children;
}

export default RequirePasswordReset;
