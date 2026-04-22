import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

function RequireAccountAccess({ children }) {
  const { user } = useAuth();
  const location = useLocation();

  if (user?.account_status === "admin_deactivated" && location.pathname !== "/account-status") {
    return <Navigate to="/account-status" replace state={{ from: location }} />;
  }

  return children;
}

export default RequireAccountAccess;
