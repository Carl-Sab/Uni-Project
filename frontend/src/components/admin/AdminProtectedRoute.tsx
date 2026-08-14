import { Navigate, Outlet } from "react-router-dom";
import { useAdminAuth } from "../../lib/AdminAuthContext";

export function AdminProtectedRoute() {
  const { username } = useAdminAuth();
  if (!username) return <Navigate to="/admin/login" replace />;
  return <Outlet />;
}
