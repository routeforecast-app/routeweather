import { Navigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

function SupportRoute({ children }) {
  const { isSupportOrHigher } = useAuth();

  if (!isSupportOrHigher) {
    return <Navigate to="/" replace />;
  }

  return children;
}

export default SupportRoute;
