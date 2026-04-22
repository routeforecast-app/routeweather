import { Navigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

function AdminRoute({ children }) {
  const { isAdministrationOrHigher } = useAuth();

  if (!isAdministrationOrHigher) {
    return <Navigate to="/" replace />;
  }

  return children;
}

export default AdminRoute;
